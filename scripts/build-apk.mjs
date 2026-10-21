// Builds the Android debug APK: music -> vite build (base ./) -> cap sync -> gradle assembleDebug -> dist-apk/.
import { execFileSync, execSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, statSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const env = { ...process.env };

if (!env.JAVA_HOME) {
  try { env.JAVA_HOME = execSync('/usr/libexec/java_home', { encoding: 'utf8' }).trim(); } catch { /* rely on PATH */ }
}
env.ANDROID_HOME ||= join(homedir(), 'Library/Android/sdk');
env.ANDROID_SDK_ROOT ||= env.ANDROID_HOME;
if (env.JAVA_HOME) env.PATH = `${join(env.JAVA_HOME, 'bin')}:${env.PATH}`;
console.log(`JAVA_HOME=${env.JAVA_HOME}\nANDROID_HOME=${env.ANDROID_HOME}`);

const run = (cmd, args, opts = {}) => {
  console.log(`\n> ${cmd} ${args.join(' ')}`);
  execFileSync(cmd, args, { cwd: root, env, stdio: 'inherit', ...opts });
};

const androidDir = join(root, 'android');
if (!existsSync(androidDir)) run('npx', ['cap', 'add', 'android']);
// Always keep local.properties pointing at the SDK (gitignored).
writeFileSync(join(androidDir, 'local.properties'), `sdk.dir=${env.ANDROID_HOME}\n`);

run('node', ['scripts/prepare-music.mjs']);
env.BASE_PATH = './';
run('npx', ['vite', 'build']);
run('npx', ['cap', 'sync', 'android']);
run('./gradlew', ['assembleDebug', '--no-daemon', '-q'], { cwd: androidDir });

const built = join(androidDir, 'app/build/outputs/apk/debug/app-debug.apk');
if (!existsSync(built)) { console.error(`APK not found at ${built}`); process.exit(1); }
const outDir = join(root, 'dist-apk');
mkdirSync(outDir, { recursive: true });
const out = join(outDir, 'battle-chess-debug.apk');
copyFileSync(built, out);
console.log(`\nAPK: ${out} (${(statSync(out).size / 1048576).toFixed(1)} MB)`);
