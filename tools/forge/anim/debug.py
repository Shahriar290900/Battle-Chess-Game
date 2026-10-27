"""debug.py - stick-figure strips for fast animation iteration (no mesh build, no browser).

    from anim.debug import stick_strip
    stick_strip(animator, sampled, [0, 0.2, 0.4], "/tmp/x.png", extra=lambda S, f: [((p0), (p1), colour), ...])

Each cell: front view (top) and side view (bottom, +Z to the right).  Left-side bones red, right blue, spine/head grey,
foot/hand end bones as dots, the plinth top as a line.  Footprints that are in contact are drawn green.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw


def stick_strip(anim, S, times, path, cell=300, extra=None, y_range=(0.0, 1.2), ground=0.22, contacts=True):
    sk = anim.sk
    times = list(times)
    W = cell * len(times)
    img = Image.new("RGB", (W, cell * 2), (24, 24, 30))
    d = ImageDraw.Draw(img)
    scale = cell / (y_range[1] - y_range[0]) * 0.92
    for ci, t in enumerate(times):
        f = int(np.argmin(np.abs(S.times - t)))
        P = S.Pw[f]
        for row, (ax, flip) in enumerate(((0, 1), (2, 1))):
            ox = ci * cell + cell / 2
            oy = row * cell + cell * 0.96

            def pt(p, ax=ax, ox=ox, oy=oy):
                return (ox + p[ax] * scale * flip, oy - (p[1] - y_range[0]) * scale)

            # plinth
            d.line([pt((-0.4, ground, -0.4)), pt((0.4, ground, 0.4))] if False else [(ox - 0.4 * scale, oy - (ground - y_range[0]) * scale), (ox + 0.4 * scale, oy - (ground - y_range[0]) * scale)], fill=(110, 90, 60), width=2)
            for i, name in enumerate(sk.names):
                p = sk.parent[i]
                if p < 0:
                    continue
                col = (200, 70, 70) if name.endswith("_L") else (70, 120, 220) if name.endswith("_R") else (180, 180, 190)
                if name in ("weapon",):
                    col = (240, 200, 60)
                d.line([pt(P[p]), pt(P[i])], fill=col, width=3)
                x, y = pt(P[i])
                d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=col)
            if extra:
                for a, b, col in extra(S, f):
                    d.line([pt(a), pt(b)], fill=col, width=2)
        d.text((ci * cell + 6, 4), f"t={S.times[f]:.2f}", fill=(255, 255, 255))
    img.save(path)
    return path
