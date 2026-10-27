"""Small DSP toolkit for the Battle Chess SFX pipeline (numpy + scipy only, deterministic)."""
import glob
import os
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'work', 'src')
rng = np.random.default_rng(20241023)


def reseed(n):
    global rng
    rng = np.random.default_rng(n)


# ------------------------------------------------------------------ io
_cache = {}


def load(pack, name):
    """Load decoded source <pack>/<name>.wav (name may be a glob suffix)."""
    key = (pack, name)
    if key not in _cache:
        p = os.path.join(SRC, pack, name + '.wav')
        if not os.path.exists(p):
            m = sorted(glob.glob(os.path.join(SRC, pack, name)))
            if not m:
                raise FileNotFoundError(f'{pack}/{name}')
            p = m[0]
        sr, x = wavfile.read(p)
        x = x.astype(np.float64)
        if x.ndim > 1:
            x = x.mean(axis=1)
        _cache[key] = x
    return _cache[key].copy()


def listpack(pack):
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(SRC, pack, '*.wav')))


# ------------------------------------------------------------------ basics
def t(n):
    return np.arange(int(n)) / SR


def secs(x):
    return len(x) / SR


def db(x):
    return 10 ** (x / 20)


def pad_to(x, n):
    n = int(n)
    return np.pad(x, (0, max(0, n - len(x))))[:n] if n != len(x) else x


def seg(x, start=0.0, dur=None):
    a = int(start * SR)
    b = len(x) if dur is None else a + int(dur * SR)
    return x[a:b].copy()


def trim(x, thresh_db=-50, keep_tail=0.02):
    """Strip leading/trailing silence."""
    pk = np.max(np.abs(x)) + 1e-12
    idx = np.where(np.abs(x) > pk * db(thresh_db))[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(0.002 * SR))
    b = min(len(x), idx[-1] + int(keep_tail * SR))
    return x[a:b].copy()


def fade(x, fin=0.002, fout=0.02):
    x = x.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a > 0 and len(x) > a:
        x[:a] *= np.linspace(0, 1, a)
    if b > 0 and len(x) > b:
        x[-b:] *= np.linspace(1, 0, b) ** 1.5
    return x


def peak(x):
    return float(np.max(np.abs(x)) + 1e-12)


def norm(x, peak_db=-3.0):
    return x * (db(peak_db) / peak(x))


def gain(x, g_db):
    return x * db(g_db)


def pitch(x, ratio):
    """Varispeed: ratio>1 raises pitch and shortens."""
    if abs(ratio - 1) < 1e-4:
        return x
    from fractions import Fraction
    f = Fraction(ratio).limit_denominator(200)
    return signal.resample_poly(x, f.denominator, f.numerator)


def stretch_len(x, new_len_s):
    return signal.resample(x, int(new_len_s * SR)) if len(x) > 8 else x


def reverse(x):
    return x[::-1].copy()


def mix(layers, length=None):
    """layers: list of (signal, offset_s, gain_db)."""
    end = max(int(o * SR) + len(s) for s, o, _ in layers)
    n = int(length * SR) if length else end
    out = np.zeros(n)
    for s, o, g in layers:
        a = int(o * SR)
        if a >= n:
            continue
        s2 = s[: n - a] * db(g)
        out[a:a + len(s2)] += s2
    return out


def concat_at(x, y, offset):
    return mix([(x, 0, 0), (y, offset, 0)])


# ------------------------------------------------------------------ filters
def _sos(kind, f, order=4):
    f = np.clip(f, 20, SR / 2 - 100)
    return signal.butter(order, f, btype=kind, fs=SR, output='sos')


def lp(x, f, order=4):
    return signal.sosfilt(_sos('lowpass', f, order), x)


def hp(x, f, order=4):
    return signal.sosfilt(_sos('highpass', f, order), x)


def bp(x, f1, f2, order=3):
    return signal.sosfilt(_sos('bandpass', [f1, f2], order), x)


def sweep_lp(x, f0, f1, steps=24):
    """Time-varying lowpass (f0->f1 exponentially) by crossfading filtered copies."""
    n = len(x)
    fs = np.geomspace(f0, f1, steps)
    outs = [lp(x, f) for f in fs]
    pos = np.linspace(0, steps - 1, n)
    i0 = np.floor(pos).astype(int)
    i1 = np.minimum(i0 + 1, steps - 1)
    w = pos - i0
    arr = np.array(outs)
    return arr[i0, np.arange(n)] * (1 - w) + arr[i1, np.arange(n)] * w


def eq_tilt(x, low_db=0, high_db=0, split=800):
    return lp(x, split, 2) * db(low_db) + hp(x, split, 2) * db(high_db)


