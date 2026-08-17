# Source assets

*This file belongs to MikuCodexPet, not to the upstream project — everything else in this directory is third-party material, unmodified.*

Copied verbatim from `assets/characters/miku/` of <https://github.com/CharlesWiiFlowers/MikuPet>, commit `2976ad7085c38baf671fa4667046833b3872fa08`. All eight files were re-verified byte-for-byte against that commit on 2026-08-17.

| File | Contents |
| --- | --- |
| `character.json` | animation → sprite sheet + metadata mapping, author credit |
| `idle.json` / `idle.png` | 20 frames, 64 × 100 cells (a 10-frame breathing cycle played twice; the second pass adds a blink at 12–13 and an open-mouth beat at 15–17) |
| `walk.json` / `walk_left.png` | 3 frames, 64 × 100 cells, left-facing |
| `walk.json` / `walk_right.png` | 3 frames, 64 × 100 cells, right-facing |
| `dragging.json` / `dragging.png` | 3 frames, 100 × 100 cells (unused — see README) |

Do not edit these files; `tools/build_codex_pet.py` reads them as-is.

## Licence notice

These files come from two different rights holders and are **not** under a single licence:

- **`*.json`** — part of the MikuPet project by Charles Flowers, distributed under GPL-3.0. Redistributed here unmodified under the same licence; the full text is in [../../LICENSE](../../LICENSE).
- **`*.png`** — character artwork by **BYP Studio and Chaim Videogames** for *Miku 'n Pop*, obtained via The Spriters Resource. MikuPet credits this artwork to those third parties, so its GPL-3.0 licence does not extend to it. No licence over the artwork is claimed here.

Full details, including the modification statement and removal contact, are in [../../ATTRIBUTION.md](../../ATTRIBUTION.md).
