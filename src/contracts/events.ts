// Typed event bus + event names (architecture §4, choreography §8). Lead-owned.
import type { Faction, MoveResult, Role, Side, Square } from './types';

export interface GameEvents {
  'game:start': { mode: GameModeKind; fen: string };
  'turn:start': { side: Side; fen: string; moveNumber: number };
  'move:resolved': MoveResult;
  'move:step': { faction: Faction; role: Role };
  'capture:begin': { attacker: Role; defender: Role; attackerFaction: Faction; defenderFaction: Faction; square: Square };
  'capture:impact': { attacker: Role; defender: Role; attackerFaction: Faction; defenderFaction: Faction; heavy: boolean };
  'capture:shatter': { defender: Role; defenderFaction: Faction };
  'capture:end': { square: Square };
  'attack:whoosh': { role: Role; faction: Faction };
  'summon': { faction: Faction };
  'spell': { faction: Faction };
  'promotion': { side: Side; role: Role; square: Square };
  'castle': { side: Side };
  'check': { side: Side; kingSquare: Square };
  'game:over': { result: '1-0' | '0-1' | '1/2-1/2'; reason: 'checkmate' | 'stalemate' | 'draw' | 'resign' | 'threefold' | 'insufficient' | 'fifty-move' };
  'ui:select': { square: Square };
  'ui:click': Record<string, never>;
  'ai:thinking': { side: Side; thinking: boolean };
  'settings:changed': { key: string };
  /** Weapons meeting at impact (blocked/parried strike) — audio. */
  'clash': { attackerFaction: Faction; defenderFaction: Faction; heavy: boolean };
  /** A weapon hits the ground (checkmate surrender, or dropped in a fight). */
  'weapon:drop': { faction: Faction; role: Role };
  /** Physics contact of debris (rate-limited by fx), strength 0–1. */
  'debris:impact': { faction: Faction; strength: number };
  'taunt': { faction: Faction; role: Role };
  'surrender': { side: Side };
  'loading:progress': { loaded: number; total: number; stage: string };
  /** A piece glides across the board (stone/ice grinding loop). speed in squares/s; 'stop' ends the loop. */
  'move:slide': { faction: Faction; role: Role; phase: 'start' | 'stop'; speed: number };
  /** Shield/guard parries a blow (bright flash + ring). */
  'shield:flash': { faction: Faction };
  /** Shield or guard breaks apart. */
  'shield:break': { faction: Faction };
  /** Weapon bites armour (non-lethal beat inside a fight). */
  'armour:hit': { faction: Faction; heavy: boolean };
  /** Hop / leap / slam landing. strength 0–1. */
  'land': { faction: Faction; role: Role; strength: number };
}

export type GameModeKind = 'vs-ai' | 'hotseat';
export type EventName = keyof GameEvents;
type Handler<K extends EventName> = (payload: GameEvents[K]) => void;

export class EventBus {
  private handlers = new Map<EventName, Set<Handler<any>>>();

  on<K extends EventName>(name: K, fn: Handler<K>): () => void {
    let set = this.handlers.get(name);
    if (!set) this.handlers.set(name, (set = new Set()));
    set.add(fn);
    return () => set!.delete(fn);
  }

  emit<K extends EventName>(name: K, payload: GameEvents[K]): void {
    this.handlers.get(name)?.forEach((fn) => {
      try { fn(payload); } catch (err) { console.error(`[events] ${name} handler failed`, err); }
    });
  }
}

/** The single app-wide bus. */
export const bus = new EventBus();
