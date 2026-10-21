// Procedural SFX: every SfxName is synthesised with oscillators, a shared noise buffer, filters and envelopes.
import type { Role, SfxName } from '../contracts';

export interface SfxPlayer {
  play(name: SfxName, opts?: { volume?: number; pitch?: number }): void;
}

const ROLE_WEIGHT: Record<Role, number> = { pawn: 0.35, knight: 0.6, bishop: 0.5, rook: 0.85, queen: 0.75, king: 1 };
const MAX_VOICES = 24;

export function createSfx(ctx: AudioContext, out: AudioNode): SfxPlayer {
  // 2 s of white noise, shared by every voice.
  const noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
  const nd = noiseBuf.getChannelData(0);
  for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;

  let active = 0;
  const rnd = (a: number, b: number) => a + Math.random() * (b - a);

  function env(g: AudioParam, t0: number, peak: number, atk: number, dec: number): void {
    g.setValueAtTime(0.0001, t0);
    g.linearRampToValueAtTime(peak, t0 + atk);
    g.exponentialRampToValueAtTime(0.0001, t0 + atk + dec);
  }

  function tone(dst: AudioNode, t0: number, type: OscillatorType, f0: number, f1: number, peak: number, atk: number, dec: number): void {
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f0, t0);
    if (f1 > 0 && f1 !== f0) o.frequency.exponentialRampToValueAtTime(f1, t0 + atk + dec);
    env(g.gain, t0, peak, atk, dec);
    o.connect(g).connect(dst);
    o.start(t0);
    o.stop(t0 + atk + dec + 0.05);
  }

  function noise(dst: AudioNode, t0: number, filt: BiquadFilterType, f0: number, f1: number, q: number, peak: number, atk: number, dec: number): void {
    const s = ctx.createBufferSource();
    s.buffer = noiseBuf;
    const f = ctx.createBiquadFilter();
    f.type = filt;
    f.Q.value = q;
    f.frequency.setValueAtTime(f0, t0);
    if (f1 !== f0) f.frequency.exponentialRampToValueAtTime(f1, t0 + atk + dec);
    const g = ctx.createGain();
    env(g.gain, t0, peak, atk, dec);
    s.connect(f).connect(g).connect(dst);
    s.start(t0, Math.random() * 1.5);
    s.stop(t0 + atk + dec + 0.05);
  }

  // ------------------------------------------------------------ recipes (p = pitch multiplier)
  const bronzeRatios = [1, 1.52, 2.76, 3.9, 5.43];

  function bronzeClang(d: AudioNode, t: number, p: number, base = 220, heavy = 1): void {
    bronzeRatios.forEach((r, i) => tone(d, t, 'sine', base * r * p, base * r * p * 0.995, (0.5 / (i + 1.3)) * heavy, 0.002, 0.9 - i * 0.1));
    noise(d, t, 'bandpass', 3000, 1500, 1, 0.5, 0.001, 0.05); // strike transient
    tone(d, t, 'sine', 90 * p, 45, 0.7 * heavy, 0.003, 0.25); // body thud
  }

  function glassShatter(d: AudioNode, t: number, p: number, heavy = 1): void {
    noise(d, t, 'highpass', 5000 * p, 3000, 0.7, 0.55, 0.001, 0.35);
    for (let i = 0; i < 7; i++) {
      const dt = rnd(0, 0.28);
      tone(d, t + dt, 'sine', rnd(2800, 7500) * p, 0, 0.16 * heavy, 0.001, rnd(0.08, 0.3));
    }
    noise(d, t, 'bandpass', 8000 * p, 8000 * p, 18, 0.35, 0.001, 0.6); // high resonance ring
    tone(d, t, 'triangle', 220 * p, 70, 0.35 * heavy, 0.002, 0.2);
  }

  function whoosh(d: AudioNode, t: number, p: number, w: number): void {
    const dur = 0.18 + w * 0.35;
    noise(d, t, 'bandpass', 400 * p, 2600 * p, 1.2, 0.45 * (0.5 + w), dur * 0.6, dur * 0.5);
    noise(d, t, 'lowpass', 200, 700, 0.8, 0.25 * w, dur * 0.5, dur * 0.5);
  }

  function step(d: AudioNode, t: number, p: number, faction: 'emberhold' | 'rime'): void {
    if (faction === 'emberhold') {
      tone(d, t, 'sine', 130 * p, 55, 0.6, 0.002, 0.14);
      noise(d, t, 'lowpass', 900, 400, 0.7, 0.3, 0.002, 0.08);
    } else {
      noise(d, t, 'highpass', 2500 * p, 1500, 0.8, 0.35, 0.001, 0.07);
      noise(d, t + 0.025, 'bandpass', 4200 * p, 3000, 3, 0.25, 0.001, 0.09);
      tone(d, t, 'sine', 110 * p, 60, 0.25, 0.002, 0.1);
    }
  }

  function riser(d: AudioNode, t: number, p: number, faction: 'emberhold' | 'rime'): void {
    const dur = 0.9;
    if (faction === 'emberhold') {
      noise(d, t, 'bandpass', 200, 1800, 1.5, 0.5, dur * 0.85, dur * 0.2);
      tone(d, t, 'sawtooth', 70 * p, 220 * p, 0.18, dur * 0.85, dur * 0.2);
      tone(d, t + dur, 'sine', 80 * p, 40, 0.6, 0.004, 0.4);
    } else {
      noise(d, t, 'highpass', 1500, 6000, 1, 0.3, dur * 0.85, dur * 0.2);
      tone(d, t, 'sine', 400 * p, 1600 * p, 0.2, dur * 0.85, dur * 0.2);
      tone(d, t, 'sine', 600 * p, 2400 * p, 0.12, dur * 0.85, dur * 0.2);
      glassShatter(d, t + dur, p, 0.5);
    }
  }

  function shimmer(d: AudioNode, t: number, p: number, faction: 'emberhold' | 'rime'): void {
    const base = faction === 'emberhold' ? 440 : 880;
    for (let i = 0; i < 6; i++) {
      const st = t + i * 0.07;
      tone(d, st, faction === 'emberhold' ? 'triangle' : 'sine', base * p * (1 + i * 0.25) * (i % 2 ? 1.005 : 0.995), 0, 0.14, 0.01, 0.5);
    }
    noise(d, t, 'bandpass', faction === 'emberhold' ? 1800 : 6500, faction === 'emberhold' ? 900 : 9000, 4, 0.2, 0.2, 0.7);
  }

  function pad(d: AudioNode, t: number, freqs: number[], peak: number, atk: number, dec: number): void {
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 1200;
    lp.connect(d);
    for (const f of freqs) {
      for (const det of [-6, 6]) {
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = 'sawtooth';
        o.frequency.value = f;
        o.detune.value = det;
        env(g.gain, t, peak, atk, dec);
        o.connect(g).connect(lp);
        o.start(t);
        o.stop(t + atk + dec + 0.05);
      }
    }
  }

  const recipes = (name: SfxName, d: AudioNode, t: number, p: number): number => {
    const [kind, a, b] = name.split(':');
    switch (kind) {
      case 'move': step(d, t, p, b as 'emberhold' | 'rime'); return 0.3;
      case 'attack': whoosh(d, t, p, ROLE_WEIGHT[b as Role] ?? 0.5); return 0.7;
      case 'impact':
        if (a === 'emberhold') bronzeClang(d, t, p, 220, 1);
        else { glassShatter(d, t, p, 0.6); tone(d, t, 'sine', 100 * p, 50, 0.5, 0.003, 0.2); }
        return 1.2;
      case 'shatter': if (a === 'emberhold') { bronzeClang(d, t, p * 0.7, 160, 1.2); noise(d, t + 0.05, 'lowpass', 1200, 300, 0.7, 0.5, 0.01, 0.5); } else glassShatter(d, t, p, 1.2); return 1.3;
      case 'summon': riser(d, t, p, a as 'emberhold' | 'rime'); return 1.8;
      case 'spell': shimmer(d, t, p, a as 'emberhold' | 'rime'); return 1.2;
      case 'check':
        tone(d, t, 'sine', 70 * p, 45, 0.9, 0.004, 0.45);
        tone(d, t + 0.32, 'sine', 70 * p, 45, 0.7, 0.004, 0.45);
        noise(d, t, 'lowpass', 400, 150, 0.7, 0.3, 0.003, 0.25);
        return 1;
      case 'mate':
        tone(d, t, 'sine', 55 * p, 28, 1, 0.01, 2.2);
        noise(d, t, 'lowpass', 600, 80, 0.8, 0.7, 0.01, 1.6);
        pad(d, t + 0.1, [110 * p, 164.8 * p, 220 * p, 261.6 * p], 0.045, 0.9, 2.4);
        return 3.5;
      case 'castle':
        tone(d, t, 'sine', 100 * p, 50, 0.8, 0.003, 0.25);
        noise(d, t, 'lowpass', 700, 250, 0.7, 0.4, 0.003, 0.15);
        tone(d, t + 0.28, 'sine', 90 * p, 45, 0.8, 0.003, 0.25);
        noise(d, t + 0.28, 'lowpass', 700, 250, 0.7, 0.4, 0.003, 0.15);
        return 0.7;
      case 'promote':
        [0, 4, 7, 12].forEach((s, i) => tone(d, t + i * 0.11, 'triangle', 330 * p * 2 ** (s / 12), 0, 0.22, 0.01, 0.6));
        shimmer(d, t + 0.2, p, 'emberhold');
        return 1.6;
      case 'ui':
        if (a === 'click') { tone(d, t, 'square', 900 * p, 600 * p, 0.12, 0.001, 0.05); }
        else { tone(d, t, 'sine', 660 * p, 990 * p, 0.2, 0.002, 0.09); }
        return 0.2;
    }
    return 0;
  };

  return {
    play(name, opts) {
      if (ctx.state !== 'running' || active >= MAX_VOICES) return;
      const t = ctx.currentTime + 0.005;
      const p = (opts?.pitch ?? 1) * rnd(0.95, 1.05);
      const probe = ctx.createGain();
      // Dry-run duration is tiny; recipes return a tail estimate so the voice node outlives them.
      probe.gain.value = opts?.volume ?? 1;
      probe.connect(out);
      active++;
      const dur = recipes(name, probe, t, p);
      setTimeout(() => { active--; probe.disconnect(); }, (dur + 0.2) * 1000);
    },
  };
}
