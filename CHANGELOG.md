# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.0.0 - 2026-08-17

### Added

* Miku as a native Codex custom pet, built from the original pixel-art sprites of [CharlesWiiFlowers/MikuPet](https://github.com/CharlesWiiFlowers/MikuPet). Every cell comes from a real MikuPet frame — cropped, integer-scaled with nearest-neighbour, padded and rearranged; nothing was repainted or generated.
* The installable package `dist/miku/`: `pet.json`, `spritesheet.webp` and `CREDITS.txt`. Copy the folder into `~/.codex/pets/`, refresh the pet list and call `/pet`.
* A v2 atlas, 1536 × 2288, 8 columns × 11 rows of 192 × 208 cells. Rows 0-8 carry the animation states (`idle`, `running-right`, `running-left`, `waving`, `jumping`, `failed`, `waiting`, `running`, `review`), rows 9-10 the 16 clockwise look directions.
* A v1 atlas, `dist/miku_codex_pet_v1.png`, 1536 × 1872, for the web upload flow at <https://learn.chatgpt.com/docs/pets>, which still asks for the shorter sheet.
* **`tools/build_codex_pet.py`** — the build script that reads the LibreSprite/Aseprite metadata and PNG strips from `src/miku/` and composes the atlases. It takes `--source-dir`, `--dist-dir` and `--skip-previews`.
* Build-time validation that fails the build unless the atlas geometry is exact, every used cell is non-empty and every unused one fully transparent, no transparent pixel carries non-zero RGB, no output exceeds the 20 MiB Codex limit, and every colour already exists in the source sprites — the palette match is what proves no interpolation happened.
* Debug-only motion previews in `dist/preview/` and a full frame mapping in `dist/build-report.json`.
* **`.github/workflows/release.yml`** — a manually dispatched GitHub Actions workflow that builds the pet and opens a draft release with `miku-codex-pet.zip` attached, an archive rooted at a `miku/` folder so it unpacks straight into `~/.codex/pets/`. The version and the release notes are taken from this changelog, and the tag is created from the built commit when the draft is published.
* Documentation in English and Russian: [README.md](README.md), [README.ru.md](README.ru.md), [ATTRIBUTION.md](ATTRIBUTION.md) and [ATTRIBUTION.ru.md](ATTRIBUTION.ru.md), covering the animation mapping, the geometry rules, the known limitations and the provenance of the artwork.
