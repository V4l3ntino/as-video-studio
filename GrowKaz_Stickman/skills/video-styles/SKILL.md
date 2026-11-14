---
name: video-styles
description: >
  This skill should be used when the user runs /video-styles or asks to "show me style options", "compare the looks",
  "pick a visual style", "make it warmer / darker / more neon", "create a custom style", or "change the colour grade"
  for an GrowKaz Stickman Studio video. It renders the same shots of the user's story in five preset styles
  (emerald, ember, arctic, sakura, retro) as a comparison grid, records the choice, and builds custom styles.
metadata:
  version: "0.1.0"
  author: GrowKaz
---

# /video-styles: render style options and lock the look

Work inside `growkaz-stickman-studio/` on the active project (`projects/<slug>`; if several exist, ask which one). Shared references are in `../make-2d-video/references/` relative to this skill's base directory.

## 1. Make sure there is something representative to show
The grid uses the user's own shots, never the bundled example. If the project has fewer than 3 finished shots, first build (following `../make-2d-video/references/style-bible.md` and `engine-api.md`):
- `scenes/cast.js` and the 1–2 most-used sets,
- a wide set shot with ≥ 2 characters, a `bigFace` close-up, and a data/blueprint or 3D shot.

Pick one time inside each shot (about 45% through it) for the grid columns.

## 2. Render the grid
```bash
node render.mjs --project projects/<slug> --styles emerald,ember,arctic,sakura,retro --at <t1>,<t2>,<t3> --scale 0.5
```
Open `build/styles/style_grid.png` (one row per style) and check it, then send it to the user with one line each:
- **emerald — GrowKaz Emerald:** the GrowKaz signature look. Forest-green shadows, gold key light, electric lime rims. This is the default.
- **ember — Ember Forge:** charcoal and crimson, molten copper rims, heavy contrast; drama, danger, history, motivation.
- **arctic — Arctic Glass:** icy steel-teal, crisp white key, cyan rims, nearly no grain; science, tech, clean explainers.
- **sakura — Sakura Bloom:** plum shadows, rose-pink sky, peach key, soft haze; emotional, relationships, lifestyle.
- **retro — Retro Print:** faded teal and mustard, low saturation, heavy print grain; nostalgic stories, history, "back then".

Ask which they want (AskUserQuestion when available).

## 3. Save or customise
- Preset chosen → set `"style"` in `projects/<slug>/config.json`.
- Tweaks requested → add a new entry to `STYLES` in `engine/styles.js`. Copy the closest preset, give it a new id and a `name`/`desc`, then adjust:
  - `moods` overrides (per mood: `sky`, `key`, `rim`, `wall`, `floor`, `practical`),
  - `grade`: `lift` [r,g,b] tints the shadows (raise b for cooler shadows), `gain` [r,g,b] tints the highlights (raise r for warmer), `gamma` [r,g,b], `sat`, `contrast`, `vignette`, `grain`, `bloom` (3D),
  - `ui` colours (gold, accent, cream, blueprint) and `rimWidth`.

  Re-render with `--styles <newid>,<closest preset> --at …` so the user can compare, iterate until they're happy, then set it in config.json. `tools/verify_kit.py` will now report `engine/styles.js` as changed; that's expected.

Scenes only follow a style switch if they take colours from `mood()`/`S()`. If one shot ignores the style, find the hard-coded colours in it and replace them.
