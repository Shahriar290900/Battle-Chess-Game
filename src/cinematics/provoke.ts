// Check provoke: the piece giving check turns to the enemy king and taunts it (Taunt clip, or a strong procedural
// taunt per role); the king looks back and recoils while the aura pulses and the tile glows. Short camera move that
// frames both pieces. Quick = faster, Off = aura + tint only.
import { Vector3 } from 'three';
import type { Faction, PieceActor, Role, Square } from '../contracts';
import { restYaw, yawToward } from '../contracts';
import { CameraDriver } from './cameraDriver';
import { clamp, flatDir, hasShield, socketObject, socketPos, wrapPi } from './common';
import { FightFrame } from './fightFrame';
import { pickShot } from './shotPicker';
import type { Stage } from './stage';

const AURA_TINT: Record<Faction, number> = { emberhold: 0xff4a2a, rime: 0x66e6ff };
export const PROVOKE_QUICK_SCALE = 1.8;

/** Procedural taunts used when the asset has no Taunt clip. Returns the end time. */
function proceduralTaunt(stage: Stage, a: PieceActor, king: PieceActor, P0: number): number {
  const { ctx } = stage;
  const ember = a.faction === 'emberhold';
  const toKing = flatDir(a.root.position, king.root.position);
  const home = a.root.position.clone();
  const spark = ember ? 'sparks' : 'iceGlitter';
  const at = (t: number, fn: () => void) => stage.at(P0 + t, fn);
  const weaponPos = () => socketPos(a, 'socket_weapon_R', new Vector3());
  switch (a.role) {
    case 'pawn': // weapon-beat on the shield, three times
      for (let k = 0; k < 3; k++) {
        const t = 0.1 + k * 0.27;
        stage.tilt(a, 0.18, P0 + t, 0.08, 'power3.out');
        stage.tilt(a, 0, P0 + t + 0.08, 0.14, 'power2.out');
        at(t + 0.06, () => { stage.emit(spark, weaponPos(), { count: 10, scale: 0.6 }); ctx.camera.shake(0.1); stage.bus('shield:flash', { faction: a.faction }); });
      }
      return P0 + 0.95;
    case 'rook': { // brazier flare and lurch
      const lurch = home.clone().addScaledVector(toKing, 0.35);
      stage.glide(a, lurch, P0 + 0.1, 0.2, 'power3.out');
      stage.tilt(a, 0.28, P0 + 0.1, 0.2, 'power3.out');
      at(0.25, () => {
        const top = socketPos(a, 'socket_head', new Vector3());
        if (ember) { stage.emit('embers', top, { count: 50, direction: new Vector3(0, 1, 0), speed: 4, spread: 0.6, scale: 1.2 }); stage.emit('fireWave', top, { direction: toKing.clone(), duration: 0.25, speed: 5, count: 24 }); }
        else { stage.emit('frostMist', top, { count: 16, scale: 1.2 }); stage.emit('iceGlitter', top, { count: 30, direction: new Vector3(0, 1, 0), speed: 4 }); }
        ctx.camera.shake(0.25);
      });
      stage.glide(a, home, P0 + 0.65, 0.35, 'power2.inOut');
      stage.tilt(a, 0, P0 + 0.65, 0.35, 'power2.out');
      at(1.0, () => stage.bus('land', { faction: a.faction, role: 'rook', strength: 0.4 })); // settles back onto its square
      return P0 + 1.05;
    }
    case 'knight': // rear and snort
      stage.tilt(a, -0.55, P0 + 0.05, 0.35, 'power2.out');
      stage.tilt(a, 0.12, P0 + 0.55, 0.12, 'power3.in');
      stage.tilt(a, 0, P0 + 0.7, 0.3, 'power2.out');
      at(0.62, () => {
        const head = socketPos(a, 'socket_head', new Vector3());
        stage.emit(ember ? 'smoke' : 'frostMist', head, { count: 14, direction: toKing.clone(), speed: 2.5, scale: 0.8 });
        if (ember) stage.emit('embers', head, { count: 14, direction: toKing.clone(), speed: 3 });
        stage.emit('dustPuff', home.clone().setY(0.05), { count: 8, scale: 0.9 });
        stage.bus('land', { faction: a.faction, role: 'knight', strength: 0.5 }); // forelegs come down
        ctx.camera.shake(0.2);
      });
      return P0 + 1.05;
    case 'bishop': { // censer swirl / rune flare
      const base = a.getYaw();
      stage.proxy(P0 + 0.05, 1.0, 'none', (p) => a.setYaw(base + 0.3 * Math.sin(p * Math.PI * 3) * Math.sin(p * Math.PI)));
      at(0.05, () => {
        stage.bus('spell', { faction: a.faction });
        const f = socketObject(a, 'socket_cast');
        stage.emit(ember ? 'embers' : 'iceGlitter', socketPos(a, 'socket_cast', new Vector3()), { follow: f, duration: 0.9, count: 30, scale: 0.8 });
        if (!ember) stage.emit('summonSpiral', socketPos(a, 'socket_cast', new Vector3()), { follow: f, duration: 0.9, scale: 0.8 });
      });
      at(0.95, () => stage.emit(ember ? 'fireWave' : 'frostBeam', socketPos(a, 'socket_cast', new Vector3()), { direction: toKing.clone(), duration: 0.3, speed: 6, count: 30 }));
      return P0 + 1.15;
    }
    case 'queen': // point with a summoned-weapon flash
      at(0, () => { stage.bus('summon', { faction: a.faction }); stage.emit('summonSpiral', home.clone().setY(0.1), { duration: 0.4, count: 24 }); });
      stage.proxy(P0, 0.35, 'power2.out', (p) => a.setWeaponSummon(1.15 * p));
      stage.proxy(P0 + 0.35, 0.1, 'power1.out', (p) => a.setWeaponSummon(1.15 - 0.15 * p));
      stage.tilt(a, 0.15, P0 + 0.3, 0.2, 'power2.out');
      at(0.7, () => { stage.emit(spark, weaponPos(), { count: 30, scale: 1.1 }); ctx.camera.shake(0.15); });
      stage.tilt(a, 0, P0 + 0.95, 0.25, 'power2.out');
      stage.proxy(P0 + 0.95, 0.3, 'power1.in', (p) => a.setWeaponSummon(1 - p));
      return P0 + 1.3;
    case 'king': // fist raise
      if (a.hasClip('Victory')) stage.poseClip(a, 'Victory', 0.4, P0 + 0.05, 0.35);
      stage.tilt(a, -0.2, P0 + 0.05, 0.3, 'power2.out');
      at(0.4, () => { stage.emit(spark, weaponPos(), { count: 26, scale: 0.9 }); ctx.camera.shake(0.18); });
      stage.tilt(a, 0, P0 + 0.85, 0.3, 'power2.out');
      return P0 + 1.15;
  }
}

