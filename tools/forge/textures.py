"""textures.py - procedural, tileable PBR texture sets + per-vertex baking (AO, edge wear).

All textures are generated with numpy/scipy (FFT noise, periodic Voronoi) so they tile.  Each material
returns a `TextureSet`: baseColor (sRGB), ORM (R=AO G=roughness B=metal), tangent-space normal
(OpenGL +Y), optional emissive, plus the glTF material factors.

Material names follow art-bible section 6:  EH_Bronze EH_Steel EH_Leather EH_Fur EH_Cloth EH_Stone EH_Ember
EH_Interior  RH_Obsidian RH_Ice RH_Frost RH_Silver RH_Glow RH_Interior.   Register your own with
`register(MaterialDef(...))` (e.g. `EH_Wood`) - keep the EH_/RH_ prefix.

Baking:  `bake_vertex_colors(meshes, material_names)` -> list of (n,4) COLOR_0 arrays containing voxel-traced
ambient occlusion (grime tinted) and curvature-driven edge wear.  Vertex colours multiply baseColor.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

import numpy as np
from PIL import Image, ImageFile
from scipy import ndimage, sparse
from scipy.spatial import cKDTree

from geom import Mesh, fbm3, smoothstep

DEFAULT_RES = 256   # tiles are 0.25 m => 1024 px/m (pipeline texel density); keeps GLBs small
ImageFile.MAXBLOCK = 1 << 24   # lets Pillow optimise big JPEG/PNG writes to memory


# ------------------------------------------------------------------ noise primitives (tileable)
def hexcol(h: int):
    return np.array([(h >> 16) & 255, (h >> 8) & 255, h & 255], dtype=np.float64) / 255.0


def fft_noise(n, beta=2.0, seed=0, fmin=1.0, fmax=None, aniso=(1.0, 1.0)):
    """Tileable noise, ~N(0.5, 0.17) clipped to 0..1. amplitude spectrum ~ f^(-beta/2). aniso=(kx, ky) scales the
    frequency axes before filtering: a large ky makes features long along y (streaks running vertically)."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((n, n))
    F = np.fft.fft2(w)
    fy = np.fft.fftfreq(n) * n
    fx = np.fft.fftfreq(n) * n
    FX, FY = np.meshgrid(fx, fy)
    fr = np.sqrt((FX * aniso[0]) ** 2 + (FY * aniso[1]) ** 2)
    fmax = fmax if fmax else n / 2
    filt = np.where((fr >= fmin) & (fr <= fmax), np.maximum(fr, 1e-6) ** (-beta / 2.0), 0.0)
    out = np.real(np.fft.ifft2(F * filt))
    out = (out - out.mean()) / (out.std() + 1e-12)
    return np.clip(0.5 + out * 0.17, 0.0, 1.0)


def voronoi(n, cells, seed=0, jitter=0.95, warp=None, warp_amt=0.0):
    """Periodic Voronoi on an n x n grid with ~cells x cells sites.
    Returns dict(f1, f2, id, dx, dy) with distances normalised by the mean cell size."""
    rng = np.random.default_rng(seed)
    g = (np.arange(cells) + 0.5) / cells
    gx, gy = np.meshgrid(g, g)
    pts = np.stack([gx.ravel(), gy.ravel()], 1) + (rng.random((cells * cells, 2)) - 0.5) * jitter / cells
    pts = np.mod(pts, 1.0)
    tree = cKDTree(pts, boxsize=1.0)
    c = (np.arange(n) + 0.5) / n
    X, Y = np.meshgrid(c, c)
    if warp is not None and warp_amt > 0:
        X = np.mod(X + (warp[0] - 0.5) * warp_amt, 1.0)
        Y = np.mod(Y + (warp[1] - 0.5) * warp_amt, 1.0)
    q = np.stack([X.ravel(), Y.ravel()], 1)
    d, idx = tree.query(q, k=2)
    cell = 1.0 / cells
    d1, d2, i1 = d[:, 0] / cell, d[:, 1] / cell, idx[:, 0]
    dv = q - pts[i1]
    dv = dv - np.round(dv)  # wrapped offset
    return {"f1": d1.reshape(n, n), "f2": d2.reshape(n, n), "id": i1.reshape(n, n), "n_sites": len(pts),
            "dx": (dv[:, 0] / cell).reshape(n, n), "dy": (dv[:, 1] / cell).reshape(n, n), "rng": rng}


def blur(a, sigma):
    return ndimage.gaussian_filter(a, sigma, mode="wrap")


def norm01(a, lo=None, hi=None):
    lo = a.min() if lo is None else lo
    hi = a.max() if hi is None else hi
    return np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)


def smooth(e0, e1, x):
    return smoothstep(e0, e1, x)


def height_to_normal(h, strength=6.0):
    """Tileable tangent-space normal map (OpenGL, +Y up) from a height field in 0..1."""
    n = h.shape[0]
    dhdx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * n
    dhdy_row = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * n  # d/d(row): rows go down in the image
    s = strength / 64.0
    nx = -dhdx * s
    ny = dhdy_row * s  # image-up component of the normal
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5


