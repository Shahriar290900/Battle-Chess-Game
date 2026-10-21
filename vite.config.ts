import { defineConfig } from 'vite';

// BASE_PATH: '/Battle-Chess-Game/' for GitHub Pages, './' (default) for Capacitor and local builds.
export default defineConfig({
  base: process.env.BASE_PATH ?? './',
  assetsInclude: ['**/*.glb'],
  publicDir: 'public',
  build: { target: 'es2022', chunkSizeWarningLimit: 4000 },
  server: { host: true },
  test: { include: ['tests/**/*.test.ts'], environment: 'node', testTimeout: 120000 },
} as any);
