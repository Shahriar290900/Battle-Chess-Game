"""Sound-design building blocks on top of dsp.py: source access, layer helpers, scatter, crowd/choir/horn/drum builders."""
import zlib
import numpy as np
import dsp
from dsp import SR, db, t

ALIAS = {
    'ki': 'k_impact-sounds', 'kr': 'k_rpg-audio', 'ku': 'k_ui-audio', 'kf': 'k_interface-sounds',
    'creature': 'o_80-cc0-creature-sfx', 'rpg': 'o_80-cc0-rpg-sfx', 'bfh': 'o_75-cc0-breaking-falling-hit-sfx',
    'sfx1': 'o_100-cc0-sfx', 'sfx2': 'o_100-cc0-sfx-2', 'mw': 'o_100-cc0-metal-and-wood-sfx',
    'sword': 'o_20-sword-sound-effects-attacks-and-clashes', 'shield': 'o_10-impactshield-blocks',
    'ding': 'o_4-metal-dingsrings', 'swish': 'o_swishes-sound-pack', 'melee': 'o_3-melee-sounds',
    'smith': 'o_blacksmiths-hammer', 'anvil': 'o_hammer-on-anvil', 'drums': 'o_horde-war-drums-loop',
    'horn': 'o_their-coming-generic-horn-sound', 'expl4': 'o_explosions-4', 'chunky': 'o_chunky-explosion',
    'dull': 'o_dull-explosion', 'muffled': 'o_muffled-distant-explosion', 'far': 'o_explosion-somewhere-far',
    'fire': 'o_fire-staff-sound-effects', 'ice': 'o_ice-breakingshattering', 'freeze': 'o_freeze-spell-0',
    'icesp': 'o_ice-spells', 'chant': 'o_creepy-incoherent-chanting', 'troll': 'o_big-scary-troll-sounds',
    'roar': 'o_cc0-deep-monster-roar', 'trot': 'o_horse-trotting', 'snow': 'o_walking-on-snow-sound',
    'clangs': 'o_metal-clang-sounds', 'crowd': 'o_crowd-shoutingspeaking-ambience', 'cheer': 'o_cheers-0',
    'wind': 'o_wind1', 'rumble': 'o_low-rumbling', 'thwack': 'o_thwack-sounds', 'swosh': 'o_wind-hit-time-morph',
    'zombie': 'o_zombies-sound-pack', 'goblin': 'o_goblins-sound-pack', 'winch': 'o_chain-winch-sounds',
    'crash': 'o_crash-collision', 'boulder': 'o_moving-boulder', 'rock': 'o_breaking-rock', 'cave': 'o_cave-in',
    'stonemove': 'o_stone-rock-or-wood-moved-sound', 'steps': 'o_different-steps-on-wood-stone-leaves-gravel-and-mud',
}


def S(alias, name, start=0.0, dur=None, p=1.0, g=0.0, tr=True, f_lp=None, f_hp=None, rev=False, fin=0.001, fout=0.01):
    """Load a source clip, optionally cut, trimmed, pitched (varispeed), filtered, gained."""
    x = dsp.load(ALIAS.get(alias, alias), name)
    if start or dur:
        x = dsp.seg(x, start, dur)
    if tr:
        x = dsp.trim(x, -55, 0.03)
    if p != 1.0:
        x = dsp.pitch(x, p)
    if f_hp:
        x = dsp.hp(x, f_hp)
    if f_lp:
        x = dsp.lp(x, f_lp)
    if rev:
        x = dsp.reverse(x)
    x = dsp.fade(x, fin, fout)
    return x / (dsp.peak(x)) * db(g)  # peak-normalised then gained: g is relative level in dB


def pickv(options, v):
    return options[v % len(options)]


def seed(key, v):
    dsp.reseed(zlib.crc32(f'{key}#{v}'.encode()))


def onsets(x, min_gap=0.14, thresh=0.35, win=0.01):
    a = np.abs(x)
    n = int(win * SR)
    env = np.convolve(a, np.ones(n) / n, mode='same')
    out, last = [], -1e9
    m = env.max()
    # local maxima above thresh
    for i in range(1, len(env) - 1):
        if env[i] > thresh * m and env[i] >= env[i - 1] and env[i] > env[i + 1] and i - last > min_gap * SR:
            out.append(i)
            last = i
    return [i / SR for i in out]


