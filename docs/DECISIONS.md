# Decisions

| # | Decision | Why |
|---|---|---|
| 1 | **Web first** (Vite + TS + three.js), shipped as GitHub Pages site **and** an Android debug APK via Capacitor 7. | One codebase for PC browser, phone browser, APK. |
| 2 | **Modes:** vs Computer (Stockfish 19 lite single-thread WASM in a Worker; Easy/Medium/Hard/Master) and local **pass-and-play** 2-player. No online play. | Single-thread build needs no SharedArrayBuffer/COOP/COEP, so it runs on Pages and in the APK WebView. GPL is fine: personal, non-commercial project. |
| 3 | **No Blender/Unity.** Assets come from a Python "code forge" (`tools/forge/`, numpy + Pillow) writing contract-v1 GLBs; turntables rendered by headless three.js (Playwright). | Machine has no DCC tools. Result is a stylised painted-miniature look, not sculpted. |
| 4 | **Original IP only.** Factions Emberhold (White) vs Rime Host (Black) with art-bible names. No franchise names, crests or sculpt references in the repo. | Skill ground rule 1; repo is public. |
| 5 | **Music:** user's MP3 is copied to `public/audio/theme.mp3` by `npm run prepare-music` and is **gitignored**. Public Pages build has no theme; players can load their own track (IndexedDB). Local + APK builds include it. | Repo is public; avoid redistributing a copyrighted track. |
| 6 | **SFX are procedural** (WebAudio synthesis) — no sample files. | Code-only, zero licensing. |
| 7 | **Facing:** pieces face the enemy. Emberhold rest yaw = π (faces −z), Rime rest yaw = 0 (faces +z). GLB front is +Z. | Battle-chess staging; the skill text's "faces White" note was ambiguous. |
| 8 | **Node 20** toolchain: Vite 7.3.7, Vitest 4.1.11, TS 5.9.3, Capacitor 7.6.9 (Vitest 5 / Capacitor 8 need Node 22). `.npmrc legacy-peer-deps=true` (npm 10 arborist peer bug). All versions published before 2026-10-07. | Avoid changing the machine's Node. |
| 9 | **Quality tiers:** High (desktop dGPU), Medium (default desktop/iGPU), Low (mobile/APK: LOD1, no transmission, 1024 shadows, 120 particles, no SMAA). Auto-picked by 2 s benchmark + `isMobile`. | Budget: 60 fps Medium on iGPU; captures ≥ 30 fps. |
| 10 | Contract v1 per skill `references/asset-pipeline.md` §1; TS mirror in `src/contracts/`. Module boundaries in `src/contracts/apis.ts`. Only the lead edits `src/contracts/**`. | Parallel agents code against interfaces. |
| 11 | Camera default **Follow turn** in pass-and-play, **Fixed to my side** vs AI. | Architecture §7. |
| 12 | Base path: `./` for local/Capacitor, `/Battle-Chess-Game/` for Pages (`BASE_PATH` env). Assets referenced relative to `import.meta.env.BASE_URL`. | Same build works in both hosts. |
| 13 | GLBs live in `public/models/` (served as-is by Vite, copied into the APK). Forge writes there directly. | No copy step, one source of truth. |
| 14 | Playwright drives the **system Google Chrome** (`chromium.launch({ channel: "chrome" })`) — Playwright-bundled Chromium is unsupported on macOS 12. WebGL2 works headless. | Screenshots/turntables/smoke tests. |