def mix(a, b, t):
    t = np.asarray(t)
    if t.ndim == 2 and np.ndim(a) == 3:
        t = t[..., None]
    return a * (1 - t) + b * t


def to_u8(a):
    return np.clip(np.round(np.asarray(a) * 255.0), 0, 255).astype(np.uint8)


def encode_png(arr_u8, optimize=True) -> bytes:
    im = Image.fromarray(arr_u8)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=optimize, compress_level=9)
    return buf.getvalue()


def encode_jpeg(arr_u8, quality=88) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr_u8).save(buf, format="JPEG", quality=quality, subsampling=0, optimize=True)
    return buf.getvalue()


# ------------------------------------------------------------------ texture sets
@dataclass
class TextureSet:
    name: str
    albedo: np.ndarray            # (n,n,3) float 0..1 sRGB
    rough: np.ndarray             # (n,n)
    metal: np.ndarray             # (n,n)
    ao: np.ndarray                # (n,n)
    height: np.ndarray            # (n,n) 0..1
    normal_strength: float = 6.0
    emissive: np.ndarray | None = None   # (n,n,3) sRGB, scaled by emissive_strength in the material
    emissive_strength: float = 1.0
    tile: float = 0.30            # metres per texture repeat (UV scale used by the pieces)
    # glTF material extras
    transmission: float | None = None
    ior: float | None = None
    thickness: float | None = None
    attenuation_color: tuple | None = None
    attenuation_distance: float | None = None
    double_sided: bool = False
    # vertex-bake behaviour
    ao_strength: float = 0.9       # how strongly baked AO darkens
    wear: float = 0.0              # edge wear amount (0 = none)
    wear_boost: float = 1.0
    grime: tuple = (0.16, 0.12, 0.09)   # colour that AO cavities fade toward
    baked_tone: float = 0.88       # vertex colour of flat unworn surface (leaves headroom for worn edges)
    jpeg: bool = True

    def images(self):
        """Encoded images: (base, orm, normal, emissive|None, mime_for_colour)."""
        if self.jpeg:
            base = encode_jpeg(to_u8(self.albedo), 84)
            orm = encode_jpeg(to_u8(np.stack([self.ao, self.rough, self.metal], -1)), 82)
            emi = encode_jpeg(to_u8(self.emissive), 90) if self.emissive is not None else None
            mime = "image/jpeg"
        else:
            base = encode_png(to_u8(self.albedo))
            orm = encode_png(to_u8(np.stack([self.ao, self.rough, self.metal], -1)))
            emi = encode_png(to_u8(self.emissive)) if self.emissive is not None else None
            mime = "image/png"
        nrm = to_u8(height_to_normal(self.height, self.normal_strength))
        normal = encode_jpeg(nrm, 78) if self.jpeg else encode_png(nrm)
        return base, orm, normal, emi, mime


@dataclass
class MaterialDef:
    name: str
    gen: Callable[[int, int], TextureSet]
    seed: int = 1


REGISTRY: dict[str, MaterialDef] = {}


def register(d: MaterialDef):
    REGISTRY[d.name] = d
    return d


def _ts(name, **kw):
    return TextureSet(name=name, **kw)


# ---------------------------------------------------------------- Emberhold
def gen_bronze(n, seed):
    """Hammered bronze that reads as metal at small size: calm facets + large-scale tarnish/polish variation."""
    v = voronoi(n, 16, seed)
    rng = v["rng"]
    depth = rng.random(v["n_sites"])[v["id"]] * 0.5 + 0.5
    bowl = (1 - np.clip(v["f1"] / 0.9, 0, 1) ** 2) * depth
    low = fft_noise(n, 2.6, seed + 1, 1, 8)
    big = fft_noise(n, 3.2, seed + 6, 1, 3)
    fine = fft_noise(n, 1.2, seed + 2, 40, 200)
    scr = smooth(0.64, 0.72, fft_noise(n, 1.0, seed + 3, 2, 120, aniso=(0.05, 1.0)))
    h = np.clip(0.2 + 0.22 * bowl + 0.38 * low + 0.02 * fine, 0, 1)
    h = norm01(blur(h, 0.6))
    cav = norm01(blur(h, 3.0) - h, -0.1, 0.1)
    tarn = smooth(0.50, 0.74, big) * (0.55 + 0.45 * cav)
    polish = smooth(0.58, 0.8, fft_noise(n, 2.8, seed + 7, 1, 5))
    base = hexcol(0xA8713A) * 0.86
    alb = base[None, None] * (0.80 + 0.30 * big[..., None]) * (0.92 + 0.12 * low[..., None])
    alb = mix(alb, hexcol(0x3E2412), tarn * 0.8)
    alb = mix(alb, hexcol(0xCFA06A), polish * 0.35)
    alb = mix(alb, hexcol(0x2F6254), smooth(0.6, 0.9, cav) * smooth(0.5, 0.8, big) * 0.2)
    alb = alb * (0.86 + 0.18 * h[..., None]) + 0.03 * scr[..., None]
    rough = np.clip(0.28 + 0.32 * tarn - 0.10 * polish + 0.10 * cav + 0.05 * fine + 0.12 * scr, 0.14, 0.9)
    metal = np.clip(1.0 - 0.5 * tarn, 0, 1)
    ao = np.clip(0.78 + 0.22 * h, 0, 1)
    return _ts("EH_Bronze", albedo=alb, rough=rough, metal=metal, ao=ao, height=h, normal_strength=1.0, tile=0.30,
               wear=1.0, wear_boost=1.0, grime=(0.20, 0.12, 0.06), baked_tone=0.86)