def scatter(clips, n, t0, t1, g0=0.0, g1=-18.0, pmin=0.8, pmax=1.3, shape=2.0, dur=None, r=None):
    """Randomly place n short clips between t0..t1 (denser early when shape>1), gain falling g0->g1."""
    r = r or dsp.rng
    layers = []
    for i in range(n):
        u = r.random() ** shape
        tt = t0 + (t1 - t0) * u
        c = clips[int(r.integers(len(clips)))]
        c = dsp.pitch(c, float(r.uniform(pmin, pmax)))
        if dur:
            c = c[: int(dur * SR)]
        g = g0 + (g1 - g0) * u + float(r.uniform(-3, 2))
        layers.append((dsp.fade(c, 0.001, 0.02), tt, g))
    return dsp.mix(layers) if layers else np.zeros(1)


def crowd(dur=1.8, swell=0.35, g=0.0, lpf=3200, dark=1.0, start=None, rv=0.4):
    """Arena crowd roar sweetener built from CC0 crowd + cheer clips."""
    a = dsp.load(ALIAS['crowd'], 'crowd_shouting_0')
    st = (start if start is not None else 6.0 + float(dsp.rng.uniform(0, 8)))
    c = dsp.seg(a, st, dur + 0.2)
    c = c / dsp.peak(c)
    ch = S('cheer', 'cheers_1', tr=False)
    c = c + dsp.pad_to(ch, len(c)) * 0.5
    if dark != 1.0:
        c = dsp.pitch(c, dark)
    c = dsp.lp(c, lpf)
    n = len(c)
    tt = np.arange(n) / SR
    e = np.where(tt < swell * dur, (tt / (swell * dur)) ** 1.5, np.exp(-(tt - swell * dur) / (0.35 * dur)))
    c = c * e
    c = dsp.reverb(c, 1.2, rv, 0.02, 5000)
    return c / dsp.peak(c) * db(g)


def horn(dur=1.6, base=98.0, g=0.0, attack=0.12):
    """Brass-like horn sting from CC0 horn sample + a synthesized detuned saw stack."""
    tt = t(dur * SR)
    y = np.zeros(len(tt))
    for k, c in enumerate([-9, -3, 0, 4, 9]):
        f = base * 2 ** (c / 1200)
        y += (2 * ((tt * f) % 1) - 1) / (1 + 0.5 * k)
        y += (2 * ((tt * f * 1.5) % 1) - 1) * 0.3
    y = dsp.sweep_lp(y, 500, 2600, 12)
    e = np.minimum(1, tt / attack) * np.exp(-np.maximum(tt - 0.5 * dur, 0) / (0.25 * dur))
    y = y * e
    h = S('horn', 'theircoming3_0', 0.0, dur, p=base / 98.0 * 1.0, tr=False, f_hp=120)
    y = y / dsp.peak(y) + 0.5 * dsp.pad_to(h, len(y)) * np.minimum(1, tt / 0.05)
    y = dsp.saturate(y, 1.4)
    return y / dsp.peak(y) * db(g)


def war_drum(g=0.0, pitchr=1.0, tail=0.9):
    """Layered war drum hit: sampled drum onset + synthesized tom + skin slap."""
    d = dsp.load(ALIAS['drums'], 'horde_war_drums_by_william_hector')
    on = onsets(d, 0.4, 0.5)
    t0 = on[min(3, len(on) - 1)] if on else 0.2
    s = dsp.seg(d, max(0, t0 - 0.01), tail)
    s = dsp.pitch(s, pitchr)
    tom = dsp.sub_drop(120 * pitchr, 52 * pitchr, tail, 0.28, True, 1.8)
    n = dsp.hp(dsp.noise(0.06), 600) * dsp.env_exp(int(0.06 * SR), 0.012)
    y = dsp.mix([(s / dsp.peak(s), 0, -2), (tom / dsp.peak(tom), 0, 0), (n, 0, -8)])
    return y / dsp.peak(y) * db(g)


