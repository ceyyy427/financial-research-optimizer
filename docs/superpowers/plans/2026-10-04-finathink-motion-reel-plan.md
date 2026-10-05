# Finathink Bilingual Motion Reel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate a 15-second bilingual Finathink brand motion-graphics reel from the approved design, using the installed `ruic-motion-reel` engine and the two existing product images as the opening transition.

**Architecture:** Create a self-contained `motion-reel/` project from the installed template. Keep brand identity and timing in `theme.py`, reusable bilingual layout/image/transition helpers in `scenes.py`, and audio generation in the copied template audio module. Use a local machine font path for Chinese glyphs without redistributing a system font. Render stills per scene before the full film, then verify the encoded artifact with `ffprobe` and audio checks.

**Tech Stack:** Python 3, NumPy, Pillow, FFmpeg, the installed `ruic-motion-reel` engine, bundled Latin fonts plus a verified macOS CJK system font, H.264 video, AAC audio.

**Spec:** `docs/superpowers/specs/2026-10-04-finathink-motion-reel-design.md`

## Global Constraints

- Delivery is exactly 1920×1080, 30fps, 450 frames, and 15.000 seconds.
- The timeline is 8 bars at 128 BPM; each scene is one 1.875-second bar.
- English is the primary title language and Chinese is the supporting explanation line.
- The two opening assets remain recognizable and are transitioned by geometry, masking, zoom, and gradient rather than a plain crossfade.
- Layout is authored in 1280×720 and uses an 80px horizontal / 54px vertical authoring-space safe margin.
- The film stays within research-only product boundaries and contains no performance promises, financial advice, or live-trading claims.
- Changes go into the user project directory; do not modify `/Users/mac/.agents/skills/ruic-motion-reel`.
- Do not publish or upload the rendered film without an explicit request.

## Review Focus

- Mixed aspect ratios in the 900×900 and 1536×1024 opening images must preserve the product text and bottom tagline; test the opening stills at both scene boundaries.
- Long bilingual headlines must fit the intended 62% / 42% width caps; test every exact title/subtitle pair through the fitting helper.
- Chinese font availability must be deterministic on this machine; test that `/System/Library/Fonts/PingFang.ttc` or the documented fallback is found before rendering.
- Every scene must cover exactly one bar and the complete frame sequence must contain 450 frames; test scene frame counts and `ffprobe` output.
- Gradient transitions and bright pulses must not wash out the light editorial palette; inspect representative frames and measure basic luminance ranges.

---

### Task 1: Scaffold the self-contained reel project and asset manifest

**Files:**
- Create: `motion-reel/` and its copied template/engine files via `new_reel.py`
- Create: `motion-reel/assets/finathink-research-splash.jpg`
- Create: `motion-reel/assets/finathink-splash-map.jpg`
- Create: `motion-reel/ASSET_MANIFEST.md`
- Test: `motion-reel/tests/test_assets.py`

**Interfaces:**
- Consumes: `/Users/mac/.agents/skills/ruic-motion-reel/scripts/new_reel.py`, `site/assets/finathink-research-splash.jpg`, `site/assets/finathink-splash-map.jpg`.
- Produces: a self-contained project package named `finathink_reel`, two known asset paths, and a manifest containing source dimensions and intended scene roles.

- [ ] **Step 1: Create the project from the installed template**

Run `python3 /Users/mac/.agents/skills/ruic-motion-reel/scripts/new_reel.py motion-reel --name finathink_reel --style none` from the repository root.

- [ ] **Step 2: Copy the two approved product images into the project assets directory**

Copy the source images without recompression and record their dimensions and roles in `motion-reel/ASSET_MANIFEST.md`.

- [ ] **Step 3: Write asset contract tests**

Create `test_opening_assets_exist_with_expected_dimensions()` asserting the two files exist and are `(900, 900)` and `(1536, 1024)` respectively.

- [ ] **Step 4: Run the asset tests**

Run `python3 -m pytest motion-reel/tests/test_assets.py -q`.
Expected: PASS with both assets present and dimensions unchanged.

- [ ] **Step 5: Commit the scaffold**

```bash
git add motion-reel
git commit -m "feat: scaffold Finathink motion reel project"
```

### Task 2: Configure bilingual identity, palette, timing, and typography