/** Returns the extra speed scale for the stage (Quick plays faster). */
export function buildCheck(stage: Stage, kingSquare: Square): number {
  const { ctx, tl } = stage;
  const { board, fx, move, camera } = ctx;
  const mode = ctx.settings.captureMode;
  const king = board.actorAt(kingSquare);
  if (!king) { tl.set({}, {}, 0.01); return 1; }
  const checker = board.actorAt(move.to);
  const prov = checker && checker !== king ? checker : null;
  const tint = AURA_TINT[king.faction];
  const aura = () => fx.aura(socketPos(king, 'socket_head', new Vector3()), king.faction);

  // ---- Off: just the aura and the tile glow
  if (mode === 'off' || !prov) {
    stage.at(0.1, () => { board.tintSquare(kingSquare, tint); aura(); });
    stage.at(0.1, () => stage.bus('taunt', { faction: (prov ?? king).faction, role: (prov ?? king).role }));
    tl.set({}, {}, 0.8);
    stage.onSettle(() => { board.tintSquare(kingSquare, null); king.play('Idle', { fade: 0 }); });
    return 1;
  }

  const quick = mode === 'quick';
  const P0 = 0.35;
  const bystanders = board.allActors().filter((a) => a !== king && a !== prov);
  const rest = restYaw(prov.side); const kingRest = restYaw(king.side);
  const faceYaw = yawToward(prov.root.position, king.root.position);
  const headK = () => socketPos(king, 'socket_head', new Vector3());
  const headP = () => socketPos(prov, 'socket_head', new Vector3());

  // ---- camera: one clear shot that frames both pieces
  let driver: CameraDriver | null = null;
  let restoreStarted = false;
  try {
    driver = new CameraDriver(camera.borrow(), () => board.allActors());
    const seatZ: 1 | -1 = camera.camera.position.z >= 0 ? 1 : -1;
    const inputs = { attacker: () => prov.root.position, defender: () => king.root.position, seatZ, aspect: () => camera.camera.aspect || 16 / 9 };
    driver.setCues([{ at: 0, shot: pickShot('lowSide', inputs, bystanders, board.allActors()) }], 0.4);
  } catch (e) { console.warn('[cinematics] camera.borrow failed', e); }
  const frame = new FightFrame(stage, {
    driver, keyFaction: prov.faction, rimFaction: king.faction,
    focus: () => [prov.root.position, king.root.position], bystanders: () => bystanders,
  });
  const startRestore = () => {
    if (restoreStarted || !driver) return;
    restoreStarted = true; driver.released = true; frame.release();
    stage.safe(() => { stage.track(camera.restore(0.45)); });
  };
  tl.eventCallback('onUpdate', () => frame.update(tl.time()));
  frame.fadeIn(0, 0.3);

  // ---- turn to face each other; kinematics look-at when available
  stage.yaw(prov, faceYaw, 0, 0.3, 'power2.out');
  if (stage.hasKinematics) {
    stage.at(0.15, () => { stage.look(king, headP(), 1); stage.look(prov, headK(), 1); });
  } else {
    stage.yaw(king, kingRest + clamp(wrapPi(yawToward(king.root.position, prov.root.position) - kingRest) * 0.6, -1.1, 1.1), 0.15, 0.3, 'power2.out');
  }
  stage.at(0.2, () => board.tintSquare(kingSquare, tint));

  // ---- provoke
  stage.at(P0, () => stage.bus('taunt', { faction: prov.faction, role: prov.role as Role }));
  let tauntEnd: number;
  if (prov.hasClip('Taunt')) {
    tauntEnd = stage.clip(prov, 'Taunt', P0, 1.6);
    stage.at(P0 + 0.4, () => stage.emit(prov.faction === 'emberhold' ? 'sparks' : 'iceGlitter', socketPos(prov, 'socket_weapon_R', new Vector3()), { count: 14, scale: 0.7 }));
    if (hasShield(prov.role)) stage.at(P0 + 0.45, () => stage.bus('shield:flash', { faction: prov.faction }));
  } else {
    tauntEnd = proceduralTaunt(stage, prov, king, P0);
  }

  // ---- king reacts: aura pulses, small recoil, flinch
  stage.at(P0 + 0.45, aura);
  stage.at(P0 + 0.95, aura);
  stage.tilt(king, -0.2, P0 + 0.5, 0.12, 'power3.out');
  stage.tilt(king, 0, P0 + 0.62, 0.35, 'power2.out');
  stage.poseClip(king, 'HitReact', 0.3, P0 + 0.5, 0.15);
  stage.proxy(P0 + 0.65, 0.3, 'power2.inOut', (p) => king.scrub('HitReact', king.clipDuration('HitReact') * 0.3 * (1 - p)));

  // ---- wrap up
  const end = Math.max(tauntEnd, P0 + 1.0) + 0.35;
  stage.at(end - 0.45, startRestore);
  frame.fadeOut(end - 0.45, 0.3);
  stage.yaw(prov, rest, end - 0.4, 0.3);
  stage.yaw(king, kingRest, end - 0.4, 0.3);
  stage.at(end - 0.4, () => { stage.unlook(king); stage.unlook(prov); });
  tl.set({}, {}, end);
  stage.onSettle((reason) => {
    board.tintSquare(kingSquare, null);
    prov.setYaw(rest); king.setYaw(kingRest);
    prov.setWeaponSummon(0);
    prov.play('Idle', { fade: 0 }); king.play('Idle', { fade: 0 });
    if (driver && (!restoreStarted || reason !== 'complete')) { restoreStarted = true; driver.released = true; stage.safe(() => { stage.track(camera.restore(reason === 'complete' ? 0.2 : 0)); }); }
  });
  return quick ? PROVOKE_QUICK_SCALE : 1;
}