def gong(base=62.0, dur=5.0, g=0.0):
    y = dsp.tone_bank([base * r for r in (1, 1.59, 2.14, 2.3, 2.65, 3.5, 4.1, 5.43)],
                      [1, .8, .6, .55, .5, .35, .25, .15], [3.2, 2.8, 2.4, 2.2, 1.8, 1.5, 1.2, 0.9], dur)
    mod = 1 + 0.08 * np.sin(2 * np.pi * 3.1 * t(len(y))) * np.exp(-t(len(y)) / 2.0)
    y = y * mod
    s = S('sfx1', 'gong_01', p=base / 120.0 if base < 120 else 1.0, tr=False)
    y = dsp.mix([(y / dsp.peak(y), 0, -1), (dsp.pad_to(s, len(y)), 0, -3)])
    thud = dsp.sub_drop(base * 1.3, base * 0.6, 1.0, 0.5)
    y = dsp.mix([(y, 0, 0), (thud / dsp.peak(thud), 0, -2)])
    return y / dsp.peak(y) * db(g)


def choir(dur=4.0, root=73.4, g=0.0, minor=True, swell=0.6):
    """Synthetic choir pad: detuned saw voices through vowel formants, plus pitched ethereal chant samples."""
    tt = t(dur * SR)
    notes = [root, root * 1.5, root * 2, root * (2.378 if minor else 2.52), root * 3, root * 4]
    y = np.zeros(len(tt))
    for k, f in enumerate(notes):
        for det in (-8, 0, 7):
            fv = f * 2 ** (det / 1200) * (1 + 0.004 * np.sin(2 * np.pi * (4.8 + k * 0.3) * tt + det))
            ph = np.cumsum(fv) / SR
            y += (2 * (ph % 1) - 1) / (1 + 0.3 * k)
    y = dsp.bp(y, 600, 900, 2) + dsp.bp(y, 1000, 1400, 2) * 0.7 + dsp.bp(y, 2200, 2900, 2) * 0.35 + dsp.lp(y, 400) * 0.6
    e = np.where(tt < swell * dur, (tt / (swell * dur)) ** 2, np.exp(-(tt - swell * dur) / (0.25 * dur)))
    y = y * e
    try:
        c = S('chant', 'ethereal_chant_Subclip_02_02', 0.0, dur, p=0.75, tr=False)
        c = dsp.lp(c, 3500) * e[: len(c)] if len(c) <= len(e) else dsp.lp(c, 3500)[: len(e)] * e
        y = y / dsp.peak(y) + 0.45 * dsp.pad_to(c / (dsp.peak(c) + 1e-9), len(y))
    except Exception:
        pass
    y = dsp.reverb(y, 2.2, 0.4, 0.03, 5000)
    return y / dsp.peak(y) * db(g)


def hoof_clops(n=6):
    d = dsp.load(ALIAS['trot'], 'Trot')
    on = onsets(d, 0.18, 0.25)
    clips = []
    for o in on[: max(n, 8)]:
        c = dsp.seg(d, max(0, o - 0.012), 0.22)
        c = dsp.hp(c, 60)
        clips.append(dsp.fade(c / dsp.peak(c), 0.001, 0.08))
    return clips


def gallop(dur=1.8, g=0.0, hard=1.0, surface='stone', tempo=0.34):
    clips = hoof_clops()
    layers = []
    tt = 0.0
    k = 0
    while tt < dur - 0.2:
        for off, gg in ((0.0, -5), (0.095, -3), (0.19, 0)):
            c = clips[int(dsp.rng.integers(len(clips)))]
            c = dsp.pitch(c, float(dsp.rng.uniform(0.92, 1.12)))
            lay = [(c, tt + off, gg + (k * 0)), ]
            # stone/ice impact layer under every hoof
            ia = S('ki', pickv(['impactPlate_medium_%03d', 'impactMetal_light_%03d', 'footstep_concrete_%03d'], k) % int(dsp.rng.integers(5)), f_lp=2500, g=-12)
            lay.append((ia, tt + off, gg - 4))
            if surface == 'ice':
                cr = S('snow', 'SnowWalk', g=-12, f_hp=2500)
                lay.append((cr[: int(0.2 * SR)], tt + off, gg - 9))
            layers += lay
        tt += tempo * (0.97 ** k)
        k += 1
    y = dsp.mix(layers)
    y *= np.minimum(1, np.minimum(t(len(y)) / 0.15, (len(y) / SR - t(len(y))) / 0.25 + 0.0))
    y = dsp.compress(y, -20, 3)
    y = dsp.reverb(y, 1.0 if surface == 'stone' else 1.6, 0.25, 0.015, 5000)
    return y / dsp.peak(y) * db(g)