**Files:**
- Modify: `motion-reel/finathink_reel/theme.py`
- Create: `motion-reel/tests/test_theme_contract.py`
- Modify: `motion-reel/mg/fonts.py`

**Interfaces:**
- Consumes: Task 1 asset paths and the approved design spec.
- Produces: importable `theme.py` constants for identity, palette, bilingual scene copy, 128 BPM timing, 1280×720 authoring space, 1920×1080 delivery, and a verified CJK font path.

- [ ] **Step 1: Write theme contract tests**

Create tests asserting `FPS == 30`, `BPM == 128`, `BARS == 8`, `OUT_W, OUT_H == (1920, 1080)`, `W, H == (1280, 720)`, `NFRAMES == 450`, the selected CJK font path exists, and the eight scene entries each contain an English title and Chinese subtitle.

- [ ] **Step 2: Run the theme tests to establish the failing baseline**

Run `python3 -m pytest motion-reel/tests/test_theme_contract.py -q`.
Expected: FAIL against the untouched template identity/timing/copy.

- [ ] **Step 3: Add deterministic CJK font loading**

Add `cjk(size)` to the copied `mg/fonts.py`, loading `theme.CJK_FONT_PATH` or the documented macOS PingFang fallback through Pillow's TrueType collection support. Do not copy or redistribute the system font into the project.

- [ ] **Step 4: Replace the template identity and palette**

Set Finathink identity, the measured palette from the spec, the bilingual copy, scene names, safe margins, typography ratios, and source asset paths. Use `F.fit_size()` at render time; do not hard-code headline widths.

- [ ] **Step 5: Run the theme tests**

Run `python3 -m pytest motion-reel/tests/test_theme_contract.py -q`.
Expected: PASS with the exact timing and copy contract.

- [ ] **Step 6: Commit the theme configuration**

```bash
git add motion-reel/finathink_reel/theme.py motion-reel/mg/fonts.py motion-reel/tests/test_theme_contract.py
git commit -m "feat: configure bilingual Finathink reel theme"
```

### Task 3: Implement reusable bilingual layout and opening image-transition helpers

**Files:**
- Modify: `motion-reel/finathink_reel/scenes.py`
- Modify: `motion-reel/finathink_reel/chrome.py` only if the template chrome conflicts with the light editorial treatment
- Create: `motion-reel/tests/test_scene_contract.py`

**Interfaces:**
- Consumes: Task 2 theme constants and Task 1 asset paths.
- Produces: scene classes `OpenResearch`, `ArchitectureBridge`, `Evidence`, `KnowledgeMath`, `QuantResearch`, `StrategyBacktest`, `LearningAgent`, `Signoff`, plus helpers `draw_bilingual_title(...)`, `draw_card_image(...)`, and `draw_bridge_wipe(...)`.

- [ ] **Step 1: Write scene contract tests**

Create `test_scene_objects_match_eight_bars()` asserting the scene list has eight renderable objects, each has `render(canvas, tl, t)`, and each asset helper resolves to an existing file.

- [ ] **Step 2: Run the scene tests to establish the failing baseline**

Run `python3 -m pytest motion-reel/tests/test_scene_contract.py -q`.
Expected: FAIL because the copied template exposes different scene classes and references the placeholder mark.

- [ ] **Step 3: Implement the shared bilingual title helper**

Implement a helper that fits the English headline to 62% of `W`, places the Chinese subtitle below it within 42% of `W` using `F.cjk(...)`, and applies 1–2-frame staggered character reveals without overlapping the cap-height band.

- [ ] **Step 4: Implement the two opening scenes**

Render the 900×900 research workspace as a centered 640×640 authoring-space card with a controlled push-in. Transition from its center Logo into a radial node/wipe, then reveal the 1536×1024 architecture map using height-fit placement with warm-white side gradients so the bottom tagline remains visible.

- [ ] **Step 5: Implement the five product chapters**

Implement evidence, knowledge/math, quant research, strategy/OOS, and learning/agent scenes as code-drawn editorial cards, lines, nodes, equations, curves, and status chips. Keep all numeric values structural examples only.

- [ ] **Step 6: Implement the signoff scene**

Reverse the connector geometry into the Finathink lockup and render the final English/Chinese closing copy plus `EVENTS · KNOWLEDGE · QUANT · YOU`.