def gen_steel(n, seed):
    streak = fft_noise(n, 1.4, seed, 3, 160, aniso=(0.06, 1.0))
    streak2 = fft_noise(n, 1.8, seed + 1, 2, 60, aniso=(0.1, 1.0))
    low = fft_noise(n, 2.6, seed + 2, 1, 6)
    v = voronoi(n, 22, seed + 3)
    dimple = (1 - np.clip(v["f1"] / 0.9, 0, 1) ** 2) * (v["rng"].random(v["n_sites"])[v["id"]] * 0.5 + 0.5)
    h = norm01(0.45 * streak + 0.3 * streak2 + 0.28 * dimple + 0.1 * low)
    rust_m = smooth(0.62, 0.8, fft_noise(n, 2.2, seed + 4, 2, 12)) * smooth(0.5, 0.7, fft_noise(n, 1.0, seed + 5, 20, 120))
    base = hexcol(0x3B3A38)
    alb = base[None, None] * (0.8 + 0.5 * streak[..., None] * 0.9) * (0.9 + 0.2 * low[..., None])
    alb = mix(alb, hexcol(0x59301A), rust_m * 0.75)
    rough = np.clip(0.40 + 0.3 * (streak - 0.5) + 0.35 * rust_m + 0.05 * low, 0.18, 0.9)
    metal = np.clip(0.95 - 0.5 * rust_m, 0, 1)
    ao = np.clip(0.8 + 0.2 * h, 0, 1)
    return _ts("EH_Steel", albedo=alb, rough=rough, metal=metal, ao=ao, height=h, normal_strength=4.0, tile=0.30,
               wear=1.0, wear_boost=1.0, grime=(0.08, 0.07, 0.06), baked_tone=0.88)


def gen_leather(n, seed):
    v = voronoi(n, 70, seed, jitter=1.0)
    pebble = smooth(0.0, 0.32, v["f2"] - v["f1"])
    wr = fft_noise(n, 2.2, seed + 1, 2, 18)
    wr = 1 - np.abs(wr - 0.5) * 2
    wr = smooth(0.7, 1.0, wr)
    fine = fft_noise(n, 1.0, seed + 2, 30, 200)
    h = norm01(0.55 * pebble + 0.28 * wr + 0.1 * fine)
    low = fft_noise(n, 2.4, seed + 3, 1, 6)
    base = hexcol(0x50321C)
    alb = base[None, None] * (0.7 + 0.5 * low[..., None]) * (0.7 + 0.4 * pebble[..., None])
    worn = smooth(0.6, 0.8, fft_noise(n, 2.0, seed + 4, 1, 8)) * (1 - pebble * 0.5)
    alb = mix(alb, hexcol(0x7A5434), worn * 0.22)
    rough = np.clip(0.66 + 0.12 * (1 - pebble) - 0.18 * worn + 0.05 * fine, 0.3, 0.95)
    ao = np.clip(0.6 + 0.4 * pebble, 0, 1)
    return _ts("EH_Leather", albedo=alb, rough=rough, metal=np.zeros((n, n)), ao=ao, height=h, normal_strength=3.2,
               tile=0.2, wear=0.35, grime=(0.08, 0.05, 0.03), baked_tone=0.9, ao_strength=0.9)


def gen_fur(n, seed):
    strand = fft_noise(n, 0.8, seed, 70, 240, aniso=(1.0, 9.0))
    strand2 = fft_noise(n, 1.2, seed + 1, 25, 110, aniso=(1.0, 6.0))
    clump = fft_noise(n, 2.2, seed + 2, 3, 20, aniso=(1.0, 4.0))
    grey = smooth(0.7, 0.9, fft_noise(n, 1.0, seed + 3, 50, 200, aniso=(1.0, 12.0)))
    h = norm01(0.5 * strand + 0.3 * strand2 + 0.3 * clump)
    dark, mid, tip = hexcol(0x2A1B10), hexcol(0x70502F), hexcol(0xA27A4A)
    t = np.clip(0.2 + 0.9 * (strand - 0.25) + 0.5 * (clump - 0.5), 0, 1)
    t3 = t[..., None]
    lo_c = dark[None, None] * (1 - 2 * t3) + mid[None, None] * (2 * t3)
    hi_c = mid[None, None] * (2 - 2 * t3) + tip[None, None] * (2 * t3 - 1)
    alb = np.where(t3 < 0.5, lo_c, hi_c)
    alb = mix(alb, hexcol(0xC9BBA3), grey * 0.10)
    rough = np.clip(0.8 + 0.12 * strand, 0.5, 1.0)
    ao = np.clip(0.35 + 0.75 * (0.35 * strand + 0.65 * clump), 0.3, 1)
    return _ts("EH_Fur", albedo=alb, rough=rough, metal=np.zeros((n, n)), ao=ao, height=h, normal_strength=7.0, tile=0.12,
               wear=0.0, ao_strength=1.0, grime=(0.07, 0.05, 0.035), baked_tone=1.0, double_sided=False)