# ------------------------------------------------------------------ synth
def noise(dur, color='white'):
    n = int(dur * SR)
    w = rng.standard_normal(n)
    if color == 'pink':
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        w = signal.lfilter(b, a, w)
    elif color == 'brown':
        w = np.cumsum(w)
        w -= signal.lfilter([1], [1, -0.999], w) * 0  # keep
        w = hp(w, 25, 1)
    return w / (np.max(np.abs(w)) + 1e-9)


def env_exp(n, decay_s, atk_s=0.0):
    tt = np.arange(int(n)) / SR
    e = np.exp(-tt / max(decay_s, 1e-4))
    if atk_s > 0:
        e *= np.minimum(1, tt / atk_s)
    return e


def sine_sweep(f0, f1, dur, decay=None, curve='exp'):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    if curve == 'exp':
        f = f0 * (f1 / f0) ** (tt / dur)
    else:
        f = f0 + (f1 - f0) * tt / dur
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph)
    if decay:
        y *= np.exp(-tt / decay)
    return y


def sub_drop(f0=110, f1=34, dur=1.2, decay=0.45, click=True, drive=1.5):
    """Cinematic sub-bass thump: pitch-dropping sine with a short click."""
    y = sine_sweep(f0, f1, dur, curve='exp') * np.exp(-t(dur * SR) / decay)
    y = np.tanh(y * drive) / np.tanh(drive)
    if click:
        c = hp(noise(0.02), 800) * env_exp(int(0.02 * SR), 0.004)
        y[:len(c)] += c * 0.4
    return y * np.minimum(1, t(len(y)) / 0.0025)


def tone_bank(freqs, amps, decays, dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    y = np.zeros(n)
    for f, a, d in zip(freqs, amps, decays):
        y += a * np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) * np.exp(-tt / d)
    return y


def bell(base, dur=2.0, hard=1.0, ratios=(1, 2.0, 2.76, 5.4, 8.9), decay=0.9):
    amps = [1 / (i + 1) ** 0.8 for i in range(len(ratios))]
    decs = [decay / (1 + i * 0.6) for i in range(len(ratios))]
    y = tone_bank([base * r for r in ratios], amps, decs, dur)
    c = hp(noise(0.03), 1500) * env_exp(int(0.03 * SR), 0.006) * hard * 0.3
    y[:len(c)] += c
    return y


def whoosh(dur=0.5, f0=300, f1=3000, q=1.2, peak_pos=0.5, color='white'):
    n = noise(dur + 0.3, color)
    nn = len(n)
    out = np.zeros(nn)
    steps = 20
    tt = np.arange(nn) / SR
    e = np.sin(np.pi * np.clip(tt / dur, 0, 1) ** (np.log(0.5) / np.log(peak_pos))) ** 2 * (tt < dur)
    for i in range(steps):
        a, b = int(nn * i / steps), int(nn * (i + 1) / steps)
        fc = f0 * (f1 / f0) ** ((i + 0.5) / steps)
        band = bp(n, fc / (1 + 0.5 / q), fc * (1 + 0.5 / q))
        out[a:b] = band[a:b]
    return out * e / (np.max(np.abs(out)) + 1e-9)


def saturate(x, drive=2.0):
    return np.tanh(x * drive) / np.tanh(drive)


# ------------------------------------------------------------------ reverb
_ir_cache = {}


def make_ir(rt60=1.2, predelay=0.012, damp=6000, hf_decay=0.5, seed=7):
    key = (rt60, predelay, damp, hf_decay, seed)
    if key in _ir_cache:
        return _ir_cache[key]
    r = np.random.default_rng(seed)
    n = int((rt60 + predelay) * SR * 1.1)
    w = r.standard_normal(n)
    tt = np.arange(n) / SR
    env = 10 ** (-3 * np.clip(tt - predelay, 0, None) / rt60)
    env[tt < predelay] = 0
    hi = lp(w, damp)
    # darker as it decays
    ir = w * env * 0.4 + lp(w, damp * 0.35) * env ** (1 + hf_decay) * 0.8
    ir = hi * env * 0.3 + ir
    ir /= np.sqrt(np.sum(ir ** 2))
    _ir_cache[key] = ir
    return ir


def reverb(x, rt60=1.2, wet=0.3, predelay=0.012, damp=6000, tail=True, seed=7):
    ir = make_ir(rt60, predelay, damp, 0.5, seed)
    wetsig = signal.fftconvolve(x, ir)
    n = len(wetsig) if tail else len(x)
    out = np.zeros(max(n, len(x)))
    out[:len(x)] += x * (1 - wet * 0.5)
    w = wetsig[:len(out)]
    out[:len(w)] += w * wet * (np.sqrt(np.sum(x ** 2)) / (np.sqrt(np.sum(wetsig ** 2)) + 1e-9)) * 1.4
    return out


