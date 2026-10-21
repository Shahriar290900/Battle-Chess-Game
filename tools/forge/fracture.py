"""fracture.py - pre-fractured fragment sets from the LOD1 geometry.

Pipeline: decimate LOD1 parts to a source mesh -> Voronoi-cluster its triangles (k-means on triangle
centroids, label smoothing, island repair) -> every cluster becomes a closed shell: the outer skin keeps its
material, an inward-offset copy plus boundary walls use `{FACTION}_Interior`.  Fragment origins sit at the
(approximate) centre of mass and the nodes are placed so the set is assembled in rest pose.

    frags = build_fragments(parts_lod1, count=20, interior_material="EH_Interior")
    # frags: list of Fragment(centroid, prims=[(Mesh, material_name), ...])
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from geom import Mesh, decimate, merge, normalize


@dataclass
class Fragment:
    centroid: np.ndarray
    prims: list   # [(Mesh, material_name)] meshes are centred on `centroid`

    @property
    def tris(self):
        return sum(m.tri_count for m, _ in self.prims)


def _kmeans_faces(cent, area, k, seed, iters=14, aniso=(1.0, 1.25, 1.0)):
    rng = np.random.default_rng(seed)
    X = cent * np.asarray(aniso)
    n = len(X)
    # area-weighted farthest-point init (with a little randomness)
    first = rng.choice(n, p=area / area.sum())
    centers = [X[first]]
    d = np.linalg.norm(X - centers[0], axis=1)
    for _ in range(1, k):
        p = (d ** 2) * area
        p = p / p.sum()
        nxt = rng.choice(n, p=p)
        centers.append(X[nxt])
        d = np.minimum(d, np.linalg.norm(X - X[nxt], axis=1))
    C = np.array(centers)
    lab = np.zeros(n, dtype=np.int64)
    for _ in range(iters):
        dist = np.linalg.norm(X[:, None, :] - C[None], axis=2)
        lab = dist.argmin(1)
        for j in range(k):
            sel = lab == j
            if sel.any():
                C[j] = (X[sel] * area[sel, None]).sum(0) / area[sel].sum()
    return lab


def _face_neighbors(F, gid):
    m = len(F)
    e = np.stack([np.stack([gid[F[:, 0]], gid[F[:, 1]]], 1), np.stack([gid[F[:, 1]], gid[F[:, 2]]], 1),
                  np.stack([gid[F[:, 2]], gid[F[:, 0]]], 1)], 1).reshape(-1, 2)
    key = np.sort(e, 1)
    k = key[:, 0].astype(np.int64) * (gid.max() + 1) + key[:, 1]
    order = np.argsort(k, kind="stable")
    ks = k[order]
    face = np.repeat(np.arange(m), 3)[order]
    pairs = []
    i = 0
    n = len(ks)
    while i < n:
        j = i + 1
        while j < n and ks[j] == ks[i]:
            j += 1
        if j - i == 2:
            pairs.append((face[i], face[i + 1]))
        i = j
    nb = [[] for _ in range(m)]
    for a, b in pairs:
        nb[a].append(b)
        nb[b].append(a)
    return nb


def _repair_labels(lab, nb, k, passes=2):
    lab = lab.copy()
    for _ in range(passes):  # majority smoothing
        new = lab.copy()
        for f, ns in enumerate(nb):
            if len(ns) < 2:
                continue
            votes = np.bincount(lab[ns], minlength=k)
            top = votes.argmax()
            if votes[top] >= 2 and votes[top] > votes[lab[f]]:
                new[f] = top
        lab = new
    # keep only the largest connected component of every label; give islands to the neighbouring label
    for c in range(k):
        faces = np.flatnonzero(lab == c)
        if len(faces) == 0:
            continue
        seen = set()
        comps = []
        for f in faces:
            if f in seen:
                continue
            stack, comp = [f], []
            seen.add(f)
            while stack:
                x = stack.pop()
                comp.append(x)
                for y in nb[x]:
                    if lab[y] == c and y not in seen:
                        seen.add(y)
                        stack.append(y)
            comps.append(comp)
        comps.sort(key=len, reverse=True)
        for comp in comps[1:]:
            votes = np.zeros(k, dtype=int)
            for x in comp:
                for y in nb[x]:
                    if lab[y] != c:
                        votes[lab[y]] += 1
            if votes.max() > 0:
                lab[comp] = votes.argmax()
    return lab


def _inward_thickness(P, F, vn, thick, max_frac=0.45):
    """Cast each vertex inward; thickness = min(thick, max_frac * distance to the opposite surface)."""
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    e1, e2 = b - a, c - a
    out = np.full(len(P), thick)
    for s in range(0, len(P), 128):
        o = P[s:s + 128]
        d = -vn[s:s + 128]
        pvec = np.cross(d[:, None, :], e2[None])                    # (v,t,3)
        det = np.einsum('tj,vtj->vt', e1, pvec)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tvec = o[:, None, :] - a[None]
        u = np.einsum('vtj,vtj->vt', tvec, pvec) * inv
        qvec = np.cross(tvec, e1[None])
        v = np.einsum('vj,vtj->vt', d, qvec) * inv
        t = np.einsum('tj,vtj->vt', e2, qvec) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0.004)
        tt = np.where(hit, t, np.inf).min(1)
        out[s:s + 128] = np.minimum(thick, np.where(np.isinf(tt), thick, max_frac * tt))
    return np.maximum(out, 0.004)


def build_fragments(parts, count, interior_material, budget=5800, thickness=0.03, seed=0, source_share=0.4):
    """parts: [(Mesh, material_name)] (LOD1 geometry, shaded, with UV/colours).  Returns list[Fragment]."""
    total = sum(m.tri_count for m, _ in parts)
    share = source_share
    for attempt in range(6):
        target = int(budget * share)
        scale = min(1.0, target / max(total, 1))
        src = []
        for m, mat in parts:
            if m.tri_count > 14:
                m = decimate(m, max(10, int(m.tri_count * scale)))
            src.append((m, mat))
        frags = _fracture(src, count, interior_material, thickness, seed)
        tris = sum(f.tris for f in frags)
        if tris <= budget:
            return frags
        share *= 0.82
    return frags


def _fracture(src, count, interior_material, thickness, seed):
    mats = sorted({mat for _, mat in src})
    mesh = merge([m for m, _ in src])
    fmat = np.concatenate([[mats.index(mat)] * m.tri_count for m, mat in src])
    P, F = mesh.P, mesh.F
    gid = mesh.weld_ids()
    sn = mesh.smooth_normals()
    area = mesh.face_areas() + 1e-9
    cent = P[F].mean(1)
    nb = _face_neighbors(F, gid)
    lab = _kmeans_faces(cent, area, count, seed)
    lab = _repair_labels(lab, nb, count)
    thick_v = _inward_thickness(P, F, sn, thickness)
    frags = []
    used = sorted(set(lab.tolist()))
    for c in used:
        fc = np.flatnonzero(lab == c)
        if len(fc) < 2:
            continue
        # centre of mass: area-weighted centroid shifted half a thickness inward
        fnorm = mesh.face_normals()[fc]
        w = area[fc]
        centroid = (cent[fc] * w[:, None]).sum(0) / w.sum() - (fnorm * w[:, None]).sum(0) / w.sum() * thickness * 0.5
        prims = []
        # outer skin per material
        for mi, mat in enumerate(mats):
            sel = fc[fmat[fc] == mi]
            if len(sel) == 0:
                continue
            Fm = F[sel]
            vs, inv = np.unique(Fm.reshape(-1), return_inverse=True)
            m = Mesh(P[vs] - centroid, inv.reshape(-1, 3), mesh.UV[vs], None if mesh.N is None else mesh.N[vs],
                     None if mesh.C is None else mesh.C[vs], {k: v[vs] for k, v in mesh.A.items()}, mesh.crease)
            prims.append((m, mat))
        # interior: inward shell (flipped) + boundary walls
        Fc = F[fc]
        vs, inv = np.unique(Fc.reshape(-1), return_inverse=True)
        Pin = P[vs] - sn[vs] * thick_v[vs][:, None] - centroid
        inner = Mesh(Pin, inv.reshape(-1, 3)[:, ::-1], mesh.UV[vs], -sn[vs], None, {}, 60)
        # boundary edges (welded ids) with the face's own winding a->b
        ed = np.concatenate([Fc[:, [0, 1]], Fc[:, [1, 2]], Fc[:, [2, 0]]])
        ge = np.sort(gid[ed], 1)
        key = ge[:, 0].astype(np.int64) * (gid.max() + 1) + ge[:, 1]
        uq, idx, cnt = np.unique(key, return_index=True, return_counts=True)
        bidx = idx[cnt == 1]
        walls_P, walls_F = [], []
        for e in bidx:
            a, b = ed[e]
            pa, pb = P[a] - centroid, P[b] - centroid
            pa2 = pa - sn[a] * thick_v[a]
            pb2 = pb - sn[b] * thick_v[b]
            base = len(walls_P)
            walls_P += [pa, pa2, pb2, pb]
            walls_F += [(base, base + 1, base + 2), (base, base + 2, base + 3)]
        parts_in = [inner]
        if walls_P:
            wm = Mesh(np.array(walls_P), np.array(walls_F), crease=1.0).shade(1.0)
            parts_in.append(wm)
        interior = merge([p if p.N is not None else p.shade(60) for p in parts_in])
        interior = interior.uv_box(0.25)
        interior.C = np.ones((len(interior.P), 4))
        prims.append((interior, interior_material))
        frags.append(Fragment(centroid, prims))
    return frags
