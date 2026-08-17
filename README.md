# Miku — a native Codex custom pet

[README in Russian](README.ru.md)

A Codex/ChatGPT desktop custom pet built from the original pixel-art Hatsune Miku sprites of [CharlesWiiFlowers/MikuPet](https://github.com/CharlesWiiFlowers/MikuPet).

> Unofficial, non-commercial fan project. Not affiliated with or endorsed by Crypton Future Media, BYP Studio, Chaim Videogames, the MikuPet author or OpenAI. The character artwork is not covered by this repository's licence — see [ATTRIBUTION.md](ATTRIBUTION.md).

This is not a port of the MikuPet application. There is no Python runtime, no Tkinter, no `MikuPet.exe`, no overlay and no window tracking. Codex owns the floating pet and its activity states; this repository only converts MikuPet's sprite assets into the atlas format Codex expects.

## Build

```bash
pip install Pillow
python tools/build_codex_pet.py
```

Pillow is a build-time tool only. It is not a requirement of the source project (whose runtime is not reproduced here — only its PNG/JSON assets are) and not a requirement of Codex, which consumes `dist/miku/` as plain data and never runs Python. Everything in `dist/` is already built, so installing the pet needs no dependencies at all — you only need Pillow if you want to rebuild the atlas from the sprites, which is also the only way to re-run the palette, alpha and geometry checks under [Validation](#validation).

## Output

| File | Purpose |
| --- | --- |
| `dist/miku/pet.json` + `dist/miku/spritesheet.webp` + `dist/miku/CREDITS.txt` | **The installable pet package** (desktop app) |
| `dist/miku_codex_pet.png` | v2 atlas, 1536 × 2288, transparent PNG |
| `dist/miku_codex_pet.webp` | v2 atlas, lossless WebP (same pixels) |
| `dist/miku_codex_pet_v1.png` | v1 atlas, 1536 × 1872, for the web upload flow |
| `dist/preview/*.gif` | Debug-only motion previews (Codex does not use these) |
| `dist/build-report.json` | Frame mapping, per-cell placement, validation record |

## Codex format

```text
spriteVersionNumber: 2
Sheet size:  1536 × 2288
Grid:        8 columns × 11 rows
Cell size:   192 × 208
Background:  transparent (true alpha, RGB of transparent pixels zeroed)
Format:      PNG or WebP, ≤ 20 MiB (this pet: ~27 KB)
```

> [!NOTE]
> The format was taken from the bundled `hatch-pet` skill shipped with Codex (`~/.codex/skills/hatch-pet/references/codex-pet-contract.md` and `references/animation-rows.md`).

Rows 0-8 are the standard animation states, rows 9-10 are the 16 clockwise look directions (`000` = up, `090` = screen-right, `180` = down, `270` = screen-left), and cell (row 0, column 6) holds the neutral/front look frame.

A v1 sheet (`1536 × 1872`, rows 0-8 only) is also produced because the **web** upload flow documented at <https://learn.chatgpt.com/docs/pets> still asks for exactly 1536 × 1872. `spriteVersionNumber: 2` is mandatory for the 2288-tall sheet; without it the app falls back to the v1 contract and rejects the asset.

## Install

**Desktop app (recommended, v2):**

```bash
mkdir -p ~/.codex/pets/miku && cp dist/miku/pet.json dist/miku/spritesheet.webp dist/miku/CREDITS.txt ~/.codex/pets/miku/
```

On Windows PowerShell:

```bash
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\pets\miku"; Copy-Item dist\miku\* "$env:USERPROFILE\.codex\pets\miku\" -Force
```

Then in Codex: refresh the pet list, pick **Miku**, and use `/pet` to summon the floating pet.

**Web (v1):** Settings → Personalization → Pet → Upload pet, and upload `dist/miku_codex_pet_v1.png`.

## Animation mapping

Every cell comes from a real MikuPet frame — cropped, integer-scaled with nearest-neighbour, padded and rearranged. Nothing was repainted or generated.

| Row | Codex state | Source | Notes |
| --- | --- | --- | --- |
| 0 | `idle` | `idle` 0, 12, 13, 4, 6, 8 | Breathing cycle with the original blink. Column 0 is the reduced-motion still. |
| 1 | `running-right` | `walk_right` 0-1-2-1-0-1-2-1 | Real right-facing art; nothing mirrored. |
| 2 | `running-left` | `walk_left` 0-1-2-1-0-1-2-1 | Real left-facing art; nothing mirrored. |
| 3 | `waving` | `idle` 15, 16, 17, 16 | The open-mouth "singing" beat of the idle loop. |
| 4 | `jumping` | `walk_right` 0-1-2-1-0 | Mid-stride poses lifted 5–8 px off the baseline. |
| 5 | `failed` | `idle` 13, 12 | Eyes squeeze shut and Miku sinks a few pixels. |
| 6 | `waiting` | `idle` 15, 16, 17, 16, 15, 10 | Mouth wide open with a small bob — "asking". |
| 7 | `running` | `walk_right` 0-1-2-0-1-2 | Tight walk cycle. |
| 8 | `review` | `idle` 0, `walk_left` 1, `idle` 11, `walk_right` 1 | Miku looks the work over, left then right. |
| 9–10 | look directions | `walk_right` / `walk_left` / `idle` | Right-component directions face right, left-component face left, `000`/`180` fall back to front-facing idle frames. |

How that lines up with the Codex activity states:

- **Running** → `running` (row 7) — Miku walks.
- **Needs input** → `waiting` (row 6) — mouth open, calling for you.
- **Ready** → `review` (row 8) / `idle` (row 0) — calm, looking around.
- **Blocked** → `failed` (row 5) — eyes shut, slumped.
- **Reduced motion** → row 0 column 0, a neutral front-facing idle frame.

## Geometry

- Uniform 3× nearest-neighbour integer scale for every state (64 × 100 source cells; Miku ends up 189–192 px tall, matching the ~198 px of the built-in Codex pets). 4× would overflow the 192 px cell.
- Every frame of an animation is cropped to the animation's *shared* bounding box, so the registration the original artist authored is preserved and no state jitters horizontally.
- All states sit on a single baseline (`y = 202`); the only deviations are the deliberate jump lift and the `failed` slump.

## Validation

`tools/build_codex_pet.py` fails the build unless:

- both atlases are exactly 1536 × 2288 / 1536 × 1872, RGBA;
- every used cell is non-empty and every unused cell is fully transparent;
- no transparent pixel carries non-zero RGB;
- every colour in the atlas already exists in the source sprites — an exact palette match, which is what proves no bilinear/bicubic interpolation happened;
- no output file exceeds the 20 MiB Codex limit.

The output was additionally checked with Codex's own validator:

```bash
python ~/.codex/skills/hatch-pet/scripts/validate_atlas.py dist/miku/spritesheet.webp --require-v2
```

## Known limitations

- MikuPet's `dragging` animation is not used. Its flailing pose is 84 px wide in the source, which becomes 252 px at the uniform 3× scale and cannot fit a 192 px cell without cropping her hair or breaking the single-scale rule.
- The source set has no upward or downward facing art, so look directions `000` (up) and `180` (down) both fall back to front-facing idle frames, distinguished only by eye state. The left/right cardinals are unmistakable.
- `waving` and `waiting` both draw on the open-mouth idle frames; they differ in timing and bob, not in pose.

## Licence and credits

| What | Terms |
| --- | --- |
| Build tooling (`tools/`) and documentation | GPL-3.0 — [LICENSE](LICENSE) |
| MikuPet animation metadata (`src/miku/*.json`) | GPL-3.0, copied verbatim from [MikuPet](https://github.com/CharlesWiiFlowers/MikuPet) |
| Character sprites (`src/miku/*.png`) and everything derived from them in `dist/` | **Not GPL-3.0** — rights remain with the artwork's authors |

```text
Character assets:
BYP Studio and Chaim Videogames — Miku 'n Pop
Source: The Spriters Resource / The VG Resource

Sprite source project:
CharlesWiiFlowers/MikuPet (GPL-3.0)

Hatsune Miku (C) Crypton Future Media, INC. www.piapro.net
```

Reuse of these sprites with credit was [publicly allowed by Chaim Vester on itch.io](https://chaim-videogames.itch.io/mikun-pop#post-15508543) (2026-02-19) — an informal statement rather than a licence, and one that speaks only for that artist, not for BYP Studio.

This is non-commercial fan work, given away free; the artwork is reused as-is with credit, not relicensed. Commercial use would need permission from the artwork's rights holders and from Crypton — permission this project neither has nor can pass on. Rights holders who want the material taken down can [open an issue](https://github.com/vkostyanetsky/MikuCodexPet/issues); it will be removed promptly.

The full picture — provenance hashes, GPL notices, statement of modification — is in [ATTRIBUTION.md](ATTRIBUTION.md).