- [ ] **Step 7: Run scene contract tests**

Run `python3 -m pytest motion-reel/tests/test_scene_contract.py -q`.
Expected: PASS.

- [ ] **Step 8: Render one still sheet per scene and inspect proportions**

Run `python3 -m finathink_reel.build --stills 0` through `--stills 7` from `motion-reel/`. Inspect every sheet for headline width, Chinese legibility, safe margins, image crop, and transition continuity. Adjust only the relevant scene constants and rerender the affected sheet.

- [ ] **Step 9: Commit the scene implementation**

```bash
git add motion-reel/finathink_reel motion-reel/tests/test_scene_contract.py
git commit -m "feat: build Finathink bilingual motion scenes"
```

### Task 4: Calibrate audio, frame counts, and final encoding

**Files:**
- Modify: `motion-reel/finathink_reel/audio.py` only for the approved bilingual brand rhythm if the template mix needs adjustment
- Modify: `motion-reel/finathink_reel/build.py` only if the project-specific output name or encoder fallback needs a narrow fix
- Create: `motion-reel/VERIFY.md`
- Create: `motion-reel/tests/test_render_contract.py`

**Interfaces:**
- Consumes: all eight scene objects and the approved 128 BPM timing.
- Produces: `motion-reel/out/finathink_motion_reel.mp4`, source frame/audio intermediates, and a verification record.

- [ ] **Step 1: Render boundary frames before the full film**

Run `python3 -m finathink_reel.build --at 0:0.00`, `--at 0:1.80`, `--at 1:0.00`, `--at 1:1.80`, `--at 7:0.00`, and `--at 7:1.80`. Inspect opening image continuity, the first chapter transition, and the final lockup.

- [ ] **Step 2: Render the full film with bounded parallelism**

Run `python3 -m finathink_reel.build --jobs 2`; keep the process at two workers so the machine remains usable.

- [ ] **Step 3: Verify media geometry and timing**

Run:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,nb_frames,r_frame_rate \
  -show_entries format=duration \
  -of default=noprint_wrappers=1 motion-reel/out/finathink_motion_reel.mp4
```

Expected: width `1920`, height `1080`, `30/1` frame rate, `450` frames, and `15.000000` seconds.

- [ ] **Step 4: Verify decoded audio peak**

Run the skill's `loudnorm=print_format=summary` check and record integrated loudness and true peak in `motion-reel/VERIFY.md`; true peak must remain below 0 dBTP.

- [ ] **Step 5: Write and run render contract tests**

Create `test_output_metadata_is_15_seconds_1080p30()` using `ffprobe` output and `test_representative_frames_have_visible_dynamic_range()` using Pillow to assert the rendered output is not blank or uniformly washed out at the eight representative timestamps. Run `python3 -m pytest motion-reel/tests/test_render_contract.py -q` after the full render.

- [ ] **Step 6: Inspect representative rendered frames**

Extract or open frames at 0.5s, 2.5s, 4.5s, 6.5s, 8.5s, 10.5s, 12.5s, and 14.5s. Confirm bilingual text, visual hierarchy, gradients, and the five chapter identities.

- [ ] **Step 7: Commit the verified deliverable metadata**

```bash
git add motion-reel/VERIFY.md motion-reel/tests/test_render_contract.py motion-reel/finathink_reel/audio.py motion-reel/finathink_reel/build.py
git commit -m "feat: render and verify Finathink motion reel"
```

### Task 5: Final delivery handoff

**Files:**
- Modify: `motion-reel/README.md`

**Interfaces:**
- Consumes: verified MP4, source project, and `VERIFY.md`.
- Produces: a concise local handoff with the exact MP4 path, source path, render specification, and known limits.

- [ ] **Step 1: Document how to rerender and where the deliverables live**

Record the command `python3 -m finathink_reel.build --jobs 2`, the output path, and the bilingual scene list.

- [ ] **Step 2: Run the final repository hygiene checks**

Run `git diff --check`, the motion-reel tests, and `git status --short`. Confirm no generated intermediate frames or temporary files are accidentally staged unless intentionally retained.

- [ ] **Step 3: Commit the handoff documentation**

```bash
git add motion-reel/README.md
git commit -m "docs: add Finathink motion reel handoff"
```
