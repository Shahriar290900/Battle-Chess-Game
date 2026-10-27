// Per-persona instrumentation sink: action log, anomalies, console, latency, fps, screenshots, summary.
import { appendFileSync, mkdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const SHOT_CAP_BYTES = 20 * 1024 * 1024; // all screenshots of a run; logs add a few MB

const pct = (a, p) => (a.length ? a[Math.min(a.length - 1, Math.floor(p * a.length))] : null);
export function stats(values) {
  if (!values.length) return { n: 0 };
  const a = values.slice().sort((x, y) => x - y);
  const mean = a.reduce((s, v) => s + v, 0) / a.length;
  return { n: a.length, mean: +mean.toFixed(1), p50: +pct(a, 0.5).toFixed(1), p95: +pct(a, 0.95).toFixed(1), max: +a[a.length - 1].toFixed(1) };
}

export class Recorder {
  constructor(outRoot, personas) {
    this.root = outRoot;
    this.t0 = Date.now();
    this.page = null;
    this.shotBytes = 0;
    this.shotsSkipped = 0;
    this.cur = personas[0];
    this.phase = 'boot';
    this.p = {};
    rmSync(outRoot, { recursive: true, force: true });
    for (const name of personas) {
      const dir = join(outRoot, name);
      mkdirSync(join(dir, 'shots'), { recursive: true });
      this.p[name] = {
        name, dir, actions: 0, byAction: {}, anomalies: {}, anomalyKeys: new Set(), anomalyTotal: 0, shots: 0, shotsByType: {},
        console: { error: 0, warning: 0, pageerror: 0, keys: new Map() }, lat: {}, fps: [], games: [], phases: [], notes: [],
      };
    }
  }
  get P() { return this.p[this.cur]; }
  use(persona, phase) { this.cur = persona; if (phase) this.phase = phase; }
  now() { return +((Date.now() - this.t0) / 1000).toFixed(2); }
  _w(file, obj, p = this.P) { appendFileSync(join(p.dir, file), JSON.stringify(obj) + '\n'); }

  act(action, target, extra = {}) {
    const p = this.P;
    p.actions++; p.byAction[action] = (p.byAction[action] || 0) + 1;
    this._w('actions.jsonl', { ts: new Date().toISOString(), t: this.now(), persona: p.name, phase: this.phase, action, target, ...extra });
  }

  /** Record an anomaly; first occurrences (per type, up to a cap) also get a screenshot. */
  async anomaly(type, detail, o = {}) {
    const p = this.P;
    const key = `${type}|${o.key ?? String(detail).slice(0, 100)}|${o.scope ?? ''}`;
    p.anomalyTotal++;
    const a = (p.anomalies[type] ??= { unique: 0, occurrences: 0 });
    a.occurrences++;
    if (p.anomalyKeys.has(key)) return;
    p.anomalyKeys.add(key);
    a.unique++;
    let shot = null;
    if (o.shot !== false && this.page && !this.page.isClosed() && (p.shotsByType[type] ?? 0) < 3 && p.shots < 30) {
      p.shotsByType[type] = (p.shotsByType[type] ?? 0) + 1;
      shot = await this.shot(`shots/anom-${String(p.shots + 1).padStart(3, '0')}-${type}.jpg`).catch(() => null);
    }
    this._w('anomalies.jsonl', { ts: new Date().toISOString(), t: this.now(), persona: p.name, phase: this.phase, type, severity: o.severity ?? 'warn', detail, key: o.key, scope: o.scope, shot, data: o.data });
    console.log(`  [anomaly ${p.name}] ${type}: ${String(detail).slice(0, 160)}`);
  }

  /** Small JPEG (q60) screenshot; the whole run's screenshots are capped (disk is tight). */
  async shot(rel) {
    const p = this.P;
    if (this.shotBytes >= SHOT_CAP_BYTES) { this.shotsSkipped++; return null; }
    const name = (rel.startsWith('shots/') ? rel : `shots/${rel}`).replace(/\.png$/, '.jpg');
    const path = join(p.dir, name);
    await this.page.screenshot({ path, type: 'jpeg', quality: 60 });
    try { this.shotBytes += statSync(path).size; } catch { /* ignore */ }
    p.shots++;
    return name;
  }

  consoleMsg(kind, text, loc) {
    const p = this.P;
    p.console[kind]++;
    const norm = text.replace(/\d+(\.\d+)?/g, '#').slice(0, 200);
    const e = p.console.keys.get(norm) ?? { count: 0, first: text.slice(0, 400), kind, loc };
    e.count++;
    p.console.keys.set(norm, e);
    this._w('console.jsonl', { ts: new Date().toISOString(), t: this.now(), persona: p.name, phase: this.phase, kind, text: text.slice(0, 600), loc });
  }

  lat(kind, ms) {
    if (!Number.isFinite(ms) || ms < 0) return;
    const p = this.P;
    (p.lat[kind] ??= []).push(ms);
    this._w('latency.jsonl', { t: this.now(), phase: this.phase, kind, ms: +ms.toFixed(1) });
  }

  fpsSample(label, s) {
    this.P.fps.push({ label, phase: this.phase, ...s });
    this._w('fps.jsonl', { t: this.now(), phase: this.phase, label, ...s });
  }

  game(g) { this.P.games.push({ ...g, t: this.now() }); this._w('actions.jsonl', { ts: new Date().toISOString(), t: this.now(), persona: this.P.name, phase: this.phase, action: 'game-summary', target: g.label, ...g }); }
  note(text) { this.P.notes.push(text); }

  summary(extra = {}) {
    const out = {};
    for (const [name, p] of Object.entries(this.p)) {
      const lat = {};
      for (const [k, v] of Object.entries(p.lat)) lat[k] = stats(v);
      const s = {
        persona: name, actions: p.actions, actionsByType: p.byAction, games: p.games,
        anomalies: { totalOccurrences: p.anomalyTotal, byType: p.anomalies },
        console: { error: p.console.error, warning: p.console.warning, pageerror: p.console.pageerror, distinct: [...p.console.keys.values()].sort((a, b) => b.count - a.count).slice(0, 40) },
        latencyMs: lat, fps: p.fps, screenshots: p.shots, screenshotsSkippedByCap: this.shotsSkipped, notes: p.notes, ...extra,
      };
      out[name] = s;
      writeFileSync(join(p.dir, 'summary.json'), JSON.stringify(s, null, 2));
    }
    return out;
  }
}