def gen_cloth(n, seed):
    N = 64
    x = (np.arange(n) + 0.5) / n
    X, Y = np.meshgrid(x, x)
    a = 0.5 + 0.5 * np.sin(2 * math.pi * N * X)
    b = 0.5 + 0.5 * np.sin(2 * math.pi * N * Y)
    parity = (np.floor(X * N) + np.floor(Y * N)) % 2
    thread = np.where(parity > 0.5, a, b)
    slub = fft_noise(n, 1.0, seed, 20, 150, aniso=(1.0, 0.1))
    slub2 = fft_noise(n, 1.0, seed + 1, 20, 150, aniso=(0.1, 1.0))
    h = norm01(0.7 * thread + 0.15 * slub + 0.15 * slub2)
    low = fft_noise(n, 2.4, seed + 2, 1, 6)
    dirt = smooth(0.55, 0.8, fft_noise(n, 2.4, seed + 3, 1, 10))
    base = hexcol(0x6A2420)
    alb = base[None, None] * (0.74 + 0.38 * h[..., None]) * (0.85 + 0.25 * low[..., None])
    alb = mix(alb, hexcol(0x2A1A14), dirt * 0.4)
    rough = np.clip(0.88 + 0.08 * (1 - h), 0.5, 1)
    ao = np.clip(0.55 + 0.45 * h, 0, 1)
    return _ts("EH_Cloth", albedo=alb, rough=rough, metal=np.zeros((n, n)), ao=ao, height=h, normal_strength=7.0, tile=0.2,
               wear=0.0, grime=(0.08, 0.025, 0.02), baked_tone=1.0, ao_strength=1.0, double_sided=True)


def _crack_mask(n, seed, cells=7, width=0.05, warp=0.05):
    w1 = fft_noise(n, 2.6, seed + 11, 1, 24)
    w2 = fft_noise(n, 2.6, seed + 12, 1, 24)
    v = voronoi(n, cells, seed, warp=(w1, w2), warp_amt=warp)
    edge = v["f2"] - v["f1"]
    fine = fft_noise(n, 1.5, seed + 13, 10, 80)
    crack = 1 - smooth(0.0, width, edge + (fine - 0.5) * 0.04)
    return crack, edge, v


def gen_stone(n, seed):
    crack, edge, v = _crack_mask(n, seed, 4, 0.045)
    grain = fft_noise(n, 2.0, seed + 1, 2, 60)
    fine = fft_noise(n, 0.8, seed + 2, 40, 220)
    low = fft_noise(n, 2.6, seed + 3, 1, 5)
    pits = voronoi(n, 40, seed + 4)
    pit = (1 - np.clip(pits["f1"] / 0.6, 0, 1)) * (pits["rng"].random(pits["n_sites"])[pits["id"]] > 0.55)
    slab = voronoi(n, 5, seed + 5, jitter=0.7)  # large chipped blocks
    block_tone = slab["rng"].random(slab["n_sites"])[slab["id"]]
    h = norm01(0.55 * grain + 0.25 * fine + 0.3 * low - 0.35 * pit - 0.5 * crack + 0.12 * block_tone)
    patchy = smooth(0.60, 0.72, fft_noise(n, 2.4, seed + 6, 1, 6))
    glow = crack * patchy
    glow = blur(glow, 0.8)
    base = hexcol(0x3A322B)
    alb = base[None, None] * (0.7 + 0.5 * grain[..., None]) * (0.85 + 0.25 * low[..., None]) * (0.9 + 0.2 * block_tone[..., None])
    alb = mix(alb, hexcol(0x8C7B68), smooth(0.7, 0.9, fine) * 0.35)
    alb = mix(alb, hexcol(0x120D0A), np.clip(blur(crack, 3.0) * 2.2, 0, 1) * 0.85)
    hot = np.clip(glow * (0.5 + 0.9 * fft_noise(n, 2.0, seed + 7, 2, 14)), 0, 1)
    emi = np.stack([hot, hot ** 1.6 * 0.42, hot ** 3.0 * 0.09], -1)
    emi = np.clip(emi + glow[..., None] * np.array([0.5, 0.1, 0.0]), 0, 1)
    rough = np.clip(0.78 + 0.15 * (1 - grain) - 0.1 * crack, 0.4, 1)
    ao = np.clip(0.55 + 0.45 * norm01(h), 0, 1)
    return _ts("EH_Stone", albedo=alb, rough=rough, metal=np.zeros((n, n)), ao=ao, height=h, normal_strength=7.0, tile=0.4,
               emissive=None, wear=0.8, grime=(0.05, 0.04, 0.035), baked_tone=0.82, ao_strength=1.0)


