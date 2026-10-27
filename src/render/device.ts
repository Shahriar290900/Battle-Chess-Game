// Device sniffing for the quality bootstrap. Reads the (unmasked) GPU string from a throw-away WebGL context so the first
// guess - and the renderer's antialias flag, which cannot change after context creation - are right from the start.
import type { QualityTier } from '../contracts';

export interface DeviceInfo {
  gpu: string;
  mobile: boolean;
  cores: number;
  memoryGb: number;
  /** Integrated / mobile-class GPU: never auto-pick High, probe Medium vs Low. */
  weak: boolean;
  /** Known to be slow even on Medium (old mobile GPUs, software GL): start on Low. */
  veryWeak: boolean;
  /** Tier to start with before the real FPS probe. */
  guess: QualityTier;
}

const WEAK = /Intel.*(HD|UHD|Iris|Graphics)|Mali|Adreno|PowerVR|Apple GPU|VideoCore|Vivante|Tegra|SwiftShader|llvmpipe|softpipe|Microsoft Basic/i;
const VERY_WEAK = /Mali-(4|T[0-7])|Mali-G(5|31|51|52)|Adreno.*\(?TM\)?\s*[2-5]\d\d\b|Adreno\s*[2-5]\d\d\b|PowerVR|VideoCore|Vivante|SwiftShader|llvmpipe|softpipe|Microsoft Basic/i;

export function readGpuString(): string {
  try {
    const c = document.createElement('canvas');
    const gl = (c.getContext('webgl2') || c.getContext('webgl')) as WebGLRenderingContext | null;
    if (!gl) return 'none';
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    const s = String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    return s;
  } catch { return 'unknown'; }
}

export function detectDevice(isMobile: boolean): DeviceInfo {
  const gpu = readGpuString();
  const cores = navigator.hardwareConcurrency || 4;
  const memoryGb = (navigator as { deviceMemory?: number }).deviceMemory ?? 8;
  const weak = isMobile || WEAK.test(gpu) || cores <= 4;
  const veryWeak = VERY_WEAK.test(gpu) || (isMobile && (cores <= 4 || memoryGb <= 3));
  const guess: QualityTier = veryWeak ? 'low' : isMobile ? 'low' : 'medium';
  return { gpu, mobile: isMobile, cores, memoryGb, weak, veryWeak, guess };
}