# ------------------------------------------------------------------ dynamics
def compress(x, thresh_db=-18, ratio=4, atk=0.003, rel=0.08, makeup=0.0):
    """Feed-forward peak compressor, vectorised via one-pole envelope follower."""
    a = np.abs(x)
    ca = np.exp(-1 / (atk * SR))
    cr = np.exp(-1 / (rel * SR))
    # envelope follower: instant attack (peak hold) with smoothing, implemented as lfilter on max-hold
    env = np.empty_like(a)
    e = 0.0
    # python loop is too slow for long files; use block approach
    blk = 32
    nb = len(a) // blk + 1
    padded = np.pad(a, (0, nb * blk - len(a)))
    pk = padded.reshape(nb, blk).max(axis=1)
    envb = np.empty(nb)
    ca_b = np.exp(-blk / (atk * SR))
    cr_b = np.exp(-blk / (rel * SR))
    for i in range(nb):
        c = ca_b if pk[i] > e else cr_b
        e = c * e + (1 - c) * pk[i]
        envb[i] = e
    env = np.interp(np.arange(len(a)), (np.arange(nb) + 0.5) * blk, envb)
    lvl = 20 * np.log10(env + 1e-9)
    over = np.maximum(lvl - thresh_db, 0)
    g = -over * (1 - 1 / ratio)
    return x * db(g + makeup)


def limit(x, ceiling_db=-1.0):
    """Look-ahead-ish soft limiter: smooth gain reduction then hard ceiling safety."""
    c = db(ceiling_db)
    a = np.abs(x)
    la = int(0.004 * SR)
    # peak-hold over lookahead window
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    hold = maximum_filter1d(a, size=la * 2 + 1)
    g = np.minimum(1, c / (hold + 1e-9))
    g = uniform_filter1d(g, size=la * 2 + 1)
    g = np.minimum(g, 1)
    y = x * g
    return np.clip(y, -c, c)


# ------------------------------------------------------------------ loudness (BS.1770-ish)
def _kweight(x):
    # stage 1 high-shelf (+4dB @ ~1.68kHz), stage 2 high-pass (~38Hz); coefficients for 48k approximated at 44.1k via bilinear design
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = np.tan(np.pi * f0 / SR)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    y = signal.lfilter(b, a, x)
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * f0 / SR)
    a = [1, 2 * (K * K - 1) / (1 + K / Q + K * K), (1 - K / Q + K * K) / (1 + K / Q + K * K)]
    b = [1, -2, 1]
    return signal.lfilter(b, a, y)


def momentary_lufs_max(x):
    """Maximum 400 ms (100 ms hop) K-weighted loudness, in LUFS. Short files are zero-padded to 400 ms."""
    y = _kweight(x)
    w = int(0.4 * SR)
    if len(y) < w:
        y = np.pad(y, (0, w - len(y)))
    sq = y ** 2
    c = np.concatenate([[0], np.cumsum(sq)])
    hop = int(0.1 * SR)
    starts = np.arange(0, len(y) - w + 1, hop)
    ms = (c[starts + w] - c[starts]) / w
    return float(-0.691 + 10 * np.log10(np.max(ms) + 1e-12))


def master(x, target_lufs=-14.0, ceiling_db=-1.0, comp=(-16, 3.0), tail_fade=0.05, hp_hz=22, psy=True):
    """Compress, loudness-normalise (momentary max) and brick-limit; 3 passes so limiting reaches the target."""
    x = hp(x, hp_hz, 2)
    x = trim(x, -60, 0.05)
    if comp:
        x = compress(x, comp[0], comp[1], 0.004, 0.09)
    if psy and target_lufs > -17:
        # psychoacoustic bass: saturate the sub band so its harmonics survive phone / laptop speakers
        sub = lp(x, 110, 2)
        harm = hp(np.tanh(sub / (np.max(np.abs(sub)) + 1e-9) * 3.0), 130, 2)
        x = x + 0.32 * harm * np.max(np.abs(sub))
    y = x
    for _ in range(4):
        L = momentary_lufs_max(y)
        g = target_lufs - L
        y = limit(x * db(g + (_ * 0.0)), ceiling_db)
        x_pre = x
        if abs(momentary_lufs_max(y) - target_lufs) < 0.4:
            break
        # push harder into the limiter
        x = x * db(max(0, min(g, 6)) * 0.5)
    y = fade(y, 0.001, tail_fade)
    return y


def write(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wavfile.write(path, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