def _molten(n, seed):
    v1 = fft_noise(n, 2.2, seed, 2, 14)
    ridge = 1 - np.abs(v1 - 0.5) * 2
    ridge = smooth(0.55, 0.98, ridge) ** 1.5
    pool = smooth(0.45, 0.75, fft_noise(n, 2.4, seed + 1, 1, 8))
    heat = np.clip(0.25 + 0.6 * pool + 0.7 * ridge, 0, 1)
    return heat, ridge


def _fire_ramp(t):
    t = np.clip(t, 0, 1)[..., None]
    c0, c1, c2, c3 = np.array([0.18, 0.02, 0.0]), np.array([0.85, 0.16, 0.02]), np.array([1.0, 0.5, 0.08]), np.array([1.0, 0.88, 0.45])
    return np.where(t < 0.4, c0 + (c1 - c0) * (t / 0.4), np.where(t < 0.75, c1 + (c2 - c1) * ((t - 0.4) / 0.35), c2 + (c3 - c2) * ((t - 0.75) / 0.25)))


def gen_ember(n, seed):
    heat, ridge = _molten(n, seed)
    h = norm01(blur(heat, 1.0))
    emi = _fire_ramp(heat)
    alb = np.stack([0.12 + 0.2 * heat, 0.03 + 0.05 * heat, 0.01 + 0.0 * heat], -1)
    return _ts("EH_Ember", albedo=alb, rough=np.full((n, n), 0.55), metal=np.zeros((n, n)), ao=np.ones((n, n)), height=h,
               normal_strength=3.0, tile=0.2, emissive=emi, emissive_strength=6.0, ao_strength=0.0, wear=0.0)


def gen_ember_vein(n, seed):
    ts = gen_ember(n, seed)
    ts.name = "EH_EmberVein"
    ts.emissive = ts.emissive * np.array([0.95, 0.5, 0.18])
    ts.emissive_strength = 1.8
    return ts


def gen_eh_interior(n, seed):
    crack, edge, v = _crack_mask(n, seed + 20, 9, 0.12, 0.06)
    heat, ridge = _molten(n, seed + 21)
    core = np.clip(0.35 + 0.55 * heat + 0.6 * crack, 0, 1)
    emi = _fire_ramp(core * 0.95)
    grain = fft_noise(n, 2.0, seed + 22, 2, 80)
    h = norm01(grain - 0.4 * crack)
    alb = np.stack([0.16 + 0.25 * core, 0.06 + 0.08 * core, np.full_like(core, 0.03)], -1)
    return _ts("EH_Interior", albedo=alb, rough=np.full((n, n), 0.6), metal=np.zeros((n, n)), ao=np.ones((n, n)), height=h,
               normal_strength=5.0, tile=0.25, emissive=emi, emissive_strength=3.2, ao_strength=0.0, wear=0.0, double_sided=True)


def gen_skin(n, seed):
    pores = voronoi(n, 90, seed, jitter=1.0)
    pit = (1 - np.clip(pores["f1"] / 0.5, 0, 1)) * (pores["rng"].random(pores["n_sites"])[pores["id"]] > 0.6)
    low = fft_noise(n, 2.4, seed + 1, 1, 6)
    fine = fft_noise(n, 1.2, seed + 2, 30, 200)
    h = norm01(0.3 * low + 0.2 * fine - 0.5 * pit)
    flush = smooth(0.5, 0.75, fft_noise(n, 2.4, seed + 3, 1, 5))
    alb = mix(hexcol(0xB98765)[None, None] * np.ones((n, n, 1)), hexcol(0xC9795A), flush * 0.4) * (0.88 + 0.2 * low[..., None])
    return _ts("EH_Skin", albedo=alb, rough=np.clip(0.58 + 0.15 * fine, 0.3, 0.9), metal=np.zeros((n, n)), ao=np.clip(0.8 + 0.2 * h, 0, 1),
               height=h, normal_strength=3.0, tile=0.2, wear=0.0, grime=(0.25, 0.12, 0.08), baked_tone=1.0, ao_strength=0.9)


# ---------------------------------------------------------------- Rime Host
def gen_obsidian(n, seed):
    v = voronoi(n, 7, seed, jitter=1.0)
    rng = v["rng"]
    sl = (rng.random((v["n_sites"], 2)) - 0.5) * 0.9
    fac = sl[v["id"], 0] * v["dx"] + sl[v["id"], 1] * v["dy"]
    ripple = np.sin(v["f1"] * 2 * math.pi * 3.2 + rng.random(v["n_sites"])[v["id"]] * 6) * np.exp(-v["f1"] * 0.6)
    fine = fft_noise(n, 1.4, seed + 1, 20, 160)
    scr = smooth(0.66, 0.74, fft_noise(n, 1.0, seed + 2, 2, 140, aniso=(0.04, 1.0)))
    h = norm01(0.55 * fac + 0.25 * ripple + 0.08 * fine)
    low = fft_noise(n, 2.4, seed + 3, 1, 6)
    alb = hexcol(0x1C2430)[None, None] * (0.55 + 0.9 * low[..., None]) * (0.8 + 0.4 * h[..., None])
    alb = mix(alb, hexcol(0x4C6078), scr * 0.5)
    rough = np.clip(0.10 + 0.1 * fine + 0.35 * scr, 0.05, 0.6)
    ao = np.clip(0.8 + 0.2 * h, 0, 1)
    return _ts("RH_Obsidian", albedo=alb, rough=rough, metal=np.full((n, n), 0.2), ao=ao, height=h, normal_strength=7.0,
               tile=0.35, wear=0.8, wear_boost=1.0, grime=(0.01, 0.015, 0.025), baked_tone=0.9, ao_strength=0.85)


