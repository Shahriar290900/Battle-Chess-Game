// Asset contract v1 (skill references/asset-pipeline.md §1). Lead-owned.
// Changing anything here requires updating scripts/validate_glb.py in the same commit.
import type { Faction, Role } from './types';

export const CONTRACT_VERSION = 1;

export const FACTIONS: readonly Faction[] = ['emberhold', 'rime'];
export const ROLES: readonly Role[] = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'];

export type AssetId = `${Faction}_${Role}`;
export const assetId = (faction: Faction, role: Role): AssetId => `${faction}_${role}`;
export const ALL_ASSET_IDS: AssetId[] = FACTIONS.flatMap((f) => ROLES.map((r) => assetId(f, r)));

/** URL (relative to the app base) of a piece or its fragment set. */
export const modelUrl = (id: AssetId) => `models/${id}.glb`;
export const fragmentsUrl = (id: AssetId) => `models/${id}_fragments.glb`;

/** Required clips (validator-enforced). */
export const CLIPS = ['Idle', 'Move', 'Attack', 'HitReact', 'Victory'] as const;
/** Optional clips (contract v1.1). Taunt: provoke gesture toward the enemy king while giving check (1–1.6 s, once). */
export const OPTIONAL_CLIPS = ['Taunt'] as const;
export type ClipName = (typeof CLIPS)[number] | (typeof OPTIONAL_CLIPS)[number];
export const LOOPING_CLIPS: readonly ClipName[] = ['Idle', 'Move'];

export const BONES_REQUIRED = ['root', 'body', 'top'] as const;
export const BONES_HUMANOID = ['spine', 'head', 'arm_L', 'hand_L', 'arm_R', 'hand_R'] as const;
export const BONES_KNIGHT = ['mount_body', 'mount_head'] as const;

export const SOCKETS = ['socket_weapon_R', 'socket_cast', 'socket_impact', 'socket_head'] as const;
export type SocketName = (typeof SOCKETS)[number];

/** Queens only: node scaled 0 except during Attack. */
export const WEAPON_SUMMON_NODE = 'weapon_summon';

export const lodName = (id: AssetId, lod: 0 | 1) => `${id}_LOD${lod}`;
export const fragmentsRootName = (id: AssetId) => `${id}_fragments`;
export const FRAGMENT_PREFIX = 'frag_';

export type AttackStyle = 'melee' | 'leap' | 'ranged' | 'slam' | 'summon';

/** Root-node glTF extras (three.js GLTFLoader exposes these as root.userData). */
export interface PieceExtras {
  faction: Faction;
  role: Role;
  displayName: string;
  impactTime: number;
  strikeRange: number;
  attackStyle: AttackStyle;
  contractVersion: number;
}

/** Heights to top of tallest feature (art-bible §2); pedestal Ø 0.80, 0.22 tall. */
export const ROLE_HEIGHT: Record<Role, number> = {
  pawn: 1.05, rook: 1.2, knight: 1.3, bishop: 1.4, queen: 1.55, king: 1.7,
};
export const PEDESTAL_HEIGHT = 0.22;
export const PEDESTAL_DIAMETER = 0.8;

/** Defaults used when a GLB lacks extras (procedural fallback). */
export const DEFAULT_EXTRAS: Record<Role, Omit<PieceExtras, 'faction' | 'displayName' | 'contractVersion'>> = {
  pawn: { role: 'pawn', attackStyle: 'melee', impactTime: 0.95, strikeRange: 0.55 },
  rook: { role: 'rook', attackStyle: 'slam', impactTime: 0.75, strikeRange: 0.1 },
  knight: { role: 'knight', attackStyle: 'leap', impactTime: 1.0, strikeRange: 0.5 },
  bishop: { role: 'bishop', attackStyle: 'ranged', impactTime: 1.1, strikeRange: 1.5 },
  queen: { role: 'queen', attackStyle: 'summon', impactTime: 1.3, strikeRange: 0.7 },
  king: { role: 'king', attackStyle: 'melee', impactTime: 1.2, strikeRange: 0.6 },
};

/** Art-bible display names. Never use franchise names. */
export const DISPLAY_NAME: Record<AssetId, string> = {
  emberhold_pawn: 'Emberhold Shieldbearer', rime_pawn: 'Rime Thrall',
  emberhold_rook: 'Emberhold Forge Bastion', rime_rook: 'Rime Glacier Bastion',
  emberhold_knight: 'Emberhold Ashmane Rider', rime_knight: 'Rime Gravewind Rider',
  emberhold_bishop: 'Emberhold Cinder Oracle', rime_bishop: 'Rime Frost Chanter',
  emberhold_queen: 'Emberhold Flamecrown Warden', rime_queen: 'Rime Pale Tide Queen',
  emberhold_king: 'Emberhold Ember Sovereign', rime_king: 'Rime Glacier Tyrant',
};

export const FACTION_NAME: Record<Faction, string> = { emberhold: 'Emberhold', rime: 'Rime Host' };

/** Faction palette (art-bible §3–4), hex. */
export const PALETTE = {
  emberhold: { bronze: 0xa8713a, steel: 0x3b3a38, ember: 0xff7a1a, cloth: 0x5e1f1a, fur: 0x6b5440, soot: 0x1e1814 },
  rime: { obsidian: 0x10151c, armour: 0x1c2e44, silver: 0x9fb4c4, ice: 0x7fd3f0, glow: 0x6ff3ff, frost: 0xdceff7 },
} as const;

/** Fragment counts by defender role (choreography §4). */
export const FRAGMENT_COUNT: Record<Role, number> = {
  pawn: 20, rook: 30, knight: 30, bishop: 30, queen: 40, king: 40,
};
