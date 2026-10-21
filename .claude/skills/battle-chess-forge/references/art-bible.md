# Art Bible — Emberhold vs the Rime Host

All designs here are original to this project. Keep them that way: when inventing extra
detail, invent — don't borrow crests, crowns, creatures or costumes from existing works.

## Contents
1. Visual goals
2. Shared rules (scale, pedestal, readability)
3. Faction: Emberhold (White)
4. Faction: Rime Host (Black)
5. Piece sheets (12)
6. Material library
7. Lighting & presentation

---

## 1. Visual goals

- **Collector miniature, not cartoon.** Proportions ~6.5–7 heads tall for humanoids, not
  chibi. Small heads, believable hands, weight in the stance.
- **Silhouette first.** Every role must be identifiable from a top-down 45° camera at 1080p
  when the piece is ~60 px tall. Each role has one signature shape (listed per sheet) that is
  exaggerated ~15%.
- **Material storytelling.** Emberhold = warm forged metal, leather, fur, soot, glowing
  embers in cracks. Rime Host = black volcanic glass armour, translucent blue ice, frost
  build-up, cold inner glow. Factions must read apart in greyscale (Emberhold mid-value,
  Rime Host very dark with bright ice accents).
- **Breakable look.** Pieces are "living statues". Their material justifies shattering:
  Emberhold cracks into bronze/stone chunks spilling embers; Rime Host shatters into ice
  shards and frost mist.

## 2. Shared rules

- Units: 1 unit = 1 board square edge. Pedestal diameter 0.80. Heights: pawn 1.05, rook
  1.20, knight 1.30, bishop 1.40, queen 1.55, king 1.70 (to top of tallest feature,
  weapons included in idle pose).
- Pedestal: two-tier octagonal-to-round plinth, 0.22 tall, faction trim band, a single
  inset faction emblem on the front face (see faction emblems). Bottom at y=0 (glTF Y-up).
- Front of every piece faces +Z in glTF space. The engine rotates Black 180°.
- Idle pose holds weapons in a way that the capture clip can "draw" or "raise" them.
  Queens start with no great-weapon visible — it is summoned in the attack.

## 3. Emberhold (White)

Highland forge-kingdom. Riveted bronze plate over quilted gambesons, banded fur mantles,
braided leather. Weapons: broad leaf-blade swords, hooked axes, round shields with forge
rings. Emblem: **an anvil inside a ring of six flames**.
Palette: aged bronze #A8713A, blackened steel #3B3A38, ember orange #FF7A1A (emissive),
oxblood cloth #5E1F1A, warm fur #6B5440, soot #1E1814.

## 4. Rime Host (Black)

Revenants from a frozen sea. Armour is faceted black obsidian plates bound with pale
silver wire; ice grows out of joints and along edges as crystal clusters. Eyes and runes
glow cold cyan. Cloth is tattered, stiff with frost. Emblem: **a six-pointed snow-crystal
pierced by a downward blade**.
Palette: obsidian #10151C, deep armour blue #1C2E44, silver wire #9FB4C4, glacial ice
#7FD3F0 (subsurface/transmission), cyan glow #6FF3FF (emissive), frost white #DCEFF7.

## 5. Piece sheets

Format: name — concept; signature shape; idle pose; capture idea (details in
capture-choreography.md); detail notes.

### Pawn
- **Emberhold Shieldbearer** — young levy in bronze half-plate. Signature: big round shield
  with forge-ring boss. Idle: shield forward, short sword sheathed on hip. Capture: draws
  sword, shield-bash then overhead chop. Detail: rivets, dented shield rim, fur collar.
- **Rime Thrall** — hunched revenant foot-soldier. Signature: icicle spikes along the spine
  and a jagged ice cleaver. Idle: cleaver lowered, head tilted. Capture: lunging two-hand
  hack. Detail: cracked obsidian chest plate, frost on shoulders, glowing eye slits.

### Rook
- **Emberhold Forge Bastion** — squat round tower with a working brazier crown and a
  bronze battering-ram face. Signature: brazier flames on top. Idle: flames flicker
  (emissive + particles). Capture: tower lifts, lurches forward and slams down, ram-face
  first. Detail: masonry courses, bronze strapwork, arrow slits glowing inside.
- **Rime Glacier Bastion** — a tower of stacked ice monoliths with an obsidian core.
  Signature: crown of tilted ice shards. Capture: shards fire as spikes, then the tower
  topples onto the target. Detail: trapped bubbles in the ice, cracks with cyan glow.

### Knight
- **Emberhold Ashmane Rider** — armoured rider on a heavy war-elk with a mane of smouldering
  embers; lance with pennon. Signature: the elk's broad forward-swept horns and ember
  mane. Capture: rears, leaping arc, lance strike on landing. Detail: barding plates, saddle
  stitching, embers drifting from mane.