def gen_ice(n, seed):
    crack, edge, v = _crack_mask(n, seed, 5, 0.04, 0.09)
    crack2, _, _ = _crack_mask(n, seed + 31, 9, 0.025, 0.12)
    facet = voronoi(n, 5, seed + 32, jitter=1.0)
    fac = ((facet["rng"].random((facet["n_sites"], 2)) - 0.5) * 0.5)
    h = norm01(fac[facet["id"], 0] * facet["dx"] + fac[facet["id"], 1] * facet["dy"] + 0.15 * fft_noise(n, 2.0, seed + 33, 2, 40))
    frost = smooth(0.58, 0.8, fft_noise(n, 2.2, seed + 34, 2, 20))
    alb = mix(hexcol(0xB8E6FA)[None, None] * np.ones((n, n, 1)), hexcol(0xE6F6FF), frost * 0.7 + crack * 0.4)
    emi = np.stack([0.18 * np.ones((n, n)), 0.85 * np.ones((n, n)), 1.0 * np.ones((n, n))], -1) * (np.clip(crack * 0.9 + crack2 * 0.35, 0, 1))[..., None] * 0.55
    rough = np.clip(0.07 + 0.5 * frost + 0.1 * crack, 0.03, 0.8)
    return _ts("RH_Ice", albedo=alb, rough=rough, metal=np.zeros((n, n)), ao=np.ones((n, n)), height=h, normal_strength=4.0, tile=0.4,
               emissive=emi, emissive_strength=1.5, transmission=0.9, ior=1.31, thickness=0.05, attenuation_color=(0.45, 0.8, 1.0),
               attenuation_distance=0.35, wear=0.0, ao_strength=0.4, grime=(0.3, 0.45, 0.55), baked_tone=1.0, double_sided=False)


def gen_frost(n, seed):
    cr = fft_noise(n, 1.0, seed, 8, 150)
    sparkle = smooth(0.74, 0.82, fft_noise(n, 0.6, seed + 1, 80, 250))
    low = fft_noise(n, 2.4, seed + 2, 1, 8)
    h = norm01(0.6 * cr + 0.4 * low)
    alb = hexcol(0xDCEFF7)[None, None] * (0.82 + 0.25 * low[..., None])
    alb = np.clip(alb + sparkle[..., None] * 0.15, 0, 1)
    rough = np.clip(0.88 - 0.4 * sparkle, 0.3, 1)
    return _ts("RH_Frost", albedo=alb, rough=rough, metal=np.zeros((n, n)), ao=np.clip(0.6 + 0.4 * h, 0, 1), height=h,
               normal_strength=6.0, tile=0.25, wear=0.0, ao_strength=0.7, grime=(0.45, 0.55, 0.62), baked_tone=1.0)


def gen_silver(n, seed):
    streak = fft_noise(n, 1.2, seed, 3, 180, aniso=(0.05, 1.0))
    scr = smooth(0.66, 0.74, fft_noise(n, 1.0, seed + 1, 2, 140, aniso=(1.0, 0.04)))
    low = fft_noise(n, 2.4, seed + 2, 1, 6)
    h = norm01(streak * 0.7 + 0.3 * low)
    alb = hexcol(0xB4C6D2)[None, None] * (0.78 + 0.35 * streak[..., None]) * (0.9 + 0.2 * low[..., None])
    rough = np.clip(0.28 + 0.2 * (streak - 0.5) + 0.2 * scr, 0.1, 0.8)
    return _ts("RH_Silver", albedo=alb, rough=rough, metal=np.full((n, n), 1.0), ao=np.clip(0.8 + 0.2 * h, 0, 1), height=h,
               normal_strength=3.0, tile=0.25, wear=0.6, grime=(0.12, 0.15, 0.18), baked_tone=0.9)


def gen_glow(n, seed):
    v1 = fft_noise(n, 2.2, seed, 2, 14)
    ridge = smooth(0.55, 0.98, 1 - np.abs(v1 - 0.5) * 2)
    heat = np.clip(0.4 + 0.7 * ridge, 0, 1)
    emi = np.stack([0.2 + 0.5 * heat, 0.75 + 0.25 * heat, np.ones_like(heat)], -1) * (0.55 + 0.45 * heat)[..., None]
    return _ts("RH_Glow", albedo=np.full((n, n, 3), 0.03), rough=np.full((n, n), 0.4), metal=np.zeros((n, n)), ao=np.ones((n, n)),
               height=norm01(heat), normal_strength=2.0, tile=0.2, emissive=emi, emissive_strength=4.0, ao_strength=0.0)


