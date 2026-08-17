# Attribution and rights

*[ATTRIBUTION in Russian](ATTRIBUTION.ru.md)*

This is an **unofficial, non-commercial fan project**. Different parts of it carry different rights, and they are deliberately kept separate: nothing here relicenses artwork that this project does not own.

## Who owns what

| Layer | Files | Rights holder | Terms |
| --- | --- | --- | --- |
| Build tooling and documentation | `tools/`, `*.md` | Vlad Kostyanetsky (maintainer) | GPL-3.0 — see [LICENSE](LICENSE) |
| MikuPet animation metadata | `src/miku/*.json` | Charles Flowers ([MikuPet](https://github.com/CharlesWiiFlowers/MikuPet)) | GPL-3.0, copied verbatim |
| Character sprites | `src/miku/*.png` | BYP Studio and Chaim Videogames (*Miku 'n Pop*) | **Not GPL-3.0.** No licence is claimed or granted here; [reuse with credit was publicly allowed by the artist](#permission-stated-by-the-artist) |
| Built atlases and pet package | `dist/**` | derived from the sprites above | Same terms as the sprites |
| The character herself | — | Crypton Future Media, INC. | Non-commercial use in the spirit of the piapro character guidelines |

The maintainer claims no ownership of any artwork in this repository, and asserts no rights beyond releasing his own contribution under GPL-3.0. That contribution — the build tooling and this documentation — was produced with AI assistance at his direction; to the extent it is copyrightable at all, it is GPL-3.0, and where it is not, no rights are asserted.

## GPL-3.0 notices

The MikuPet repository is distributed under GPL-3.0, so the files taken from it are redistributed under the same licence, with a full copy of that licence in [LICENSE](LICENSE).

**Provenance.** The eight files in `src/miku/` were copied byte-for-byte from `assets/characters/miku/` of `CharlesWiiFlowers/MikuPet` at commit [`2976ad7085c38baf671fa4667046833b3872fa08`](https://github.com/CharlesWiiFlowers/MikuPet/tree/2976ad7085c38baf671fa4667046833b3872fa08/assets/characters/miku). Their SHA-256 hashes were re-verified against that commit on 2026-08-17:

```text
character.json  idle.json  idle.png
walk.json       walk_left.png  walk_right.png
dragging.json   dragging.png
```

**Statement of modification** (GPL-3.0 §5a). No MikuPet *source code* is included or reproduced here — there is no port of the application. The `.json` metadata files are unmodified. The accompanying PNG artwork was mechanically transformed in August 2026 by `tools/build_codex_pet.py` into the Codex sprite atlas found in `dist/`.

**Scope.** GPL-3.0 covers the build tooling, the documentation and the MikuPet metadata files. It does **not** cover the character artwork: MikuPet itself credits that artwork to third parties, so the presence of a GPL-3.0 licence in that repository cannot be read as a GPL-3.0 grant over the sprites.

## Character artwork

```text
Character assets:
BYP Studio and Chaim Videogames
Miku 'n Pop
Source: The Spriters Resource / The VG Resource
https://www.spriters-resource.com/pc_computer/mikunpop/sheet/46493/
```

No formal licence covers these sprites, and none is claimed here. They are reused as non-commercial fan work, unmodified in design, with credit preserved everywhere the pet travels — including inside the installable package (`dist/miku/CREDITS.txt`), so that the attribution survives installation.

### Permission stated by the artist

On the official *Miku 'n Pop* page on itch.io, a user asked whether the game's sprites could be reused in a free project they intended to publish. Chaim Vester answered on 2026-02-19 that the sprites may be used — "You can use the Sprites if you like them" — noting that they are already available on The Spriters Resource, and asking that proper credit be given, because hardly anyone does ([permalink](https://chaim-videogames.itch.io/mikun-pop#post-15508543)).

This project follows that request: credit is given in the README, here, and inside the installable package itself. Two caveats are worth stating plainly rather than glossing over. It is an informal public statement, not a licence. And it comes from Chaim Vester alone, while the artwork is credited to BYP Studio *and* Chaim Videogames — so it does not speak for BYP Studio.

## The character

```text
Hatsune Miku (C) Crypton Future Media, INC. www.piapro.net
```

Crypton permits non-commercial derivative use of the character under its piapro character guidelines, but that permission covers the character, not any particular artist's drawing of her. It therefore does not substitute for the rights of BYP Studio and Chaim Videogames in these specific sprites.

## No affiliation, no commerce

This project is not affiliated with, endorsed by or sponsored by Crypton Future Media, BYP Studio, Chaim Videogames, the MikuPet author, or OpenAI. *Codex*, *ChatGPT* and *OpenAI* are trademarks of OpenAI; *Hatsune Miku* is a trademark of Crypton Future Media. They are used here only to describe what this project is compatible with.

Nothing here is sold, and nothing here may be sold: commercial redistribution of the artwork or of the built atlases would need permission from the artwork's rights holders (and from Crypton), which this project does not have and cannot pass on.

## Removal requests

If you hold rights in any of this material and would rather it were not published here, open an issue at <https://github.com/vkostyanetsky/MikuCodexPet/issues> or contact the maintainer directly. The material will be removed promptly, no argument.

## What was done to the artwork

Only mechanical operations — the character design was not altered and no art was generated or repainted:

- crop to frame rectangles read from the original JSON metadata
- crop to the bounding box shared by all frames of an animation
- integer 3× upscale using **nearest-neighbour** only
- transparent padding and repositioning inside 192 × 208 cells
- reordering, subsetting and duplication of frames

No mirroring was needed: MikuPet ships genuine `walk_left` and `walk_right` art.

The build verifies that every colour in the final atlas already exists in the source sprites, which proves no interpolated in-between colours were introduced.

## Format reference

The Codex sprite contract was read from the `hatch-pet` skill bundled with the local Codex installation (`~/.codex/skills/hatch-pet/`) and from <https://learn.chatgpt.com/docs/pets>. No files under `hatch-pet` were modified, and none are reproduced here.