- **Rime Gravewind Rider** — skeletal rider on a gaunt ice ram whose horns are crystal
  spirals. Signature: spiral crystal horns. Capture: leaping arc, ram headbutt then rider's
  hooked glaive. Detail: exposed rib cage of the mount filled with frost-light.

### Bishop
- **Emberhold Cinder Oracle** — hooded seer carrying a chained censer-staff that swings
  smoke and embers. Signature: tall hood + hanging censer. Capture: swings censer in a
  circle, releases a fire wave that cracks the target. Detail: embroidered stole, prayer
  beads, soot on hem.
- **Rime Frost Chanter** — gaunt caster with a lantern of trapped blue light on a crooked
  staff; floating ice runes orbit it. Signature: lantern staff + orbiting runes. Capture:
  runes converge into a beam; target freezes white then bursts. Detail: frozen beard,
  layered robes.

### Queen
- **Emberhold Flamecrown Warden** — armoured warrior-queen, swept bronze pauldrons, cloak
  of overlapping bronze scales. Signature: tall forged crown of upward blade-points with an
  ember gem. Idle: empty hands, cloak settled. Capture: summons a huge two-handed
  hammer-staff out of embers, spins, ground-slam shockwave. Detail: filigree on breastplate,
  braided hair, scale cloak with per-scale bevels.
- **Rime Pale Tide Queen** — tall spectral queen in obsidian gown-armour that frays into
  ice at the hem. Signature: a floating crescent halo of ice behind the head. Capture: pulls
  a long crystal glaive from the air, glides, sweeping cut that freezes and shatters.
  Detail: translucent ice veil, silver wire lacing, frost trailing on the floor.

### King
- **Emberhold Ember Sovereign** — older broad-shouldered king, bronze plate, a plain heavy crown
  (thick band, six squat points, ember gems), greatsword
  resting point-down. Signature: greatsword + heavy crown. Capture: slow walk, one
  decisive overhead cleave, time slows on impact. Detail: battle-worn plate, fur mantle,
  rings on gauntlets.
- **Rime Glacier Tyrant** — massive armoured revenant lord, obsidian plate, ice breaking
  through the back like a ridge, crown formed by a ring of short vertical ice prisms
  hovering just above the head. Signature: back ridge + hovering prism ring. Capture:
  raises a fist, the floor beneath the target erupts in ice spikes, then he backhands the
  frozen target. Detail: cape frozen mid-sway, silver wire runes, cracked visor glowing.

## 6. Material library

Build these as Blender node groups so every piece shares them (and fragments inherit them):

| Material | Base | Key maps / tricks |
|---|---|---|
| `EH_Bronze` | metallic 1, rough 0.35 | curvature-driven edge wear, cavity grime, faint hammered normal |
| `EH_Steel` | metallic 1, rough 0.45 | blackened with polished edges |
| `EH_Leather` | metallic 0, rough 0.7 | grain normal, stitch normal detail |
| `EH_Fur` | metallic 0, rough 0.85 | card or sculpted clumps, AO strong |
| `EH_Cloth` | metallic 0, rough 0.9 | weave normal, soot gradient at hem |
| `EH_Stone` | pedestal | chipped edges, ember-glow emissive in cracks (mask) |
| `EH_Ember` | emissive #FF7A1A × 4–8 | used in cracks, eyes of the elk, braziers |
| `RH_Obsidian` | metallic 0.2, rough 0.12 | conchoidal fracture normal, sharp spec |
| `RH_Ice` | transmission 0.9, IOR 1.31, rough 0.08 | thickness map, inner cracks texture; export as KHR_materials_transmission + volume |
| `RH_Frost` | rough 0.9, white | top-facing mask (normal.y) build-up |
| `RH_Silver` | metallic 1, rough 0.3 | wire, crowns |
| `RH_Glow` | emissive #6FF3FF × 3–6 | eyes, runes, lantern |

Web note: transmission is expensive; for the low-spec quality tier swap `RH_Ice` for a
fake-refraction shader (fresnel + matcap + emissive inner glow) — see vfx notes in
capture-choreography.md.

## 7. Lighting & presentation

- Board: dark carved stone with bronze inlay on Emberhold's side transitioning to frosted
  obsidian on the Rime side (an original board, not a printed franchise board).
- Key light warm from the Emberhold side, rim light cold from the Rime side, low ambient,
  HDRI for reflections, ACES/AgX tone mapping, bloom only on emissives.
- Turntable renders for approval: 1920×1080, 3/4 view, both factions per role side by side.
