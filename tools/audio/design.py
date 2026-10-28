"""Battle Chess SFX design: recipes layering CC0 samples with synthesized sub / transient / tail layers.
Usage: python3 design.py [key-prefix ...]   (writes work/out/*.wav and work/registry.json)"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp
from dsp import SR, db, t, mix
from lib import S, pickv, seed, scatter, crowd, horn, war_drum, gong, choir, gallop, creature_call, shimmer, boom, finish, hoof_clops, onsets, granular, stick_slip, make_loop, finish_loop

REG = {}          # key -> dict(nvar, pri, gain, preload, lufs, fn)
ALIASES = {}      # key -> target key
ROLES = ['pawn', 'knight', 'bishop', 'rook', 'queen', 'king']
EMB = dict(rt=1.4, damp=4200, wet=0.3)
RIME = dict(rt=2.3, damp=9000, wet=0.36)


def reg(key, nvar=1, pri=2, gain=1.0, preload=False, lufs=-14.0, comp=(-16, 3.0), cooldown=None, maxlen=None, loop=False):
    def deco(fn):
        REG[key] = dict(nvar=nvar, pri=pri, gain=gain, preload=preload, lufs=lufs, comp=comp, cooldown=cooldown, maxlen=maxlen, loop=loop, fn=fn)
        return fn
    return deco


def alias(key, target):
    ALIASES[key] = target


def R(x, f):  # faction reverb
    return dsp.reverb(x, f['rt'], f['wet'], 0.012, f['damp'])


def V(i, n):  # normalised variation position
    return i / max(1, n - 1)


def rr(a, b):
    return float(dsp.rng.uniform(a, b))


def ri(n):
    return int(dsp.rng.integers(n))


def lay(*layers, length=None):
    return mix(list(layers), length)


def thump(f0=95, f1=36, dur=0.7, decay=0.28, g=0.0, drive=1.6):
    x = dsp.sub_drop(f0, f1, dur, decay, True, drive)
    return x / dsp.peak(x) * db(g)


def crack_t(g=0.0, v=0, bright=True):
    """Sharp transient: first ~60 ms of a metal/plate hit, high-passed."""
    nm = pickv(['impactMetal_heavy_%03d', 'impactPlate_heavy_%03d', 'impactMetal_medium_%03d'], v) % ri(5)
    x = S('ki', nm, 0, 0.09, f_hp=1800 if bright else 900)
    return x * db(g)


def ring(base, dur=1.6, g=-12, hard=0.5):
    y = dsp.bell(base, dur, hard)
    return y / dsp.peak(y) * db(g)


# ====================================================================== STEPS
def step_base(v, faction):
    k = ri(5)
    if faction == 'emberhold':
        a = S('ki', f'footstep_concrete_{k:03d}', g=0)
        b = S('ki', pickv(['impactPlate_medium_%03d', 'impactMetal_light_%03d', 'impactPlate_light_%03d'], v) % ri(5), f_lp=3000, g=-7)
        c = S('rpg', f'chain_0{1 + ri(3)}', f_hp=2500, g=-16, dur=0.2)
        th = thump(85 * rr(.95, 1.05), 45, 0.3, .12, -3)
        y = lay((a, 0, 0), (b, 0.004, -2), (c, 0.02, -2), (th, 0, -2))
        y = dsp.reverb(y, 0.7, 0.22, 0.008, 4000)
    else:
        a = S('ki', f'footstep_snow_{k:03d}', g=0)
        b = S('snow', pickv(['SnowWalk', 'SnowWalk2', 'SnowWalk'], v), f_hp=1500, g=-6, dur=0.35)
        c = S('ki', f'impactGlass_light_{ri(5):03d}', 0, 0.12, f_hp=3500, g=-14)
        th = thump(110, 62, 0.2, .07, -12)
        y = lay((a, 0, 0), (b, 0.012, -2), (c, 0.01, -3), (th, 0, -2))
        y = dsp.reverb(y, 1.0, 0.25, 0.008, 9000)
    return y


for f in ('emberhold', 'rime'):
    reg(f'move:step:{f}', 3, 1, 0.55, True, lufs=-22, maxlen=0.4, cooldown=0.08)(lambda v, f=f: step_base(v, f))


def hoof_step(v, f):
    clips = hoof_clops()
    c = clips[(v * 2 + ri(2)) % len(clips)]
    c = dsp.pitch(c, rr(.95, 1.08) * (1.0 if f == 'emberhold' else 1.06))
    st = S('ki', f'footstep_concrete_{ri(5):03d}', f_lp=2500, g=-9) if f == 'emberhold' else S('snow', 'SnowWalk', f_hp=2500, g=-10, dur=0.3)
    arm = S('rpg', f'chain_0{1 + ri(3)}', f_hp=2000, g=-18, dur=0.2) if f == 'emberhold' else S('ki', f'impactGlass_light_{ri(5):03d}', 0, .1, f_hp=4000, g=-14)
    y = lay((c, 0, 0), (st, 0.005, -3), (arm, 0.03, -3), (thump(95, 48, 0.25, .1, -6), 0, -3))
    return dsp.reverb(y, 0.9, 0.22, 0.01, 5000 if f == 'emberhold' else 9000)


def heavy_step(v, f):
    th = thump(70, 28, 0.9, 0.32, 0)
    if f == 'emberhold':
        a = S('ki', f'impactPlate_heavy_{ri(5):03d}', g=-2)
        st = S('bfh', f'bfh1_rock_falling_0{1 + ri(9)}', f_lp=3500, g=-7)
        dust = dsp.lp(dsp.noise(0.3), 1200) * dsp.env_exp(int(0.3 * SR), 0.08) * 0.3
    else:
        a = S('ki', f'impactGlass_heavy_{ri(5):03d}', g=-3)
        st = S('ice', pickv(['LedasLuzta', 'LedasLuzta2'], v), g=-8, f_hp=500)
        dust = dsp.hp(dsp.noise(0.4), 5000) * dsp.env_exp(int(0.4 * SR), 0.1) * 0.15
    y = lay((th, 0, -1), (a, 0, 0), (st, 0.03, -3), (dust, 0.02, -4))
    return R(y, dict(rt=1.0, wet=0.25, damp=EMB['damp'] if f == 'emberhold' else RIME['damp']))


for f in ('emberhold', 'rime'):
    reg(f'step:knight:{f}', 3, 1, 0.6, True, lufs=-22, maxlen=0.4)(lambda v, f=f: hoof_step(v, f))
    reg(f'step:heavy:{f}', 2, 2, 0.8, True, lufs=-16)(lambda v, f=f: heavy_step(v, f))


# ====================================================================== WHOOSHES
def whoosh_fx(role, faction, v):
    w = {'pawn': .3, 'knight': .55, 'bishop': .45, 'rook': .85, 'queen': .75, 'king': 1.0}[role]
    dur = 0.3 + w * 0.5
    f0, f1 = (260, 2400) if faction == 'emberhold' else (500, 5200)
    a = dsp.whoosh(dur, f0, f1, 1.1, 0.55)
    b = S('swosh', pickv(['qubodup-megaswosh1', 'qubodup-megaswosh2', 'qubodup-slomo1'], v), g=-4,
          p=(1.1 - 0.4 * w) * (1 if faction == 'emberhold' else 1.2), f_hp=250 if faction == 'rime' else None)
    b = dsp.pad_to(b, int((dur + .2) * SR))[: int((dur + .2) * SR)]
    parts = [(a, 0, 0), (b, 0, -3)]
    if role == 'pawn':
        parts.append((S('kr', pickv(['knifeSlice', 'knifeSlice2', 'drawKnife2'], v), g=-8, f_hp=1500), dur * 0.35, 0))
        parts.append((S('swish', f'swish-{1 + ri(13)}', g=-3), dur * .3, 0))
    if role == 'knight':
        parts.append((creature_call('bellow' if faction == 'emberhold' else 'whinny', -9, 1.0, .9)[: int(.9 * SR)], 0, -3))
        parts.append((S('swish', 'swish-7', g=-3, p=.8), dur * .4, 0))
    if role in ('rook', 'king', 'queen'):
        parts.append((thump(75, 38, dur + .3, .4, -9), dur * .45, -2))
        parts.append((S('rumble', 'low-rumbling-176033', 0, dur + .3, g=-10, f_lp=250), 0, -3))
    if role == 'bishop':
        parts.append((S('fire', 'LEGIT_FIR_Fire_Staff_3-Audio', 0.1, dur, g=-5) if faction == 'emberhold' else S('icesp', 'ice', 0.0, dur, g=-6, f_hp=800), 0, -2))
    if role == 'king' and faction == 'emberhold':
        parts.append((S('sword', 'sword_3', g=-8, p=.6), dur * .3, 0))
    y = lay(*parts)
    return R(y, dict(rt=0.8, wet=0.15, damp=5000))


for r in ROLES:
    for f, suf in (('emberhold', ''), ('rime', ':rime')):
        reg(f'attack:whoosh:{r}{suf}', 2, 2, 0.75, True, lufs=-17)(lambda v, r=r, f=f: whoosh_fx(r, f, v))


# ====================================================================== CAPTURE HITS  (hit:<role>:<faction>)
def hit_pawn(f, v):
    th = thump(100, 40, 0.5, .2, 0)
    if f == 'emberhold':
        shriek = S('sword', pickv(['sword_clash_4', 'sword_clash_1', 'sword_clash_8'], v), g=0, f_hp=900, p=0.92 - 0.1 * v)
        scrape = dsp.hp(S('kr', pickv(['drawKnife1', 'drawKnife3', 'knifeSlice'], v), g=-6), 1200)
        crunch = lay((S('ki', f'impactPlate_heavy_{ri(5):03d}', g=-1), 0, 0), (S('thwack', f'thwack-0{4 + v}', g=-4, f_lp=3500), 0.01, 0),
                     (S('bfh', f'bfh1_metal_hit_0{2 + v}', g=-6), 0.006, 0))
        y = lay((crunch, 0, 0), (th, 0, -2), (crack_t(-2, v), 0, 0), (shriek, 0.012, -5), (scrape, 0.12, -9),
                (S('bfh', f'bfh1_metal_falling_0{1 + v}', g=-14), 0.3, 0))
        return R(y, EMB)
    cr = S('ki', f'impactMetal_heavy_{ri(5):03d}', g=0, p=0.85)
    ic = S('ice', pickv(['LedasLuzta', 'LedasLuzta2', 'LedasLuzta5'], v), g=-2)
    gl = S('ki', f'impactGlass_heavy_{ri(5):03d}', g=-3)
    frost = dsp.hp(dsp.noise(.5), 5000) * dsp.env_exp(int(.5 * SR), .12) * .2
    y = lay((cr, 0, 0), (ic, 0.008, -1), (gl, 0.02, -2), (th, 0, -3), (crack_t(-2, v + 1), 0, 0), (frost, .05, -2),
            (S('sword', pickv(['sword_clash_6', 'sword_clash_2'], v), g=-9, p=1.15, f_hp=1500), .02, 0))
    return R(y, RIME)


def hit_rook(f, v):
    big = boom(72 - 8 * v, 26, 2.2, 0, expl=('expl4', 'explosion3' if v == 0 else 'explosions4'), lpf=1100)
    rock_clips = [S('bfh', f'bfh1_rock_falling_0{i}', g=0, tr=True) for i in range(1, 10)] + \
                 [S('bfh', f'bfh1_rock_breaking_0{i}', g=0) for i in range(1, 4)] + [S('rock', 'rock_break_0')]
    rain = scatter(rock_clips, 20, 0.35, 2.7, -4, -26, 0.55, 1.2, 1.7)
    caves = S('cave', 'cave_in_-_starninjas_0', 0.4 + .3 * v, 2.6, g=-6, f_lp=5000)
    collapse = lay((caves, 0.15, 0), (S('boulder', 'boulder_drop_0', g=0, p=.8), 0.25, 0),
                   (S('ki', f'impactPlate_heavy_{ri(5):03d}', g=0, p=.7), 0.0, 0))
    base = [(big, 0, 0), (thump(60, 25, 1.7, .6, 0), 0, 0), (crack_t(-1, v), 0, -1), (collapse, 0.08, -4), (rain, 0, -3)]
    if f == 'emberhold':
        fire = S('rpg', f'spell_fire_0{3 + v}', g=-1, p=0.75, f_lp=6000)
        flames = S('fire', 'LEGIT_FIR_Fire_Staff_11-Audio', 0.0, 2.2, g=-8, f_hp=300)
        base += [(fire, 0.12, -3), (flames, 0.2, -5)]
        y = lay(*base)
        return dsp.reverb(y, 2.2, 0.28, 0.02, 3500)
    ice = S('ice', 'LedasLuzta33', g=-2)
    cold = S('icesp', 'coldsnap', g=-5, f_hp=600)
    shards = scatter([S('ice', n, g=0, f_hp=2500) for n in ('LedasLuzta', 'LedasLuzta2', 'LedasLuzta4', 'LedasLuzta5')] +
                     [S('bfh', f'bfh1_glass_falling_0{i}', g=0, f_hp=2500) for i in range(1, 5)], 22, .3, 2.9, -8, -28, .9, 1.5, 1.4)
    base += [(ice, 0.05, -2), (cold, 0.1, -4), (shards, 0, -2)]
    y = lay(*base)
    return dsp.reverb(y, 3.0, 0.32, 0.025, 8000)


def hit_knight(f, v):
    th = thump(90, 34, 0.9, .3, 0)
    cl = crowd(1.8, 0.3, -7, 3600 if f == 'emberhold' else 2800, 1.0 if f == 'emberhold' else 0.85)
    if f == 'emberhold':
        lance = lay((S('ki', f'impactPlate_heavy_{ri(5):03d}', g=0), 0, 0), (S('ki', f'impactMetal_heavy_{ri(5):03d}', g=-1), 0.004, 0),
                    (S('thwack', f'thwack-0{5 + v}', g=-3, f_lp=4000), 0.012, 0), (S('shield', f'impact_{3 + 3 * v}', g=-3), 0.0, 0))
        clash = S('sword', pickv(['sword_clash_5', 'sword_clash_9', 'sword_clash_3'], v), g=-3, p=.88)
        y = lay((lance, 0, 0), (th, 0, -1), (crack_t(-3, v), 0, 0), (clash, 0.06, -4), (cl, 0.1, -3),
                (ring(180 + 40 * v, 1.8, -17), 0.02, 0), (S('kr', 'metalPot1', g=-14, p=.7), 0.1, 0))
        return R(y, EMB)
    cr = lay((S('ki', f'impactGlass_heavy_{ri(5):03d}', g=0), 0, 0), (S('ice', 'LedasLuzta3' if False else 'LedasLuzta33', g=-3), 0.0, 0),
             (S('ki', f'impactMetal_heavy_{ri(5):03d}', g=-2, p=.9), 0.01, 0))
    clash = S('sword', pickv(['sword_clash_7', 'sword_clash_2'], v), g=-3, p=1.05)
    y = lay((cr, 0, 0), (th, 0, -2), (crack_t(-3, v + 1), 0, 0), (clash, 0.05, -4), (cl, 0.12, -4), (ring(520, 1.6, -18), 0.03, 0),
            (shimmer(1.4, 2400, -12, 8), 0.1, 0))
    return R(y, RIME)


def hit_bishop(f, v):
    if f == 'emberhold':
        ex = S('expl4', pickv(['explosion2', 'explosions4'], v), g=0, f_lp=4500)
        fire = S('rpg', f'spell_fire_0{1 + v}', g=-2, p=0.85)
        crumble = lay((S('rock', 'rock_break_0', g=-3), 0.12, 0), (S('bfh', f'bfh1_rock_breaking_0{1 + v}', g=-4), .22, 0))
        crack_seams = scatter([S('bfh', f'bfh1_wood_breaking_0{i}', g=0, f_lp=5000) for i in (1, 2, 3, 4)], 9, .05, .6, -8, -18)
        y = lay((ex, 0, 0), (thump(80, 30, 1.2, .4, 0), 0, 0), (fire, 0.04, -3), (crumble, 0, -3), (crack_seams, 0, -6),
                (S('fire', 'LEGIT_FIR_Fire_Staff_12-Audio', 0.3, 1.6, g=-9), 0.1, 0))
        return dsp.reverb(y, 1.8, 0.28, 0.02, 4000)
    fr = S('freeze', 'freeze', g=-1)
    cs = S('icesp', 'coldsnap', g=-3, p=1.0 + .1 * v)
    sh = S('ice', 'LedasLuzta33', g=-2)
    hum = dsp.tone_bank([392, 784.5, 1180, 1568], [1, .6, .3, .2], [1.2, 1.0, .8, .6], 1.6)
    y = lay((fr, 0, 0), (cs, 0, -2), (sh, 0.35, -2), (thump(100, 44, .7, .22, -1), .33, 0), (hum / dsp.peak(hum), 0.3, -14),
            (shimmer(1.4, 2600, -10, 14), .4, 0), (crack_t(-3, v), .34, 0))
    return dsp.reverb(y, 2.6, 0.32, 0.02, 9000)


def hit_queen(f, v):
    if f == 'emberhold':
        hm = lay((S('smith', 'blacksmithhammer', g=0, p=.55), 0, 0), (S('ki', f'impactMining_{ri(5):03d}', g=0, p=.7), 0, 0),
                 (S('ki', f'impactPlate_heavy_{ri(5):03d}', g=0, p=.75), 0.004, 0))
        shock = S('rumble', 'low-rumbling-176033', 0.5, 3.0, g=-4, f_lp=400)
        shock = shock * np.minimum(1, t(len(shock)) / .12) * np.exp(-t(len(shock)) / 1.5)
        big = boom(58, 22, 2.6, 0, expl=('expl4', 'explosion1_0'), lpf=900)
        deb = scatter([S('bfh', f'bfh1_rock_falling_0{i}', g=0) for i in range(1, 10)], 14, .3, 2.2, -6, -24, .6, 1.1, 1.6)
        y = lay((hm, 0, 0), (big, 0, -1), (thump(52, 20, 2.2, .8, 0), 0, 0), (shock, .02, -2), (deb, 0, -3),
                (S('ding', 'ding_2', g=-8, p=.5, f_lp=3500), 0.02, 0), (crack_t(-1, v), 0, 0),
                (S('rpg', 'spell_fire_04', g=-8, p=.7), .1, 0))
        return dsp.reverb(y, 2.6, 0.3, 0.02, 3500)
    cut = dsp.whoosh(.45, 600, 7500, 1.0, .75)
    sl = S('kr', 'knifeSlice', g=-2, f_hp=800) + 0
    sl2 = S('sword', 'sword_8', g=-3, f_hp=1200, p=1.1)
    shat = lay((S('ice', 'LedasLuzta33', g=0), 0, 0), (S('ice', 'LedasLuzta4', g=-2), .08, 0), (S('bfh', 'bfh1_glass_breaking_06', g=-3), .02, 0),
               (S('bfh', 'bfh1_glass_breaking_01', g=-3), .15, 0))
    tinkle = scatter([S('bfh', f'bfh1_glass_falling_0{i}', g=0, f_hp=3000) for i in range(1, 5)] + [S('ice', 'LedasLuzta5', f_hp=3000)], 20, .35, 2.6, -8, -28, 1.0, 1.7, 1.4)
    groan = S('kr', 'creak2', g=-10, p=.5, f_lp=800)
    y = lay((cut, 0, -1), (sl, .18, -3), (sl2, .24, -4), (shat, .42, 0), (thump(85, 32, 1.1, .4, -1), .42, 0),
            (crack_t(-2, v + 1), .42, 0), (tinkle, 0, -1), (shimmer(2.0, 2200, -9, 18), .5, 0), (groan, .42, 0),
            (ring(660, 2.0, -17), .45, 0))
    return dsp.reverb(y, 3.2, 0.35, 0.025, 9000)


def hit_king(f, v):
    if f == 'emberhold':
        pre = dsp.reverse(dsp.whoosh(.5, 200, 1800, 1.0, .6)) * .8
        cl = lay((S('ki', f'impactMetal_heavy_{ri(5):03d}', g=0, p=.8), 0, 0), (S('ki', f'impactPlate_heavy_{ri(5):03d}', g=0, p=.8), .003, 0),
                 (S('thwack', f'thwack-0{8 + (v % 2)}', g=-2, f_lp=4000), .01, 0), (S('sword', 'sword_clash_10', g=-3, p=.8), .01, 0))
        slow = dsp.pitch(dsp.pad_to(cl, int(.9 * SR)), .5)
        slow = dsp.sweep_lp(slow, 5000, 200, 18)[: int(2.4 * SR)]
        whoomp = dsp.sub_drop(52, 17, 2.4, 1.0, False, 1.4)
        y = lay((pre, 0, -4), (cl, .45, 0), (thump(75, 30, 1.0, .35, 0), .45, 0), (slow, .55, -4),
                (whoomp / dsp.peak(whoomp), .6, 0), (crack_t(-2, v), .45, 0), (S('rpg', 'spell_fire_05', g=-8, p=.6), .55, 0),
                (S('rumble', 'low-rumbling-176033', 2.0, 2.4, g=-6, f_lp=300), .6, 0))
        return dsp.reverb(y, 2.4, .3, .02, 3500)
    # rime: ice spikes erupt (rising crack series), then backhand
    eruptions = []
    for i in range(7):
        tk = 0.0 + i * .075 + rr(0, .03)
        eruptions.append((S('ice', pickv(['LedasLuzta', 'LedasLuzta2', 'LedasLuzta4', 'LedasLuzta5', 'LedasLuzta33'], i + v), g=0, p=.8 + .08 * i, f_hp=300, dur=.5), tk, -i * .5))
    rise = dsp.reverse(S('icesp', 'coldsnap', g=-2, f_hp=700))[: int(.8 * SR)]
    back = lay((dsp.whoosh(.3, 500, 5500, 1, .5), .75, -2), (S('ki', f'impactPunch_heavy_{ri(5):03d}', g=0), 1.0, 0),
               (S('ki', f'impactMetal_heavy_{ri(5):03d}', g=-1, p=.9), 1.0, 0), (S('bfh', 'bfh1_glass_breaking_06', g=-1), 1.01, 0),
               (S('ice', 'LedasLuzta33', g=-1), 1.0, 0))
    tinkle = scatter([S('bfh', f'bfh1_glass_falling_0{i}', g=0, f_hp=3000) for i in range(1, 5)], 16, 1.1, 3.0, -8, -28, 1.0, 1.7, 1.3)
    y = lay(*eruptions, (rise, 0, -4), (back, 0, 0), (thump(70, 26, 1.6, .5, 0), .02, 0), (thump(90, 34, 1.2, .4, -1), 1.0, 0),
            (tinkle, 0, -1), (S('rumble', 'low-rumbling-176033', 0, 1.8, g=-6, f_lp=250), 0, 0), (shimmer(2.2, 2400, -10, 18), 1.0, 0))
    return dsp.reverb(y, 3.0, .33, .02, 9000)


for role, fn in (('pawn', hit_pawn), ('rook', hit_rook), ('knight', hit_knight), ('bishop', hit_bishop), ('queen', hit_queen), ('king', hit_king)):
    for f in ('emberhold', 'rime'):
        reg(f'hit:{role}:{f}', 2, 3, 1.0, role == 'pawn')(lambda v, fn=fn, f=f: fn(f, v))


# generic bronze / ice armour hit  (SfxName impact:*)
def impact_generic(f, v):
    if f == 'emberhold':
        y = lay((thump(105, 40, .6, .22), 0, 0), (S('ki', f'impactMetal_heavy_{ri(5):03d}', g=0), 0, 0), (S('ki', f'impactPlate_heavy_{ri(5):03d}', g=-1), .003, 0),
                (ring(210 + 15 * v, 1.4, -15), 0, 0), (S('sword', f'sword_clash_{1 + ri(10)}', g=-6, p=.9), .01, 0))
        return R(y, EMB)
    y = lay((thump(115, 50, .5, .18, -1), 0, 0), (S('ki', f'impactGlass_heavy_{ri(5):03d}', g=0), 0, 0), (S('ice', 'LedasLuzta', g=-3), .01, 0),
            (S('ki', f'impactMetal_medium_{ri(5):03d}', g=-4, p=.9), 0, 0), (shimmer(1.0, 2600, -12, 7), .02, 0))
    return R(y, RIME)


for f in ('emberhold', 'rime'):
    reg(f'impact:{f}', 3, 3, 0.95, True)(lambda v, f=f: impact_generic(f, v))


# ====================================================================== SHATTER / DEBRIS
def shatter(f, tier, v):
    """tier 0 light(pawn) 1 mid 2 heavy"""
    n = (6, 12, 22)[tier]
    dur = (0.9, 1.5, 2.5)[tier]
    sub = thump((120, 95, 70)[tier], (55, 40, 24)[tier], (.35, .6, 1.5)[tier], (.12, .2, .55)[tier], 0)
    if f == 'emberhold':
        ch = [S('bfh', f'bfh1_rock_breaking_0{1 + i}', g=0) for i in range(3)] + [S('bfh', f'bfh1_metal_falling_0{1 + i}', g=0) for i in range(5)] + \
             [S('bfh', f'bfh1_rock_falling_0{1 + i}', g=0) for i in range(9)] + [S('rock', 'rock_break_0')]
        chunks = scatter(ch, n, 0.02, dur, -2, -22, .65 + .1 * (2 - tier) * 0, 1.2 + .15 * (2 - tier), 1.5)
        body = lay((S('bfh', f'bfh1_rock_breaking_0{1 + (v + tier) % 3}', g=0, p=1.0 - .1 * tier), 0, 0),
                   (S('ki', f'impactMetal_heavy_{ri(5):03d}', g=-2, p=1.0 - .12 * tier), 0, 0),
                   (S('ki', f'impactPlate_heavy_{ri(5):03d}', g=-3, p=.9 - .08 * tier), .004, 0))
        hiss = dsp.hp(dsp.noise(dur), 4500) * dsp.env_exp(int(dur * SR), dur * .35, .02) * .35
        crackle = scatter([S('rpg', f'spell_fire_0{i}', g=0, f_hp=2000, dur=.15) for i in (1, 2, 3, 6)], 5 + 3 * tier, .1, dur * .9, -10, -20, .8, 1.4, 1.2)
        y = lay((body, 0, 0), (sub, 0, -1 + tier), (chunks, 0, -2), (hiss, .03, -8), (crackle, 0, -4))
        return dsp.reverb(y, 1.2 + .4 * tier, .28, .015, 4000)
    gl = [S('bfh', f'bfh1_glass_breaking_0{1 + i}', g=0, f_hp=1200) for i in range(6)] + [S('ice', nm, g=0, f_hp=800) for nm in ('LedasLuzta', 'LedasLuzta2', 'LedasLuzta33', 'LedasLuzta4', 'LedasLuzta5')]
    tink = [S('bfh', f'bfh1_glass_falling_0{1 + i}', g=0, f_hp=3000) for i in range(4)]
    body = lay((S('ice', pickv(['LedasLuzta33', 'LedasLuzta4', 'LedasLuzta5'], v + tier), g=0, p=1.0 - .08 * tier), 0, 0),
               (S('bfh', f'bfh1_glass_breaking_0{1 + (v + tier) % 6}', g=-2, p=.95 - .05 * tier), .003, 0),
               (S('ki', f'impactGlass_heavy_{ri(5):03d}', g=-3), 0, 0))
    chunks = scatter(gl, n, .02, dur * .6, -3, -20, .8, 1.5, 1.4)
    tinkles = scatter(tink, 8 + 6 * tier, .1, dur, -8, -26, 1.0, 1.8, 1.2)
    y = lay((body, 0, 0), (sub, 0, -2 + tier), (chunks, 0, -2), (tinkles, 0, -2), (shimmer(dur, 2800, -11, 6 + 4 * tier), .05, 0))
    return dsp.reverb(y, 1.8 + .6 * tier, .32, .015, 9000)


for f in ('emberhold', 'rime'):
    for tier, suf, nv in ((0, ':light', 2), (1, '', 2), (2, ':heavy', 2)):
        reg(f'shatter:{f}{suf}', nv, 3, 0.95, tier == 1)(lambda v, f=f, tier=tier: shatter(f, tier, v))


def debris(f, s, v):
    n = (3, 6, 11)[s]
    dur = (.45, .75, 1.3)[s]
    if f == 'emberhold':
        ch = [S('bfh', f'bfh1_rock_falling_0{i}', g=0) for i in range(1, 10)] + [S('bfh', f'bfh1_metal_hit_0{i}', g=0, p=.8) for i in range(1, 7)]
    else:
        ch = [S('bfh', f'bfh1_glass_falling_0{i}', g=0, f_hp=1500) for i in range(1, 5)] + [S('ice', 'LedasLuzta2', g=0)] + [S('bfh', f'bfh1_glass_hit_0{i}', g=0) for i in (1, 2)]
    y = scatter(ch, n, 0.0, dur, 0, -14, .75 - .1 * s, 1.3 - .1 * s, 1.3, dur=.4)
    th = thump((150, 120, 95)[s], (80, 60, 45)[s], .25 + .1 * s, .1, -4 + 2 * s)
    y = lay((y, 0, 0), (th, 0, -4))
    return dsp.reverb(y, .8, .2, .01, 4000 if f == 'emberhold' else 9000)


for f in ('emberhold', 'rime'):
    for s in range(3):
        reg(f'debris:{f}:s{s + 1}', 2, 1, (0.45, 0.6, 0.75)[s], False, lufs=-20 + 2 * s, cooldown=0.09)(lambda v, f=f, s=s: debris(f, s, v))
    alias(f'debris:{f}', f'debris:{f}:s2')


# ====================================================================== CAST / SUMMON / SPELL
def summon(f, v):
    dur = 1.7
    if f == 'emberhold':
        rise = dsp.whoosh(dur, 120, 2500, 1.2, .9)
        fire = S('fire', 'LEGIT_FIR_Fire_Staff_2-Audio', 0.3, dur, g=-3)
        fire = fire * np.minimum(1, t(len(fire)) / (dur * .8))
        forge = scatter([S('anvil', 'forger_0', g=0, dur=.5), S('smith', 'blacksmithhammer', g=0)], 5, .2, dur, -14, -6, .7, .9, .8)
        tone = np.sin(2 * np.pi * np.cumsum(np.geomspace(70, 240, int(dur * SR))) / SR) * np.linspace(0, 1, int(dur * SR)) ** 2
        end = lay((thump(80, 30, 1.0, .4, 0), dur, 0), (S('rpg', 'spell_fire_03', g=-3, p=.7), dur - .05, 0), (S('ki', 'impactMetal_heavy_001', g=-3, p=.8), dur, 0),
                  (ring(165, 1.8, -14), dur, 0))
        y = lay((rise, 0, -2), (fire, 0, -2), (forge, 0, -4), (tone * .4, 0, -5), (end, 0, 0))
        return dsp.reverb(y, 2.0, .3, .02, 4000)
    rise = dsp.whoosh(dur, 500, 9000, 1.0, .9)
    chimes = scatter([dsp.tone_bank([f0, f0 * 2.76], [1, .3], [.6, .3], .7) for f0 in (880, 1175, 1568, 2093, 2637)], 12, .0, dur, -22, -8, 1, 1, .8)
    tone = np.sin(2 * np.pi * np.cumsum(np.geomspace(400, 2000, int(dur * SR))) / SR) * np.linspace(0, 1, int(dur * SR)) ** 2
    frostn = S('freeze', 'freeze', 0, dur, g=-5)
    end = lay((thump(95, 40, .8, .3, -2), dur, 0), (S('ice', 'LedasLuzta33', g=-1), dur, 0), (shimmer(1.6, 2600, -9, 14), dur, 0), (S('bfh', 'bfh1_glass_breaking_01', g=-4), dur, 0))
    y = lay((rise, 0, -4), (chimes, 0, -2), (tone * .35, 0, -6), (frostn, 0, -3), (end, 0, 0))
    return dsp.reverb(y, 2.6, .34, .02, 9000)


def spell(f, v):
    dur = 2.0
    if f == 'emberhold':
        roar = dsp.sweep_lp(dsp.noise(dur, 'brown'), 300, 2800, 20)
        roar = roar * (np.minimum(1, t(len(roar)) / .5) * np.exp(-np.maximum(t(len(roar)) - 1.0, 0) / .6))
        roar /= dsp.peak(roar)
        fl = S('fire', pickv(['LEGIT_FIR_Fire_Staff_10-Audio', 'LEGIT_FIR_Fire_Staff_11-Audio'], v), 0.2, dur, g=-1)
        sp = S('rpg', f'spell_fire_0{3 + v}', g=-2, p=.8)
        y = lay((roar, 0, -4), (fl, 0, -1), (sp, .05, -2), (thump(70, 32, 1.2, .45, -2), .1, 0), (S('creature', 'monster_04', 0, 1.0, p=.9, g=-8, f_lp=2500), .15, 0))
        return dsp.reverb(y, 1.8, .26, .02, 4000)
    hum = dsp.tone_bank([220, 330, 440.5, 662, 880, 1330], [1, .6, .5, .3, .25, .15], [2.5] * 6, dur) * (1 + .15 * np.sin(2 * np.pi * 5.5 * t(int(dur * SR))))
    hum = hum * np.minimum(1, t(len(hum)) / .35) * np.exp(-np.maximum(t(len(hum)) - 1.3, 0) / .4)
    hum /= dsp.peak(hum)
    fr = S('freeze', 'freeze', g=-2)
    cr = scatter([S('ice', nm, g=0, f_hp=3000, dur=.2) for nm in ('LedasLuzta', 'LedasLuzta2', 'LedasLuzta5')] + [S('bfh', 'bfh1_glass_hit_01', f_hp=3000)], 16, .2, dur, -10, -20, 1, 1.6, 1.0)
    y = lay((hum, 0, -4), (fr, 0, -1), (S('icesp', 'ice', g=-4), .15, 0), (cr, 0, -2), (thump(110, 55, .6, .22, -4), 0, 0))
    return dsp.reverb(y, 2.4, .3, .02, 9000)


for f in ('emberhold', 'rime'):
    reg(f'summon:{f}', 2, 3, 0.9, False)(lambda v, f=f: summon(f, v))
    reg(f'spell:{f}', 2, 3, 0.9, False)(lambda v, f=f: spell(f, v))


# ====================================================================== CHECK / MATE / CASTLE / PROMOTE
@reg('check', 2, 3, 0.95, False)
def check(v):
    d1 = war_drum(0, 1.0, .9)
    d2 = war_drum(-2, .92, .9)
    h = horn(1.5, 98 + 12 * v, -3)
    y = lay((d1, 0, 0), (d2, .33, 0), (h, .45, -3), (crack_t(-6, v), 0, 0), (thump(65, 28, 1.2, .5, -2), .33, 0))
    return dsp.reverb(y, 2.2, .3, .02, 3800)


@reg('mate', 2, 3, 1.0, False)
def mate(v):
    gg = gong(55 + 6 * v, 5.0, 0)
    ch = choir(4.2, 73.4 * (1 + .12 * v), -4, True, .55)
    rolls = []
    for i in range(6):
        rolls.append((war_drum(-3 - (5 - i) * .8, .95 + .02 * i, .6), 1.2 + i * .38, 0))
    y = lay((gg, 0, 0), (thump(50, 20, 3, 1.4, 0), 0, 0), (ch, .6, -5), *rolls, (horn(2.0, 87, -5), .9, 0),
            (crowd(2.5, .5, -14, 2500, .85, 6.0, .5), 1.4, 0))
    return dsp.reverb(y, 3.0, .3, .03, 3500)


@reg('castle', 2, 2, 0.9, False)
def castle(v):
    w = S('winch', pickv(['winch_-_Marker_8', 'winch_-_Marker_9'], v), g=-3, f_lp=5500)
    gr = S('stonemove', 'stone_rock_or_wood_moved', g=-1, p=.7) + 0
    gr2 = S('boulder', 'move_boulder_0', g=-2, p=.8)
    cr = S('kr', pickv(['creak1', 'creak2'], v), g=-8, p=.7)
    th = lay((thump(80, 34, .8, .3, 0), 1.3, 0), (S('ki', 'impactPlate_heavy_002', g=0, p=.7), 1.3, 0), (S('bfh', 'bfh1_rock_falling_01', g=-6), 1.3, 0))
    th2 = lay((thump(90, 38, .5, .2, -3), .18, 0), (S('ki', 'impactMetal_heavy_003', g=-3, p=.8), .18, 0))
    y = lay((w, 0, -2), (gr, .05, -3), (gr2, .5, -4), (cr, .1, 0), (th2, 0, 0), (th, 0, 0))
    return dsp.reverb(y, 1.6, .28, .015, 3800)


@reg('promote:emberhold', 2, 2, 0.9, False)
def promote_e(v):
    base = 196 * (1 + .1 * v)
    anv = S('anvil', 'forger_0', 0, 1.2, g=-2, p=1.0)
    rg = ring(base * 2, 2.6, 0)
    rg2 = ring(base * 3, 2.2, -4)
    brass = horn(1.8, base / 2, -9, .35)
    shim = shimmer(1.8, 2000, -10, 12)
    y = lay((anv, 0, 0), (rg, .02, -3), (rg2, .12, -5), (brass, .1, 0), (shim, .25, 0), (thump(80, 36, .6, .25, -2), 0, 0),
            (S('rpg', 'spell_fire_06', g=-8, p=.9, f_hp=400), .05, 0))
    return dsp.reverb(y, 2.4, .32, .02, 5000)


@reg('promote:rime', 2, 2, 0.9, False)
def promote_r(v):
    notes = [523, 659, 784, 1047, 1319, 1568]
    layers = []
    for i, n in enumerate(notes):
        tb = dsp.tone_bank([n * (1 + .1 * v), n * 2.0 * (1 + .1 * v), n * 3.01 * (1 + .1 * v), n * 5.4], [1, .4, .25, .1], [1.2, .8, .6, .3], 1.8)
        layers.append((tb / dsp.peak(tb), i * .09, -i * .8))
    bloom = dsp.whoosh(.9, 1500, 9000, 1.0, .8) * .4
    y = lay(*layers, (bloom, 0, -4), (shimmer(2.0, 3000, -9, 16), .1, 0), (S('freeze', 'freeze', g=-9), 0, 0), (thump(120, 60, .5, .2, -6), 0, 0),
            (S('ki', 'impactGlass_light_001', g=-6), .0, 0))
    return dsp.reverb(y, 2.8, .36, .02, 9500)


alias('promote', 'promote:emberhold')


# ====================================================================== CLASH / DROP / KNEEL / TAUNT / KNIGHT EXTRAS
def clash(f, v, heavy):
    sw = S('sword', pickv(['sword_clash_%d' % i for i in range(1, 11)], v * 3 + ri(3)), g=0, p=(1.0 if f == 'emberhold' else 1.12) * (.85 if heavy else 1))
    body = S('ki', pickv(['impactMetal_heavy_%03d', 'impactPlate_heavy_%03d', 'impactMetal_medium_%03d'], v) % ri(5), g=-1, p=1 if f == 'emberhold' else 1.1)
    sh = S('shield', f'impact_{1 + ri(10)}', g=-4)
    rg = ring((300 if f == 'emberhold' else 780) * rr(.95, 1.1), 1.3, -15)
    parts = [(sw, 0, 0), (body, 0, -1), (sh, .01, -3), (rg, .01, 0), (thump(100, 45, .4, .15, -4 if not heavy else 0), 0, 0)]
    if f == 'rime':
        parts.append((S('ki', f'impactGlass_medium_{ri(5):03d}', g=-5, f_hp=2500), .01, 0))
    if heavy:
        parts.append((crowd(1.7, .3, -6, 3500 if f == 'emberhold' else 2800, 1.0 if f == 'emberhold' else .88), .1, 0))
        parts.append((thump(70, 30, .9, .3, 0), 0, 0))
    y = lay(*parts)
    return R(y, EMB if f == 'emberhold' else RIME)


for f in ('emberhold', 'rime'):
    reg(f'clash:{f}', 3, 2, 0.85, True, lufs=-16)(lambda v, f=f: clash(f, v, False))
    reg(f'clash:{f}:heavy', 2, 3, 0.95, False)(lambda v, f=f: clash(f, v, True))


def drop(f, v):
    bounces = []
    if f == 'emberhold':
        main = lay((S('bfh', pickv(['bfh1_metal_falling_01', 'bfh1_metal_falling_02'], v), g=0), 0, 0), (S('ki', f'impactMetal_heavy_{ri(5):03d}', g=0), 0, 0), (thump(95, 42, .5, .2, -3), 0, 0))
        for i, (tm, gg) in enumerate(((.28, -9), (.46, -15), (.58, -21))):
            bounces.append((S('ki', f'impactMetal_light_{ri(5):03d}', g=0, p=1 + .08 * i), tm, gg))
        rg = ring(340, 2.4, -12, .3)
        y = lay((main, 0, 0), *bounces, (rg, .01, 0), (S('ding', 'ding_3', g=-14, p=.9), .02, 0))
        return R(y, EMB)
    main = lay((S('ki', f'impactGlass_heavy_{ri(5):03d}', g=0), 0, 0), (S('ice', 'LedasLuzta4', g=-4), 0, 0), (thump(110, 52, .4, .15, -4), 0, 0), (S('ki', f'impactMetal_medium_{ri(5):03d}', g=-5, p=.9), 0, 0))
    for i, (tm, gg) in enumerate(((.24, -10), (.38, -16))):
        bounces.append((S('ki', f'impactGlass_light_{ri(5):03d}', g=0, p=1 + .1 * i), tm, gg))
    y = lay((main, 0, 0), *bounces, (ring(900, 2.0, -16), .01, 0), (shimmer(1.3, 3000, -11, 8), .05, 0))
    return R(y, RIME)


for f in ('emberhold', 'rime'):
    reg(f'drop:{f}', 2, 3, 0.85, False)(lambda v, f=f: drop(f, v))


@reg('kneel', 2, 2, 0.8, False, lufs=-16)
def kneel(v):
    y = lay((S('ki', f'impactPlate_medium_{ri(5):03d}', g=0, p=.85), 0, 0), (thump(85, 38, .6, .22, -1), 0, 0), (S('kr', 'dropLeather', g=-4), .02, 0),
            (S('rpg', f'chain_0{1 + ri(3)}', g=-8, f_hp=2000, dur=.4), .05, 0),
            (S('kr', pickv(['cloth1', 'cloth3', 'clothBelt'], v), g=-4), .2, 0), (S('kr', 'cloth4', g=-9), .5, 0),
            (S('ki', f'impactMetal_light_{ri(5):03d}', g=-9, p=.8), .3, 0))
    return dsp.reverb(y, 1.0, .22, .01, 4000)


def taunt(f, v):
    if f == 'emberhold':
        cry = lay((S('roar', 'monster_roar', 0.3 + 1.5 * v, 1.2, g=0, p=1.0 - .05 * v, f_hp=80), 0, 0),
                  (S('troll', 'troll-roars_0', 0.4 + 2 * v, 1.3, g=-3, p=.95, f_hp=80), .04, 0),
                  (S('creature', 'roar_02', g=-3, p=.85), .02, 0))
        cry = dsp.saturate(cry, 1.8)
        beat = lay((thump(110, 50, .35, .14, 0), .9, 0), (S('ki', f'impactPlate_heavy_{ri(5):03d}', g=-1), .9, 0), (S('shield', f'impact_{2 + v}', g=-2), .9, 0),
                   (thump(105, 48, .35, .14, -1), 1.2, 0), (S('ki', f'impactPlate_heavy_{ri(5):03d}', g=-2), 1.2, 0), (S('ki', f'impactMetal_heavy_{ri(5):03d}', g=-5), 1.2, 0))
        y = lay((cry, 0, 0), (beat, 0, 0), (crowd(1.8, .4, -9, 3000, 1.0), .2, 0))
        return R(y, EMB)
    gh = lay((S('chant', pickv(['chant4', 'chant8'], v), 0, 2.0, g=0, p=.7, f_lp=6000), 0, 0), (S('zombie', pickv(['zombie-16', 'zombie-17'], v), g=-2, p=.7), .1, 0),
             (S('creature', 'breath', g=-4, p=.7, f_hp=1500), 0, 0), (S('creature', 'howl', g=-4, p=.7), .2, 0))
    hiss = dsp.hp(dsp.noise(1.6), 4000) * (np.sin(np.pi * np.clip(t(int(1.6 * SR)) / 1.6, 0, 1)) ** 2) * .45
    y = lay((gh, 0, 0), (hiss, .1, -6), (thump(60, 28, 1.0, .4, -6), .3, 0))
    return dsp.reverb(y, 3.0, .45, .03, 6500)


for f in ('emberhold', 'rime'):
    reg(f'taunt:{f}', 2, 2, 0.9, False, lufs=-15)(lambda v, f=f: taunt(f, v))
    reg(f'gallop:{f}', 2, 2, 0.8, False)(lambda v, f=f: gallop(1.8, 0, 1, 'stone' if f == 'emberhold' else 'ice', .34 + .02 * v))
    reg(f'rear:{f}', 2, 3, 0.9, False)(lambda v, f=f: dsp.reverb(lay((creature_call('bellow' if f == 'emberhold' else 'whinny', 0, 1.0 + .06 * v, 1.2), 0, 0),
                                                                       (S('creature', 'nose', g=-6, p=.8), 0, 0),
                                                                       (S('ki', f'impactSoft_heavy_{ri(5):03d}', g=-5, p=.8), .0, 0)), 1.6, .3, .02, 5000 if f == 'emberhold' else 9000))


# ====================================================================== UI
def ui_proc(x, rt=0.5, wet=0.12):
    return dsp.reverb(x, rt, wet, .004, 8000)


UI = {
    'ui:click': (3, lambda v: lay((S('ku', pickv(['click1', 'click3', 'click4'], v), g=0), 0, 0), (S('kf', 'click_001', g=-9, f_lp=4000), 0, 0))),
    'ui:select': (2, lambda v: lay((S('kf', pickv(['select_003', 'select_004'], v), g=0), 0, 0), (S('ku', 'rollover3', g=-8), 0, 0))),
    'ui:hover': (2, lambda v: S('ku', pickv(['rollover1', 'rollover4'], v), g=0, f_lp=7000)),
    'ui:back': (2, lambda v: lay((S('kf', pickv(['back_002', 'back_003'], v), g=0), 0, 0), (S('kr', 'bookClose', g=-8, f_lp=3000), 0, 0))),
    'ui:book': (2, lambda v: lay((S('kr', pickv(['bookOpen', 'bookPlace2'], v), g=0), 0, 0), (S('kf', 'open_001', g=-8, f_lp=3500), 0, 0))),
    'ui:page': (2, lambda v: lay((S('kr', pickv(['bookFlip1', 'bookFlip2'], v), g=0), 0, 0), (S('kf', 'tick_004', g=-14), 0, 0))),
    'ui:knob': (2, lambda v: lay((S('ku', pickv(['switch12', 'switch13'], v), g=0, f_hp=300), 0, 0), (S('kf', 'toggle_004', g=-4), 0, 0))),
    'ui:switch': (2, lambda v: lay((S('ku', pickv(['switch7', 'switch28'], v), g=0), 0, 0), (S('kf', 'toggle_001', g=-6), 0, 0))),
    'ui:button': (2, lambda v: lay((S('ku', pickv(['mouseclick1', 'click5'], v), g=0), 0, 0), (S('kf', pickv(['confirmation_001', 'confirmation_003'], v), g=-10, f_lp=5000), .01, 0))),
    'loading:done': (1, lambda v: lay((S('kf', 'confirmation_002', g=-2), 0, 0), (S('kf', 'bong_001', g=-6, p=.5), 0, 0), (thump(100, 50, .6, .2, -8), 0, 0),
                                       (S('ki', 'impactBell_heavy_000', g=-8, p=.8), .0, 0))),
}
for k, (nv, fn) in UI.items():
    if k == 'loading:done':
        reg(k, nv, 2, 0.7, False, lufs=-18)(lambda v, fn=fn: dsp.reverb(fn(v), 1.4, .25, .01, 6000))
    else:
        reg(k, nv, 1, 0.5, True, lufs=-24, comp=(-14, 2.0), maxlen=0.45)(lambda v, fn=fn: ui_proc(fn(v)))


# ====================================================================== CONTRACT v1.4 CUES
# Slides (loop + start lurch + stop settle), shield flash / break, armour hits, landings, draw sting.
SLIDE_L, SLIDE_X = 2.4, 0.4          # loop length / cross-fade (s)


def _lfo(n, cycles, depth, phase=0.0):
    """Loop-safe slow amplitude wobble: `cycles` whole periods across n samples."""
    return 1 + depth * np.sin(2 * np.pi * cycles * np.arange(n) / n + phase)


def slide_body(f, v):
    D = SLIDE_L + SLIDE_X
    n = int(D * SR)
    r = dsp.rng
    if f == 'emberhold':
        # dragged concrete slab: stone-door grind + boulder drag, stick-slip rumble, gritty top, sub bed
        door = S('sdoor', 'stone_door', p=0.85 - 0.04 * v, f_lp=3200, tr=False)
        drag = S('boulder', 'move_boulder_0', p=0.78, tr=False)
        scr = S('scrape', 'scrape-1', p=0.7, f_lp=2600, tr=False)
        a = granular([door], D, 0.17, 26)
        b = granular([drag], D, 0.24, 13)
        c = granular([scr], D, 0.14, 20)
        env = stick_slip(D, 8.0 + v, 0.55, 0.35)
        brown = dsp.hp(dsp.lp(dsp.noise(D, 'brown'), 420), 70)
        grit = dsp.bp(dsp.noise(D), 500, 3200) * (env ** 1.4)
        bed = dsp.lp(np.resize(S('rumble', 'low-rumbling-176033', 2.0 + 5 * v, 5.0, tr=False, f_lp=150), n), 150)
        a, b, c = dsp.hp(a, 140, 2), dsp.hp(b, 120, 2), dsp.hp(c, 220, 2)
        y = (a * 1.0 + b * 0.55) * (0.5 + 0.5 * env) + c * 0.6 * env + brown * 0.08 * env + grit * 0.4 + bed * 0.04
        y = y * _lfo(n, 2 + v, 0.14)
        y = dsp.saturate(y / np.max(np.abs(y)), 1.5)
        y = dsp.lp(y, 5200)
    else:
        # ice on stone: scraping rasp, tree-creak groan pitched down, crystalline crackle
        s1 = S('scrape', 'scrape-1', p=0.82, f_hp=450, tr=False)
        s2 = S('scrape', 'scrape-2', p=0.9 + 0.05 * v, f_hp=450, tr=False)
        cr = S('screak', 'tree_creak', 0.5 + 2 * v, 3.0, p=0.5, f_lp=2600, tr=False)
        rasp = granular([s1, s2], D, 0.13, 22)
        groan = granular([cr], D, 0.4, 8)
        env = stick_slip(D, 10.5 + v, 0.5, 0.3)
        band = dsp.bp(dsp.noise(D), 700, 2600) * env
        low = dsp.lp(dsp.noise(D, 'brown'), 220)
        # crystalline crackle: Poisson ticks of glass / ice slivers, high-passed and pitched up
        tick = [S('ki', f'impactGlass_light_{k:03d}', 0, 0.09, p=1.5 + 0.2 * k, f_hp=4200) for k in range(5)] + \
               [S('ice', 'LedasLuzta2', 0.0, 0.07, p=1.3, f_hp=5000), S('ice', 'LedasLuzta', 0.1, 0.06, p=1.6, f_hp=5000)]
        layers = []
        tt = 0.0
        while tt < D - 0.1:
            layers.append((tick[int(r.integers(len(tick)))], tt, -float(r.uniform(5, 17))))
            tt += float(r.exponential(1 / 11.0))
        crackle = dsp.mix(layers, D)
        y = rasp * (0.5 + 0.5 * env) * 0.8 + groan * 0.85 + band * 0.32 + low * 0.35 + crackle * 0.55
        y = y * _lfo(n, 3 + v, 0.12, 1.0)
        y = dsp.lp(y / np.max(np.abs(y)), 9000)
    return make_loop(y, SLIDE_L, SLIDE_X)


def slide_start(f, v):
    if f == 'emberhold':
        a = S('stnomv', 'stone_rock_or_wood_moved_no_tick', p=0.8, g=0)
        b = S('mech', 'clank1', p=0.6, f_lp=2200, g=-8, tr=False)
        g = granular([S('sdoor', 'stone_door', p=0.8, f_lp=3000, tr=False)], 0.5, 0.15, 24)
        g = g * np.minimum(1, t(len(g)) / 0.12)
        y = lay((a, 0.0, 0), (thump(70, 38, .45, .16, -3), 0, 0), (b, 0.0, 0), (g, 0.05, -4), (crack_t(-14, v, False), 0, 0))
        return R(y, dict(rt=0.9, wet=0.2, damp=4200))
    a = S('scrape', pickv(['scrape-2', 'scrape-1'], v), 0, 0.5, p=0.85, f_hp=400, g=-1)
    b = S('ice', 'LedasLuzta2', g=-8, f_hp=3000)
    c = S('screak', 'tree_creak', 1.0 + v, 0.5, p=0.6, f_lp=3000, g=-4, tr=False)
    y = lay((a, 0, 0), (b, 0.05, 0), (c, 0.0, 0), (thump(100, 52, .35, .12, -5), 0, 0))
    return R(y, dict(rt=1.2, wet=0.24, damp=9000))


def slide_stop(f, v):
    if f == 'emberhold':
        a = S('boulder', 'boulder_drop_0', p=0.82, g=-1)
        b = S('ki', f'impactPlate_heavy_{ri(5):03d}', f_lp=2500, g=-3)
        dust = dsp.lp(dsp.noise(0.7), 1500) * dsp.env_exp(int(0.7 * SR), 0.18) * 0.35
        rock = S('bfh', f'bfh1_rock_falling_0{1 + ri(9)}', f_lp=3000, g=-10)
        y = lay((thump(62, 30, .85, .3, 0), 0, 0), (a, 0, 0), (b, 0.0, 0), (dust, 0.03, -6), (rock, 0.12, 0))
        return R(y, dict(rt=1.1, wet=0.25, damp=4200))
    a = S('ki', f'impactGlass_heavy_{ri(5):03d}', f_lp=4500, g=-3, p=0.85)
    b = S('ice', pickv(['LedasLuzta5', 'LedasLuzta4'], v), 0, 0.6, g=-10, f_hp=800)
    c = S('ki', f'footstep_snow_{ri(5):03d}', g=-8)
    y = lay((thump(85, 40, .7, .25, -1), 0, 0), (a, 0, 0), (b, 0.04, 0), (c, 0.0, 0), (shimmer(.8, 2800, -14, 8), 0.1, 0))
    return R(y, dict(rt=1.5, wet=0.28, damp=9000))


for f in ('emberhold', 'rime'):
    reg(f'slide:{f}', 2, 2, 0.8, True, lufs=-20, loop=True)(lambda v, f=f: slide_body(f, v))
    reg(f'slide:{f}:start', 2, 2, 0.85, True, lufs=-17, maxlen=0.9)(lambda v, f=f: slide_start(f, v))
    reg(f'slide:{f}:stop', 2, 2, 0.9, True, lufs=-16, maxlen=1.2)(lambda v, f=f: slide_stop(f, v))


def wood_crack(i, dur=0.5, p=1.0, g=0.0):
    """One crack cut from the 35-wooden-cracks compilation (onsets found once)."""
    w = dsp.load('o_35-wooden-crackshitsdestructions', 'wood')[: int(40 * SR)]
    on = onsets(w, 0.45, 0.28)
    o = on[i % len(on)]
    c = dsp.pitch(dsp.seg(w, max(0, o - 0.01), dur), p)
    return dsp.fade(c / dsp.peak(c), 0.001, 0.08) * db(g)


def shield_flash(f, v):
    if f == 'emberhold':
        base = [740, 880, 988][v % 3]
        bell1 = ring(base, 1.5, 0, 1.0)
        bell2 = ring(base * 1.5, 1.0, -9)
        ding = S('ding', pickv(['ding_1', 'ding_2', 'ding_3'], v), g=-5, p=base / 1100.0)
        parry = S('shield', f'impact_{pickv([2, 7, 8], v)}', 0, 0.3, f_hp=900, g=-3)
        kb = S('ki', f'impactBell_heavy_{v:03d}', g=-6)
        light = dsp.whoosh(0.3, 1400, 9000, 1.6, 0.3) * db(-6)
        y = lay((parry, 0, 0), (crack_t(-3, v), 0, 0), (bell1, 0.004, -3), (bell2, 0.012, 0), (ding, 0, 0), (kb, 0, 0), (light, 0.0, 0))
        return dsp.reverb(y, 0.9, .22, .01, 5200)
    base = [2100, 2600, 3100][v % 3]
    gl = dsp.tone_bank([base, base * 2.41, base * 3.8, base * 5.6], [1, .6, .45, .3], [.9, .6, .4, .25], 1.6)
    gl = gl / dsp.peak(gl)
    ig = S('ki', f'impactGlass_light_{v:03d}', g=-2, f_hp=1500)
    ice = S('ice', 'LedasLuzta2', g=-9, f_hp=3000)
    light = dsp.whoosh(0.32, 3200, 12500, 1.8, 0.3) * db(-6)
    y = lay((ig, 0, 0), (gl, 0.003, -5), (ice, 0.01, 0), (shimmer(1.0, 2300, -9, 10), 0.03, 0), (light, 0, 0), (thump(160, 90, .2, .06, -16), 0, 0))
    return dsp.reverb(y, 1.4, .28, .012, 10000)


def shield_break(f, v):
    if f == 'emberhold':
        splints = [(wood_crack(3 + 5 * v + k, 0.45, 1.0 - 0.05 * k, -k * 2), 0.04 * k, 0) for k in range(3)]
        plank = S('ki', f'impactPlank_medium_{v:03d}', g=-2)
        tear = S('ki', f'impactMetal_heavy_{ri(5):03d}', g=-3, p=0.9)
        rivet_src = [S('mech', 'lightclunk1', f_hp=1500, dur=0.12), S('ki', f'impactMetal_light_{ri(5):03d}', 0, 0.1, f_hp=2500),
                     S('ki', f'impactMetal_light_{ri(5):03d}', 0, 0.1, f_hp=3200), S('kr', 'handleCoins', 0, 0.14, f_hp=2200)]
        rivets = scatter(rivet_src, 18, 0.12, 1.1, -2, -20, 1.0, 1.9, 1.6, 0.12)
        y = lay(*splints, (plank, 0, 0), (tear, 0.02, 0), (rivets, 0.08, 0), (thump(78, 34, .8, .28, -2), 0, 0),
                (S('bfh', f'bfh1_rock_falling_0{1 + ri(9)}', f_lp=3500, g=-12), 0.05, 0))
        return dsp.reverb(y, 1.2, .26, .01, 4800)
    # Rime guard: a slab of ice cracks (rising crack rate), then bursts and tinkles away
    ticks = []
    tt = 0.0
    k = 0
    while tt < 0.6:
        amp = -14 + 12 * (tt / 0.6)
        c = dsp.hp(dsp.noise(0.012), 3200) * dsp.env_exp(int(0.012 * SR), 0.003)
        ticks.append((c / dsp.peak(c), tt, amp))
        tt += 0.07 * (0.97 ** k) * float(dsp.rng.uniform(0.6, 1.3))
        k += 1
    pre = dsp.mix(ticks, 0.62)
    slab = S('ice', pickv(['LedasLuzta33', 'LedasLuzta4'], v), g=-1)
    glass = S('glassb', 'glass_breaking', g=-4, p=0.9)
    big = S('ki', f'impactGlass_heavy_{ri(5):03d}', g=-3)
    bits = scatter([S('ki', f'impactGlass_light_{k2:03d}', 0, 0.1, f_hp=2500) for k2 in range(5)], 16, 0.05, 1.2, -4, -20, 1.0, 1.8, 1.6, 0.12)
    y = lay((pre, 0, -2), (slab, 0.58, 0), (glass, 0.6, 0), (big, 0.6, 0), (thump(90, 38, .9, .3, -2), 0.6, 0), (bits, 0.66, 0), (shimmer(1.2, 2500, -10, 16), 0.8, 0))
    return dsp.reverb(y, 1.9, .3, .012, 9500)


for f in ('emberhold', 'rime'):
    reg(f'shield:flash:{f}', 3, 2, 0.85, False, lufs=-15, maxlen=1.7, cooldown=0.08)(lambda v, f=f: shield_flash(f, v))
    reg(f'shield:break:{f}', 2, 3, 0.9, False, lufs=-14, maxlen=2.6)(lambda v, f=f: shield_break(f, v))


def armour_hit(f, heavy, v):
    k = ri(5)
    if f == 'emberhold':
        a = S('ki', f'impactPlate_{"heavy" if heavy else "medium"}_{k:03d}', g=0)
        b = S('shield', f'impact_{pickv([1, 3, 5, 6, 9], v)}', 0, 0.35, f_lp=4500, g=-4)
        c = S('rpg', f'chain_0{1 + ri(3)}', f_hp=2000, g=-12, dur=0.25)
        th = thump(72, 32, .8, .26, -2) if heavy else thump(95, 44, .5, .16, -2)
        y = lay((a, 0, 0), (b, 0.003, 0), (c, 0.02, 0), (th, 0, 0))
        return dsp.reverb(y, 1.2 if heavy else 0.9, .2, .01, 4500)
    a = S('ki', f'impactMetal_{"heavy" if heavy else "medium"}_{k:03d}', g=-1, f_lp=6500)
    b = S('ki', f'impactGlass_{"medium" if heavy else "light"}_{ri(5):03d}', 0, 0.2, f_hp=2500, g=-5)
    c = S('ki', f'footstep_snow_{ri(5):03d}', g=-7, f_hp=700)
    th = thump(80, 50, .6, .2, -4) if heavy else thump(105, 50, .4, .12, -4)
    y = lay((a, 0, 0), (b, 0.004, 0), (c, 0.0, 0), (th, 0, 0))
    return dsp.reverb(y, 1.3, .22, .01, 9000)


for f in ('emberhold', 'rime'):
    reg(f'armour:hit:{f}', 3, 2, 0.75, False, lufs=-16, maxlen=0.9, cooldown=0.06)(lambda v, f=f: armour_hit(f, False, v))
    reg(f'armour:hit:{f}:heavy', 3, 2, 0.9, False, lufs=-14, maxlen=1.4, cooldown=0.1)(lambda v, f=f: armour_hit(f, True, v))


def land_fx(f, tier, v):
    k = ri(5)
    th = {1: (88, 42, .35, .12), 2: (74, 34, .7, .24), 3: (60, 26, 1.1, .38)}[tier]
    if f == 'emberhold':
        if tier == 1:
            parts = [(S('ki', f'footstep_concrete_{k:03d}', g=0), 0, 0), (S('ki', f'impactPlate_light_{ri(5):03d}', f_lp=3000, g=-6), 0, 0)]
        elif tier == 2:
            parts = [(S('ki', f'impactPlate_heavy_{k:03d}', f_lp=3500, g=-1), 0, 0), (S('boulder', 'boulder_drop_0', p=1.1, g=-6), 0, 0),
                     (S('bfh', f'bfh1_rock_falling_0{1 + ri(9)}', f_lp=3500, g=-12), 0.05, 0)]
        else:
            parts = [(S('ki', f'impactPlate_heavy_{k:03d}', g=-1), 0, 0), (S('boulder', 'boulder_drop_0', p=0.8, g=-2), 0, 0),
                     (S('bfh', f'bfh1_rock_falling_0{1 + ri(9)}', f_lp=4000, g=-6), 0.06, 0), (S('stonemove', 'stone_rock_or_wood_moved', p=0.7, g=-8), 0.1, 0)]
        dust = dsp.lp(dsp.noise(0.6), 1400) * dsp.env_exp(int(0.6 * SR), 0.12) * 0.3
        y = lay(*parts, (thump(*th, -1), 0, 0), (dust, 0.02, -6 + 2 * tier))
        return dsp.reverb(y, 0.8 + 0.3 * tier, .24, .01, 4200)
    if tier == 1:
        parts = [(S('ki', f'footstep_snow_{k:03d}', g=0), 0, 0), (S('ki', f'impactGlass_light_{ri(5):03d}', 0, 0.12, f_hp=3000, g=-8), 0.005, 0)]
    elif tier == 2:
        parts = [(S('ki', f'impactGlass_heavy_{k:03d}', f_lp=5000, g=-2), 0, 0), (S('ice', 'LedasLuzta5', 0, 0.5, f_hp=700, g=-10), 0.03, 0)]
    else:
        parts = [(S('ki', f'impactGlass_heavy_{k:03d}', g=-1), 0, 0), (S('ice', 'LedasLuzta33', g=-6), 0.02, 0), (S('glassb', 'glass_breaking', g=-10, f_lp=6000), 0.05, 0),
                 (shimmer(.9, 2600, -14, 8), 0.1, 0)]
    y = lay(*parts, (thump(th[0] + 16, th[1] + 8, th[2], th[3], -4 + (tier == 3) * 3), 0, 0))
    return dsp.reverb(y, 1.0 + 0.3 * tier, .26, .01, 9000)


for f in ('emberhold', 'rime'):
    for tier, (lufs, ml, g) in {1: (-18, 0.6, 0.6), 2: (-16, 0.95, 0.8), 3: (-14, 1.5, 0.95)}.items():
        reg(f'land:{f}:s{tier}', 2, 2, g, False, lufs=lufs, maxlen=ml, cooldown=0.05)(lambda v, f=f, tier=tier: land_fx(f, tier, v))
    alias(f'land:{f}', f'land:{f}:s2')


@reg('sting:draw', 1, 2, 0.8, False, lufs=-17, maxlen=3.8)
def draw_sting(v):
    h = dsp.lp(horn(2.2, 82, 0, 0.5), 1900)
    w = S('wind', 'wind2', 4.0, 3.0, g=-4, f_hp=250, f_lp=3500, tr=False)
    w = w * np.sin(np.pi * np.clip(t(len(w)) / (len(w) / SR), 0, 1)) ** 2
    y = lay((h, 0, 0), (w, 0.0, -6), (war_drum(-3, 0.62, 1.0), 0.1, 0), (thump(55, 28, 1.4, .5, -3), 0.1, 0))
    return dsp.reverb(y, 2.8, .4, .03, 5000)


def default_maxlen(key):
    rules = [('move:step', .4), ('step:knight', .4), ('step:heavy', .75), ('attack:whoosh', 1.1), ('hit:', 3.0), ('impact:', 1.5),
             ('shatter:', None), ('debris:', None), ('summon', 2.4), ('spell', 2.4), ('check', 2.4), ('mate', 5.2), ('castle', 2.2),
             ('promote', 2.6), ('clash:', None), ('drop:', 1.8), ('kneel', 1.0), ('taunt', 2.4), ('gallop', 2.3), ('rear', 1.7),
             ('loading', 1.2)]
    tiers = {'shatter:': {':light': 1.2, ':heavy': 2.9, '': 2.0}, 'debris:': {':s1': .55, ':s2': .85, ':s3': 1.3}, 'clash:': {':heavy': 2.0, '': 1.1}}
    for pre, v in rules:
        if key.startswith(pre):
            if v is None:
                for suf, vv in tiers[pre].items():
                    if suf and key.endswith(suf):
                        return vv
                return tiers[pre]['']
            return v
    return None


# ====================================================================== driver
def build(prefixes):
    meta = {}
    for key, r in REG.items():
        if prefixes and not any(key.startswith(p) for p in prefixes):
            continue
        files = []
        for v in range(r['nvar']):
            seed(key, v)
            x = r['fn'](v)
            if r['loop']:
                path, y, region = finish_loop(key, v, x, r['lufs'])
            else:
                path, y = finish(key, v, x, r['lufs'], r['comp'], maxlen=r['maxlen'] or default_maxlen(key))
                region = None
            files.append(os.path.basename(path)[:-4])
        meta[key] = dict(files=files, gain=r['gain'], priority=r['pri'], preload=r['preload'], cooldown=r['cooldown'], loop=region)
        print(f'{key:28s} {len(files)} vars  {len(y)/SR:5.2f}s', flush=True)
    return meta


if __name__ == '__main__':
    meta = build(sys.argv[1:])
    mp = os.path.join(dsp.HERE, 'work', 'registry.json')
    prev = json.load(open(mp)) if os.path.exists(mp) and sys.argv[1:] else {}
    old = dict(prev.get('entries', {}))
    old.update(meta)
    json.dump(dict(entries=old, aliases={**prev.get('aliases', {}), **ALIASES}), open(mp, 'w'), indent=1)