def gen_rh_interior(n, seed):
    crack, edge, v = _crack_mask(n, seed + 40, 8, 0.1, 0.07)
    low = fft_noise(n, 2.4, seed + 41, 1, 8)
    alb = mix(hexcol(0xA9D6EA)[None, None] * np.ones((n, n, 1)), hexcol(0xEAF8FF), low * 0.6)
    emi = np.stack([0.25 * np.ones((n, n)), 0.9 * np.ones((n, n)), np.ones((n, n))], -1) * (0.25 + 0.75 * crack)[..., None]
    return _ts("RH_Interior", albedo=alb, rough=np.clip(0.25 + 0.2 * low, 0, 1), metal=np.zeros((n, n)), ao=np.ones((n, n)),
               height=norm01(low - 0.5 * crack), normal_strength=5.0, tile=0.3, emissive=emi, emissive_strength=1.8, ao_strength=0.0,
               double_sided=True)


for _n, _f, _s in [("EH_Bronze", gen_bronze, 11), ("EH_Steel", gen_steel, 12), ("EH_Leather", gen_leather, 13),
                   ("EH_Fur", gen_fur, 14), ("EH_Cloth", gen_cloth, 15), ("EH_Stone", gen_stone, 16),
                   ("EH_Ember", gen_ember, 17), ("EH_EmberVein", gen_ember_vein, 27), ("EH_Skin", gen_skin, 19), ("EH_Interior", gen_eh_interior, 18),
                   ("RH_Obsidian", gen_obsidian, 21), ("RH_Ice", gen_ice, 22), ("RH_Frost", gen_frost, 23),
                   ("RH_Silver", gen_silver, 24), ("RH_Glow", gen_glow, 25), ("RH_Interior", gen_rh_interior, 26)]:
    register(MaterialDef(_n, _f, _s))


@lru_cache(maxsize=64)
def get_texture_set(name: str, res: int = DEFAULT_RES) -> TextureSet:
    d = REGISTRY[name]
    ts = d.gen(res, d.seed)
    ts.name = name
    return ts


# ------------------------------------------------------------------ vertex baking (AO + edge wear)
def _cos_hemisphere(k):
    i = np.arange(k) + 0.5
    phi = math.pi * (1 + 5 ** 0.5) * i
    cos_t = np.sqrt(1 - i / k)  # cosine-weighted
    sin_t = np.sqrt(1 - cos_t ** 2)
    return np.stack([sin_t * np.cos(phi), sin_t * np.sin(phi), cos_t], 1)


def _tangent_frames(N):
    a = np.where(np.abs(N[:, 1:2]) < 0.9, np.array([[0, 1.0, 0]]), np.array([[1.0, 0, 0]]))
    t = np.cross(a, N)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    b = np.cross(N, t)
    return t, b