def creature_call(kind='bellow', g=0.0, p=1.0, dur=1.2):
    """Elk/ram-like bellow or ghostly whinny designed from CC0 creature/troll/zombie recordings."""
    if kind == 'bellow':
        a = S('roar', 'monster_roar', 0.2, 1.2, p=0.9 * p, f_hp=70)
        b = S('troll', 'troll-roars_0', 0.5, 1.2, p=0.8 * p, f_hp=70)
        c = S('creature', 'monster_04', p=0.9 * p)
        y = dsp.mix([(a, 0, -2), (dsp.pad_to(b, len(a)), 0.02, -4), (c, 0.05, -3)])
        # vibrato + pitch bend up then down (rearing bellow)
        n = len(y)
        mod = 1 + 0.02 * np.sin(2 * np.pi * 6.5 * t(n))
        idx = np.cumsum(mod) * 1.0
        idx = np.clip(idx, 0, n - 1)
        y = np.interp(idx, np.arange(n), y)
        y = dsp.saturate(y, 1.8)
    else:  # whinny: scream formants swept upward with trembling
        a = S('creature', 'scream_01', p=1.15 * p, f_hp=300)
        b = S('creature', 'scream_02', p=1.3 * p, f_hp=400)
        y = dsp.mix([(a, 0, -1), (dsp.pad_to(b, len(a)), 0.03, -5)])
        n = len(y)
        mod = 1 + 0.035 * np.sin(2 * np.pi * (9 + 6 * t(n)) * t(n))
        y = np.interp(np.clip(np.cumsum(mod), 0, n - 1), np.arange(n), y)
        y = dsp.reverb(dsp.bp(y, 400, 5200) + 0.0, 2.0, 0.4, 0.02, 7000)
    y = y[: int(dur * 1.5 * SR)]
    return y / dsp.peak(y) * db(g)


def shimmer(dur=1.5, base=1800, g=0.0, n=14, spread=2.2):
    """Glassy chimes: randomly placed bell partials."""
    layers = []
    for i in range(n):
        f = base * float(dsp.rng.uniform(1, spread)) * (1 + 0.5 * (i % 3))
        tk = dsp.tone_bank([f, f * 2.76, f * 5.4], [1, .4, .2], [0.5, 0.25, 0.12], 1.0)
        layers.append((tk, float(dsp.rng.uniform(0, dur * 0.7)), -float(dsp.rng.uniform(0, 12))))
    y = dsp.mix(layers)
    return y / dsp.peak(y) * db(g)


def boom(f0=70, f1=26, dur=1.8, g=0.0, expl=('expl4', 'explosion3'), lpf=900):
    sub = dsp.sub_drop(f0, f1, dur, dur * 0.4, True, 1.6)
    e = S(expl[0], expl[1], f_lp=lpf)
    e = dsp.pad_to(e, len(sub))
    y = dsp.mix([(sub / dsp.peak(sub), 0, 0), (e, 0.0, -3)])
    return y / dsp.peak(y) * db(g)


def finish(key, v, x, lufs=-14.0, comp=(-16, 3.0), out='work/out', tail=0.08, ceil=-1.0, maxlen=None):
    if maxlen:
        x = dsp.trim(x, -55, 0.02)[: int(maxlen * SR)]
        tail = 0.12 if maxlen < 1 else 0.3
    y = dsp.master(x, lufs, ceil, comp, tail)
    path = f'{dsp.HERE}/{out}/{key.replace(":", "_")}__{v}.wav'
    dsp.write(path, y)
    return path, y
