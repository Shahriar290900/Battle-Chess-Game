"""Build the Emberhold Shieldbearer blockout (contract v1).

    blender -b --factory-startup -P blender/build/emberhold_pawn.py -- --out assets/models [--turntable]

Copy this file per asset id and change: ASSET_ID, EXTRAS, BONES, parts(), sockets, clips.
Front faces -Y in Blender (becomes +Z in glTF). Heights from art-bible §2.
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import piece_kit as K  # noqa: E402

ASSET_ID = "emberhold_pawn"
FACTION, ROLE = "emberhold", "pawn"
EXTRAS = {
    "faction": FACTION, "role": ROLE, "displayName": "Emberhold Shieldbearer",
    "impactTime": 0.95, "strikeRange": 0.55, "attackStyle": "melee", "contractVersion": 1,
}
ATTACK_LEN = 1.6

# name, parent, head, tail   (figure from pedestal top z=0.22 to head top z≈1.05)
BONES = [
    ("root", None, (0, 0, 0), (0, 0, 0.10)),
    ("body", "root", (0, 0, 0.57), (0, 0, 0.72)),
    ("spine", "body", (0, 0, 0.72), (0, 0, 0.93)),
    ("head", "spine", (0, 0, 0.93), (0, 0, 1.00)),
    ("top", "head", (0, 0, 1.00), (0, 0, 1.05)),
    ("arm_L", "spine", (-0.14, 0, 0.88), (-0.16, -0.03, 0.64)),
    ("hand_L", "arm_L", (-0.16, -0.03, 0.64), (-0.16, -0.05, 0.58)),
    ("arm_R", "spine", (0.14, 0, 0.88), (0.16, -0.03, 0.64)),
    ("hand_R", "arm_R", (0.16, -0.03, 0.64), (0.16, -0.05, 0.58)),
]


def parts(m):
    P = []
    P += K.pedestal(FACTION, m)
    # legs + boots
    for s in (-1, 1):
        P.append(K.bind(K.detail(K.cone(f"leg_{s}", (0.055 * s, 0, 0.24), 0.045, 0.055, 0.34, m["cloth"], 16)), "body"))
        P.append(K.bind(K.detail(K.box(f"boot_{s}", (0.055 * s, -0.02, 0.25), (0.07, 0.11, 0.06), m["steel"])), "body"))
    # torso: quilted gambeson + bronze breastplate
    P.append(K.bind(K.detail(K.lathe("torso", [(0.56, 0.11), (0.62, 0.13), (0.72, 0.14), (0.82, 0.15),
                                               (0.89, 0.12), (0.92, 0.06)], m["cloth"], 32)), "spine"))
    P.append(K.bind(K.detail(K.sphere("breastplate", (0, -0.035, 0.78), 0.13, m["base"], scale=(1.0, 0.75, 1.05))), "spine"))
    for s in (-1, 1):
        P.append(K.bind(K.detail(K.sphere(f"pauldron_{s}", (0.14 * s, 0, 0.88), 0.06, m["base"], scale=(1.2, 1.0, 0.8))), "spine"))
    # head + helmet with nasal guard
    P.append(K.bind(K.detail(K.sphere("head", (0, 0, 0.97), 0.065, m["cloth"])), "head"))
    P.append(K.bind(K.detail(K.sphere("helm", (0, 0, 0.99), 0.072, m["base"], scale=(1, 1, 0.85))), "head"))
    P.append(K.bind(K.detail(K.box("nasal", (0, -0.07, 0.965), (0.012, 0.01, 0.06), m["steel"])), "head"))
    # arms + hands
    for side, s in (("L", -1), ("R", 1)):
        P.append(K.bind(K.detail(K.cone(f"arm_{side}", (0.14 * s, 0, 0.88), 0.035, 0.03, 0.25, m["cloth"], 12,
                                        direction=(0.02 * s, -0.03, -0.24))), f"arm_{side}"))
        P.append(K.bind(K.detail(K.sphere(f"hand_{side}", (0.16 * s, -0.03, 0.63), 0.028, m["steel"])), f"hand_{side}"))
    # sword (held low, blade up) and round shield facing front (-Y)
    P.append(K.bind(K.detail(K.box("blade", (0.16, -0.05, 0.80), (0.012, 0.03, 0.30), m["steel"])), "hand_R"))
    P.append(K.bind(K.detail(K.cone("tip", (0.16, -0.05, 0.95), 0.015, 0.0, 0.05, m["steel"], 4)), "hand_R"))
    P.append(K.bind(K.detail(K.box("guard", (0.16, -0.05, 0.65), (0.07, 0.02, 0.012), m["base"])), "hand_R"))
    P.append(K.bind(K.detail(K.cone("shield", (-0.17, -0.06, 0.66), 0.16, 0.16, 0.025, m["base"], 40,
                                    direction=(0, -1, 0))), "hand_L"))
    P.append(K.bind(K.detail(K.sphere("shield_boss", (-0.17, -0.09, 0.66), 0.035, m["glow"], scale=(1, 0.5, 1))), "hand_L"))
    return P


def clips(rig):
    t_hit = EXTRAS["impactTime"]
    # NOTE: arm swing axis depends on bone roll; if the chop swings backwards, flip the sign.
    K.clip(rig, "Idle", [(0, "spine", "rot", (0, 0, 0)), (1.5, "spine", "rot", (0, 0.03, 0)),
                         (3.0, "spine", "rot", (0, 0, 0))], 3.0)
    K.clip(rig, "Move", [(0, "body", "loc", (0, 0, 0)), (0.2, "body", "loc", (0, 0.04, 0)),
                         (0.4, "body", "loc", (0, 0, 0)), (0.6, "body", "loc", (0, 0.04, 0)),
                         (0.8, "body", "loc", (0, 0, 0))], 0.8)
    K.clip(rig, "Attack", [
        (0.0, "arm_R", "rot", (0, 0, 0)), (t_hit * 0.45, "arm_R", "rot", (2.6, 0, 0)),
        (t_hit * 0.85, "arm_R", "rot", (2.7, 0, 0)), (t_hit, "arm_R", "rot", (-1.3, 0, 0)),
        (t_hit + 0.25, "arm_R", "rot", (-1.1, 0, 0)), (ATTACK_LEN, "arm_R", "rot", (0, 0, 0)),
        (0.0, "arm_L", "rot", (0, 0, 0)), (t_hit * 0.4, "arm_L", "rot", (-0.9, 0, 0)),  # shield bash
        (t_hit * 0.6, "arm_L", "rot", (0, 0, 0)),
        (0.0, "body", "loc", (0, 0, 0)), (t_hit * 0.8, "body", "loc", (0, 0.05, 0)),
        (t_hit, "body", "loc", (0, -0.15, 0)), (ATTACK_LEN, "body", "loc", (0, 0, 0)),
    ], ATTACK_LEN)
    K.clip(rig, "HitReact", [(0, "body", "rot", (0, 0, 0)), (0.15, "body", "rot", (-0.35, 0, 0)),
                             (0.45, "body", "rot", (0, 0, 0))], 0.45)
    K.clip(rig, "Victory", [(0, "arm_R", "rot", (0, 0, 0)), (0.5, "arm_R", "rot", (2.9, 0, 0)),
                            (1.3, "arm_R", "rot", (2.9, 0, 0)), (1.6, "arm_R", "rot", (0, 0, 0))], 1.6)
    K.check_clips(rig)


def main():
    a = K.args()
    K.reset_scene()
    m = K.faction_materials(FACTION)
    rig = K.armature(BONES)
    lod0 = K.join_parts(f"{ASSET_ID}_LOD0", parts(m), rig)
    lod1 = K.make_lod1(lod0, f"{ASSET_ID}_LOD1")
    sockets = [
        K.socket("socket_weapon_R", rig, "hand_R", (0.16, -0.05, 1.00)),
        K.socket("socket_impact", rig, "root", (0, -0.45, 0.55)),
        K.socket("socket_head", rig, "head", (0, 0, 1.06)),
    ]
    clips(rig)
    root = K.asset_root(ASSET_ID, [rig, lod0, lod1], EXTRAS)
    K.export_glb(os.path.join(a["out"], f"{ASSET_ID}.glb"), root)

    frag_root, _ = K.fracture(lod1, ASSET_ID, m["interior"], count=20)
    K.export_glb(os.path.join(a["out"], f"{ASSET_ID}_fragments.glb"), frag_root)
    frag_root.hide_render = True
    for c in frag_root.children:
        c.hide_render = True

    blend_dir = os.path.join(os.path.dirname(a["out"].rstrip("/")), "..", "blender", "src")
    os.makedirs(blend_dir, exist_ok=True)
    K.save_blend(os.path.abspath(os.path.join(blend_dir, f"{ASSET_ID}.blend")))
    if a["turntable"]:
        K.turntable(ASSET_ID, os.path.join(a["out"], "..", "renders"), height=1.05)
    _ = sockets


if __name__ == "__main__":
    main()