def voxel_ao(meshes, normals_list, res=120, rays=36, max_dist_vox=14, seed=0, pad=0.06):
    """Ambient occlusion per vertex via ray marching through a voxelised copy of all meshes."""
    allP = np.concatenate([m.P for m in meshes])
    lo, hi = allP.min(0) - pad, allP.max(0) + pad
    vox = float((hi - lo).max() / res)
    dims = np.ceil((hi - lo) / vox).astype(int) + 1
    occ = np.zeros(dims, dtype=bool)
    rng = np.random.default_rng(seed)
    for m in meshes:
        F = m.F
        a, b, c = m.P[F[:, 0]], m.P[F[:, 1]], m.P[F[:, 2]]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        cnt = np.maximum(1, np.ceil(area / (0.4 * vox) ** 2).astype(int))
        cnt = np.minimum(cnt, 4000)
        tri = np.repeat(np.arange(len(F)), cnt)
        r1, r2 = rng.random(len(tri)), rng.random(len(tri))
        s = np.sqrt(r1)
        pts = a[tri] * (1 - s)[:, None] + b[tri] * (s * (1 - r2))[:, None] + c[tri] * (s * r2)[:, None]
        idx = np.clip(((pts - lo) / vox).astype(int), 0, dims - 1)
        occ[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    dirs_local = _cos_hemisphere(rays)
    steps = vox * np.array([2.0, 3.0, 4.2, 5.8, 7.8, 10.5, 14.0])[:max_dist_vox // 2]
    dmax = steps[-1]
    out = []
    for m, N in zip(meshes, normals_list):
        P = m.P
        ao = np.ones(len(P))
        for s0 in range(0, len(P), 3000):
            sl = slice(s0, s0 + 3000)
            Pn, Nn = P[sl], N[sl]
            t, b = _tangent_frames(Nn)
            dirs = (dirs_local[None, :, 0:1] * t[:, None, :] + dirs_local[None, :, 1:2] * b[:, None, :] +
                    dirs_local[None, :, 2:3] * Nn[:, None, :])                                   # (v,k,3)
            first = np.full((len(Pn), rays), np.inf)
            for d in steps:
                q = Pn[:, None, :] + dirs * d
                idx = np.clip(((q - lo) / vox).astype(int), 0, dims - 1)
                hit = occ[idx[..., 0], idx[..., 1], idx[..., 2]]
                first = np.where(hit & (first == np.inf), d, first)
            w = np.where(np.isinf(first), 0.0, 1.0 - 0.55 * first / dmax)
            ao[sl] = 1.0 - w.mean(1)
        out.append(np.clip(ao, 0, 1))
    return out


def convexity(mesh: Mesh, blur_iters=2):
    """Per-vertex convex edge curvature (1/metres-ish; 0 on flats and concave areas), and concavity."""
    P, F = mesh.P, mesh.F
    gid = mesh.weld_ids()
    fn = mesh.face_normals()
    m = len(F)
    e = np.stack([np.stack([gid[F[:, 0]], gid[F[:, 1]]], 1), np.stack([gid[F[:, 1]], gid[F[:, 2]]], 1),
                  np.stack([gid[F[:, 2]], gid[F[:, 0]]], 1)], 1).reshape(-1, 2)   # (3m,2)
    third = np.stack([F[:, 2], F[:, 0], F[:, 1]], 1).reshape(-1)
    face = np.repeat(np.arange(m), 3)
    key = np.sort(e, 1)
    k = key[:, 0].astype(np.int64) * (gid.max() + 1) + key[:, 1]
    order = np.argsort(k, kind="stable")
    ks = k[order]
    same = ks[1:] == ks[:-1]
    # edges with exactly two incident faces
    cnt = np.diff(np.concatenate([[0], np.flatnonzero(np.diff(ks)) + 1, [len(ks)]]))
    starts = np.concatenate([[0], np.flatnonzero(np.diff(ks)) + 1])
    two = starts[cnt == 2]
    i1, i2 = order[two], order[two + 1]
    f1, f2 = face[i1], face[i2]
    ang = np.arccos(np.clip(np.einsum('ij,ij->i', fn[f1], fn[f2]), -1, 1))
    gpos = np.zeros((gid.max() + 1, 3))
    gpos[gid] = P
    ea, eb = e[i1, 0], e[i1, 1]
    L = np.linalg.norm(gpos[ea] - gpos[eb], axis=1)
    side = np.einsum('ij,ij->i', P[third[i2]] - gpos[ea], fn[f1])
    sign = np.where(side < -1e-9, 1.0, np.where(side > 1e-9, -1.0, 0.0))
    curv = sign * ang / np.maximum(L, 1e-6)
    ng = gid.max() + 1
    cx = np.zeros(ng)
    cv = np.zeros(ng)
    np.maximum.at(cx, ea, np.maximum(curv, 0))
    np.maximum.at(cx, eb, np.maximum(curv, 0))
    np.maximum.at(cv, ea, np.maximum(-curv, 0))
    np.maximum.at(cv, eb, np.maximum(-curv, 0))
    # neighbour blur on the welded graph
    ea_all, eb_all = e[:, 0], e[:, 1]
    A = sparse.coo_matrix((np.ones(len(ea_all)), (ea_all, eb_all)), shape=(ng, ng))
    A = ((A + A.T) > 0).astype(np.float64).tocsr()
    deg = np.maximum(np.asarray(A.sum(1)).reshape(-1), 1)
    for _ in range(blur_iters):
        cx = 0.5 * cx + 0.5 * (A @ cx) / deg
        cv = 0.5 * cv + 0.5 * (A @ cv) / deg
    return cx[gid], cv[gid]


def bake_vertex_colors(meshes, material_names, res=120, rays=36, seed=1, tex_res=DEFAULT_RES):
    """Return per-mesh (n,4) COLOR_0 arrays (RGB = tinted AO * wear, A = 1)."""
    normals = [m.smooth_normals() for m in meshes]
    ao_all = voxel_ao(meshes, normals, res=res, rays=rays, seed=seed)
    out = []
    for m, N, ao, mat in zip(meshes, normals, ao_all, material_names):
        ts = get_texture_set(mat, tex_res)
        cx, cv = convexity(m)
        # grime: concavity darkens too
        occl = np.clip(ao - 0.35 * smoothstep(20, 90, cv), 0, 1)
        occl = 1 - (1 - occl) * ts.ao_strength
        occl = occl ** 1.15
        # AO-proportional tint toward grime colour
        g = np.asarray(ts.grime)
        col = g[None, :] + (1 - g[None, :]) * occl[:, None]
        tone = np.clip(ts.baked_tone + (1 - ts.baked_tone) * 0.0, 0, 1)
        wear = smoothstep(28.0, 140.0, cx) * ts.wear
        nz = 0.5 + 0.6 * fbm3(m.P * 38.0, 1.0, 3, seed=seed + 5)
        wear = np.clip(wear * np.clip(nz, 0.15, 1.2), 0, 1)
        col = col * (tone + (1.0 - tone) * wear[:, None] * ts.wear_boost)
        # wear also lifts toward a clean metal tone: bring edges slightly above the tone floor
        col = np.clip(col, 0, 1)
        out.append(np.concatenate([col, np.ones((len(col), 1))], 1))
    return out
