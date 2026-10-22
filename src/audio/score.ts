// Original procedural dark-fantasy score, synthesised live with a lookahead scheduler (no files, tiny CPU).
// 60 bpm, D minor, 12 chords x 8 beats = 96 s cycle that repeats seamlessly. Motif table is fixed by a seeded RNG.
export interface Score {
  start(): void;
  stop(): void;
  readonly running: boolean;
}

const BPM_SEC = 1; // one beat = 1 s
const CHORD_BEATS = 8;
// [root midi, minor?] -- Dm Bb Gm A | Dm F Gm Bb | C A(maj) Gm A
const PROG: Array<[number, boolean]> = [
  [62, true], [58, false], [55, true], [57, false],
  [62, true], [65, false], [55, true], [58, false],
  [60, false], [57, false], [55, true], [57, false],
];
const CYCLE = PROG.length * CHORD_BEATS; // 96
const SCALE = [0, 3, 5, 7, 10]; // D minor pentatonic above D
const mtof = (m: number) => 440 * 2 ** ((m - 69) / 12);

function mulberry32(a: number) {
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

/** Sparse motif: per-beat midi note or 0. Stepwise-leaning random walk through the pentatonic, ~22% density. */
function buildMotif(): number[] {
  const r = mulberry32(0xb1ac4);
  const out: number[] = [];
  let idx = 5;
  for (let b = 0; b < CYCLE; b++) {
    const bar = Math.floor(b / 4);
    const quiet = bar % 6 === 5 || bar % 12 < 1; // breathing room
    if (!quiet && b % 4 !== 1 && r() < 0.3) {
      idx = Math.max(2, Math.min(9, idx + [-2, -1, -1, 1, 1, 2][Math.floor(r() * 6)]));
      out.push(62 + Math.floor(idx / 5) * 12 + SCALE[idx % 5]);
    } else out.push(0);
  }
  return out;
}

export function createScore(ctx: AudioContext, out: AudioNode): Score {
  const motif = buildMotif();
  const bus = ctx.createGain();
  bus.gain.value = 0.9;
  bus.connect(out);

  // Reverb-like: generated noise impulse + a dark feedback delay.
  const len = Math.floor(ctx.sampleRate * 2.6);
  const ir = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len) ** 3;
  }
  const verb = ctx.createConvolver();
  verb.buffer = ir;
  const verbIn = ctx.createGain();
  verbIn.gain.value = 0.55;
  verbIn.connect(verb).connect(bus);
  const delay = ctx.createDelay(2);
  delay.delayTime.value = 0.75;
  const fb = ctx.createGain();
  fb.gain.value = 0.42;
  const dlp = ctx.createBiquadFilter();
  dlp.type = 'lowpass';
  dlp.frequency.value = 1800;
  delay.connect(dlp).connect(fb).connect(delay);
  dlp.connect(verbIn);
  const wetSend = ctx.createGain();
  wetSend.gain.value = 0.6;
  wetSend.connect(delay);
  wetSend.connect(verbIn);

  const noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
  const nd = noise.getChannelData(0);
  for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;

  function osc(type: OscillatorType, f: number, t: number, dur: number, peak: number, atk: number, rel: number, dst: AudioNode, detune = 0): void {
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = type;
    o.frequency.value = f;
    o.detune.value = detune;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(peak, t + atk);
    g.gain.setValueAtTime(peak, t + Math.max(atk, dur - rel));
    g.gain.linearRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(dst);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  function chord(step: number, t: number): void {
    const [root, minor] = PROG[(step / CHORD_BEATS) % PROG.length];
    const dur = CHORD_BEATS * BPM_SEC + 3; // overlap into next chord
    // Drone: two detuned saws, an octave+fifth below, slow filter.
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.setValueAtTime(260, t);
    lp.frequency.linearRampToValueAtTime(520, t + 5);
    lp.connect(bus);
    for (const det of [-7, 7]) osc('sawtooth', mtof(root - 24), t, dur, 0.1, 2.5, 3, lp, det);
    osc('sine', mtof(root - 36), t, dur, 0.22, 2, 3, bus);
    // Pad: triad, soft triangles/saws through a dark filter, sent to reverb.
    const pad = ctx.createBiquadFilter();
    pad.type = 'lowpass';
    pad.frequency.value = 900;
    pad.connect(bus);
    pad.connect(verbIn);
    const tones = [root, root + (minor ? 3 : 4), root + 7, root + 12];
    tones.forEach((n, i) => {
      for (const det of [-5, 5]) osc(i % 2 ? 'triangle' : 'sawtooth', mtof(n), t, dur, 0.028, 3, 3.5, pad, det);
    });
  }

  function bell(midi: number, t: number): void {
    const f = mtof(midi);
    osc('sine', f, t, 3.2, 0.11, 0.01, 3.1, wetSend);
    osc('sine', f, t, 3.2, 0.07, 0.01, 3.1, bus);
    osc('sine', f * 2.01, t, 1.6, 0.03, 0.005, 1.55, wetSend);
    osc('triangle', f * 0.5, t, 1.2, 0.04, 0.02, 1.1, wetSend);
  }

  function tom(t: number, level: number): void {
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.frequency.setValueAtTime(110, t);
    o.frequency.exponentialRampToValueAtTime(48, t + 0.35);
    g.gain.setValueAtTime(level, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.9);
    o.connect(g);
    g.connect(bus);
    g.connect(verbIn);
    o.start(t);
    o.stop(t + 1);
    const s = ctx.createBufferSource();
    s.buffer = noise;
    const f = ctx.createBiquadFilter();
    f.type = 'lowpass';
    f.frequency.value = 400;
    const ng = ctx.createGain();
    ng.gain.setValueAtTime(level * 0.5, t);
    ng.gain.exponentialRampToValueAtTime(0.0001, t + 0.15);
    s.connect(f).connect(ng).connect(bus);
    s.start(t);
    s.stop(t + 0.2);
  }

  let timer: ReturnType<typeof setInterval> | null = null;
  let step = 0;
  let next = 0;

  function pump(): void {
    while (next < ctx.currentTime + 1.6) {
      const b = step % CYCLE;
      if (b % CHORD_BEATS === 0) chord(b, next);
      if (b % 4 === 0) tom(next, b % 16 === 0 ? 0.28 : 0.16);
      else if (b % 8 === 6) tom(next, 0.07);
      const m = motif[b];
      if (m) bell(m, next + 0.02);
      next += BPM_SEC;
      step++;
    }
  }

  return {
    get running() { return timer !== null; },
    start() {
      if (timer) return;
      next = ctx.currentTime + 0.15;
      pump();
      timer = setInterval(pump, 250);
    },
    stop() {
      if (timer) clearInterval(timer);
      timer = null;
    },
  };
}
