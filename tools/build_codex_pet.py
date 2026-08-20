#!/usr/bin/env python3
"""Build a Codex custom pet (sprite format v2) from the original MikuPet sprites.

Reads the LibreSprite/Aseprite-style JSON metadata plus the PNG strips that ship
with `CharlesWiiFlowers/MikuPet` (`assets/characters/miku/`), extracts the frames,
scales them with nearest-neighbour integer scaling and composes them into the
8 x 11 / 192 x 208 atlas that the Codex desktop app expects.

Everything here is crop / integer-scale / pad / rearrange. No repainting, no
resampling filters other than NEAREST, no generated art.

Usage:
    python tools/build_codex_pet.py

Copyright (C) 2026 Vlad Kostyanetsky.
Licensed under the GNU General Public License v3.0 (see LICENSE), the same
licence as the upstream MikuPet project. The character artwork this script
reads and transforms is NOT covered by that licence -- see ATTRIBUTION.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required: pip install Pillow")

# --------------------------------------------------------------------------
# Codex v2 sprite contract
# (~/.codex/skills/hatch-pet/references/codex-pet-contract.md + animation-rows.md)
# --------------------------------------------------------------------------
COLUMNS = 8
STANDARD_ROWS = 9          # rows 0-8: animation states  -> the v1 atlas
EXTENDED_ROWS = 11         # rows 9-10 add the 16 look directions -> the v2 atlas
CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_WIDTH = COLUMNS * CELL_WIDTH                    # 1536
STANDARD_ATLAS_HEIGHT = STANDARD_ROWS * CELL_HEIGHT   # 1872 (v1)
EXTENDED_ATLAS_HEIGHT = EXTENDED_ROWS * CELL_HEIGHT   # 2288 (v2)
SPRITE_VERSION_NUMBER = 2
MAX_FILE_BYTES = 20 * 1024 * 1024                     # 20 MiB

# row index -> (state name, number of used columns)
ROW_LAYOUT = {
    0: ("idle", 6),
    1: ("running-right", 8),
    2: ("running-left", 8),
    3: ("waving", 4),
    4: ("jumping", 5),
    5: ("failed", 8),
    6: ("waiting", 6),
    7: ("running", 6),
    8: ("review", 6),
    9: ("look-000-to-157.5", 8),
    10: ("look-180-to-337.5", 8),
}
# In the v2 atlas cell (row 0, column 6) holds the neutral / front look frame.
NEUTRAL_LOOK_CELL = (0, 6)

ROW_DURATIONS = {
    "idle": [280, 110, 110, 140, 140, 320],
    "running-right": [120, 120, 120, 120, 120, 120, 120, 220],
    "running-left": [120, 120, 120, 120, 120, 120, 120, 220],
    "waving": [140, 140, 140, 280],
    "jumping": [140, 140, 140, 140, 280],
    "failed": [140, 140, 140, 140, 140, 140, 140, 240],
    "waiting": [150, 150, 150, 150, 150, 260],
    "running": [120, 120, 120, 120, 120, 220],
    "review": [150, 150, 150, 150, 150, 280],
}

LOOK_DIRECTION_LABELS = [
    "000", "022.5", "045", "067.5", "090", "112.5", "135", "157.5",
    "180", "202.5", "225", "247.5", "270", "292.5", "315", "337.5",
]

# --------------------------------------------------------------------------
# Composition constants
# --------------------------------------------------------------------------
# Integer (nearest-neighbour) upscale applied to every frame. 3x puts Miku at
# ~189-192 px tall inside the 208 px cell, which matches the built-in Codex pets
# (measured: 198 px tall). 4x would overflow the cell.
SCALE = 3
BASELINE_Y = 202       # y of the bottom-most sprite pixel row inside a cell
ANCHOR_X = CELL_WIDTH // 2   # feet are centred here
FOOT_BAND = 0.28       # bottom fraction of the sprite used to find the foot centre
EDGE_MARGIN = 3        # keep sprites off the cell border when there is room

PET_ID = "miku"
PET_DISPLAY_NAME = "Miku"
PET_DESCRIPTION = "A pixel-art Hatsune Miku who idles, walks and sings along while Codex works."

# Shipped inside the installable package so the credits travel with the pet
# itself, not just with this repository. Kept free of build timestamps so the
# build stays byte-for-byte deterministic.
PET_CREDITS = """\
Miku -- an unofficial, fan-made custom pet for Codex
https://github.com/vkostyanetsky/MikuCodexPet

Character artwork
  BYP Studio and Chaim Videogames, created for "Miku'n POP".
  Obtained through The Spriters Resource / The VG Resource.
  The artwork is NOT covered by this project's GPL-3.0 licence; all rights
  remain with its authors. Chaim Vester has publicly allowed reuse of these
  sprites provided credit is given (itch.io, 2026-02-19):
  https://chaim-videogames.itch.io/mikun-pop#post-15508543

Sprite source project
  CharlesWiiFlowers/MikuPet (GPL-3.0)
  https://github.com/CharlesWiiFlowers/MikuPet
  The frames in this pet were cropped, integer-scaled with nearest-neighbour,
  padded and rearranged from that project's assets in August 2026. Nothing was
  repainted or generated.

Character
  Hatsune Miku (C) Crypton Future Media, INC. www.piapro.net
  Used non-commercially in the spirit of Crypton's piapro character guidelines.

Not affiliated with, endorsed by or sponsored by Crypton Future Media,
BYP Studio, Chaim Videogames, the MikuPet author or OpenAI. Non-commercial
fan work, distributed free of charge. Rights holders may request removal
via https://github.com/vkostyanetsky/MikuCodexPet/issues.
"""

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "src" / "miku"
DIST_DIR = REPO_ROOT / "dist"


# --------------------------------------------------------------------------
# Source frame loading
# --------------------------------------------------------------------------
@dataclass
class Animation:
    """One MikuPet animation, cropped to the bounding box shared by all its frames.

    Cropping every frame to the *same* box keeps the registration the original
    artist authored inside the source cell, so a state never jitters horizontally
    from frame to frame.
    """

    name: str
    image_name: str
    frames: list[Image.Image]
    union_box: tuple[int, int, int, int]

    def __len__(self) -> int:
        return len(self.frames)


def load_animation(
    source_dir: Path, name: str, metadata_name: str, image_name: str
) -> Animation:
    """Extract every frame of one MikuPet animation using its JSON metadata.

    Frame rectangles come from the metadata, never from hardcoded cell sizes.
    """
    meta = json.loads((source_dir / metadata_name).read_text(encoding="utf-8"))
    with Image.open(source_dir / image_name) as opened:
        strip = opened.convert("RGBA")

    declared = meta.get("meta", {}).get("size")
    if declared and (strip.width, strip.height) != (declared["w"], declared["h"]):
        raise SystemExit(
            f"{image_name} is {strip.width}x{strip.height} but {metadata_name} declares "
            f"{declared['w']}x{declared['h']}"
        )

    cells: list[Image.Image] = []
    for index, entry in enumerate(meta["frames"].values()):
        rect = entry["frame"]
        cell = strip.crop((rect["x"], rect["y"], rect["x"] + rect["w"], rect["y"] + rect["h"]))
        if cell.getbbox() is None:
            raise SystemExit(f"{image_name} frame {index} is empty")
        cells.append(cell)

    boxes = [cell.getbbox() for cell in cells]
    union = (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )
    return Animation(
        name=name,
        image_name=image_name,
        frames=[cell.crop(union) for cell in cells],
        union_box=union,
    )


def load_sources(source_dir: Path) -> dict[str, Animation]:
    character = json.loads((source_dir / "character.json").read_text(encoding="utf-8"))
    sources: dict[str, Animation] = {}
    for name, spec in character["animations"].items():
        sources[name] = load_animation(source_dir, name, spec["metadata"], spec["file"])
    return sources


# --------------------------------------------------------------------------
# Cell composition
# --------------------------------------------------------------------------
def foot_center_x(image: Image.Image) -> float:
    """Horizontal centre of the lowest band of opaque pixels (i.e. the feet)."""
    width, height = image.size
    data = image.convert("RGBA").tobytes()
    first_row = height - max(1, round(height * FOOT_BAND))
    total = 0
    count = 0
    for y in range(first_row, height):
        base = y * width * 4
        for x in range(width):
            if data[base + x * 4 + 3] > 16:
                total += x
                count += 1
    if not count:
        return width / 2
    return total / count


@dataclass
class Registration:
    """Where an animation's (identically cropped) frames sit inside a cell."""

    left: int
    width: int
    height: int
    clamped: bool


def register(animation: Animation) -> Registration:
    """Compute one horizontal placement shared by every frame of an animation.

    A single offset per animation is what removes frame-to-frame jitter: the
    frames keep the relative registration the artist gave them and the animation
    as a whole is aligned so Miku's feet sit on the cell's centre line.
    """
    width = (animation.union_box[2] - animation.union_box[0]) * SCALE
    height = (animation.union_box[3] - animation.union_box[1]) * SCALE
    if width > CELL_WIDTH or height > CELL_HEIGHT:
        raise SystemExit(
            f"{animation.image_name} is {width}x{height} at {SCALE}x and does not fit the "
            f"{CELL_WIDTH}x{CELL_HEIGHT} cell"
        )

    # Flatten the whole animation to find a foot centre that suits every frame.
    flat = Image.new("RGBA", animation.frames[0].size, (0, 0, 0, 0))
    for frame in animation.frames:
        flat.alpha_composite(frame)
    scaled_flat = flat.resize((width, height), Image.Resampling.NEAREST)

    desired = round(ANCHOR_X - foot_center_x(scaled_flat))
    slack = CELL_WIDTH - width
    if slack >= 2 * EDGE_MARGIN:
        low, high = EDGE_MARGIN, slack - EDGE_MARGIN
    else:
        low = high = slack // 2
    left = max(low, min(desired, high))
    return Registration(left=left, width=width, height=height, clamped=left != desired)


@dataclass
class Placement:
    row: int
    column: int
    state: str
    source: str
    source_frame: int
    left: int
    top: int
    width: int
    height: int
    clamped: bool


def compose_cell(
    animation: Animation, index: int, registration: Registration, dy: int
) -> tuple[Image.Image, dict]:
    """Scale one source frame and place it inside a transparent 192x208 cell."""
    frame = animation.frames[index]
    scaled = frame.resize((registration.width, registration.height), Image.Resampling.NEAREST)

    top = BASELINE_Y + dy - registration.height
    if top < 0 or top + registration.height > CELL_HEIGHT:
        raise SystemExit(
            f"{animation.image_name} frame {index} with dy={dy} does not fit vertically"
        )

    cell = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    cell.alpha_composite(scaled, (registration.left, top))
    info = {
        "left": registration.left,
        "top": top,
        "width": registration.width,
        "height": registration.height,
        "clamped": registration.clamped,
    }
    return cell, info


# --------------------------------------------------------------------------
# State mapping
# --------------------------------------------------------------------------
# (source animation, frame index, vertical offset in atlas pixels; negative = up)
#
# The MikuPet set contains: 20 idle frames (a 10-frame breathing cycle played
# twice, the second pass adding a blink at 12-13 and an open-mouth "singing"
# beat at 15-17), 3 walk_left frames, 3 walk_right frames and 3 dragging frames.
FrameSpec = tuple[str, int, int]

ROW_FRAMES: dict[str, list[FrameSpec]] = {
    # Calm breathing cycle (body poses 0-2-3-4-6-8) with the natural blink on the
    # two short cells. Frame 0 is also the reduced-motion still.
    "idle": [
        ("idle", 0, 0),
        ("idle", 12, 0),
        ("idle", 13, 0),
        ("idle", 4, 0),
        ("idle", 6, 0),
        ("idle", 8, 0),
    ],
    # Real directional art exists, so nothing is mirrored. 3 frames -> 8 cells
    # via a 0-1-2-1 ping-pong, which is the natural expansion of a 3-frame walk.
    "running-right": [("walk_right", i, 0) for i in (0, 1, 2, 1, 0, 1, 2, 1)],
    "running-left": [("walk_left", i, 0) for i in (0, 1, 2, 1, 0, 1, 2, 1)],
    # Greeting: the open-mouth "singing" beat of the idle animation.
    "waving": [
        ("idle", 15, 0),
        ("idle", 16, 0),
        ("idle", 17, 0),
        ("idle", 16, 0),
    ],
    # Hop: mid-stride poses lifted off the baseline and set back down.
    "jumping": [
        ("walk_right", 0, 0),
        ("walk_right", 1, -5),
        ("walk_right", 2, -8),
        ("walk_right", 1, -5),
        ("walk_right", 0, 0),
    ],
    # Stalled: eyes squeeze shut and Miku sinks, then straightens up again.
    "failed": [
        ("idle", 13, 0),
        ("idle", 13, 1),
        ("idle", 12, 2),
        ("idle", 12, 3),
        ("idle", 12, 3),
        ("idle", 12, 2),
        ("idle", 13, 1),
        ("idle", 13, 0),
    ],
    # Asking for input: mouth wide open, with a small bob so it reads at pet size.
    "waiting": [
        ("idle", 15, 0),
        ("idle", 16, -2),
        ("idle", 17, -3),
        ("idle", 16, -2),
        ("idle", 15, 0),
        ("idle", 10, 0),
    ],
    # Working: a tight walk cycle.
    "running": [("walk_right", i, 0) for i in (0, 1, 2, 0, 1, 2)],
    # Reviewing: Miku looks the work over, left then right.
    "review": [
        ("idle", 0, 0),
        ("walk_left", 1, 0),
        ("walk_left", 1, 0),
        ("idle", 11, 0),
        ("walk_right", 1, 0),
        ("walk_right", 1, 0),
    ],
}

# 16 clockwise look directions; 000 = up, 090 = screen-right, 180 = down,
# 270 = screen-left. MikuPet only ships front / left / right facings, so every
# direction with a rightward component uses the right-facing pose, every
# direction with a leftward component uses the left-facing pose, and the two
# vertical cardinals fall back to front-facing idle frames.
LOOK_FRAMES: dict[str, FrameSpec] = {
    "000": ("idle", 0, 0),        # up: front, eyes wide open
    "022.5": ("walk_right", 1, 0),
    "045": ("walk_right", 1, 0),
    "067.5": ("walk_right", 1, 0),
    "090": ("walk_right", 1, 0),
    "112.5": ("walk_right", 1, 0),
    "135": ("walk_right", 1, 0),
    "157.5": ("walk_right", 1, 0),
    "180": ("idle", 13, 0),       # down: front, eyes lowered
    "202.5": ("walk_left", 1, 0),
    "225": ("walk_left", 1, 0),
    "247.5": ("walk_left", 1, 0),
    "270": ("walk_left", 1, 0),
    "292.5": ("walk_left", 1, 0),
    "315": ("walk_left", 1, 0),
    "337.5": ("walk_left", 1, 0),
}

NEUTRAL_FRAME: FrameSpec = ("idle", 0, 0)
REDUCED_MOTION_FRAME: FrameSpec = ("idle", 0, 0)  # idle column 0


# --------------------------------------------------------------------------
# Atlas assembly
# --------------------------------------------------------------------------
@dataclass
class BuildResult:
    extended: Image.Image
    standard: Image.Image
    placements: list[Placement] = field(default_factory=list)
    cells: dict[tuple[int, int], Image.Image] = field(default_factory=dict)


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    """Zero the RGB of fully transparent pixels (Codex validation rejects residue)."""
    data = bytearray(image.convert("RGBA").tobytes())
    for index in range(0, len(data), 4):
        if data[index + 3] == 0:
            data[index] = data[index + 1] = data[index + 2] = 0
    return Image.frombytes("RGBA", image.size, bytes(data))


def build_atlas(sources: dict[str, Animation]) -> BuildResult:
    extended = Image.new("RGBA", (ATLAS_WIDTH, EXTENDED_ATLAS_HEIGHT), (0, 0, 0, 0))
    standard = Image.new("RGBA", (ATLAS_WIDTH, STANDARD_ATLAS_HEIGHT), (0, 0, 0, 0))
    placements: list[Placement] = []
    cells: dict[tuple[int, int], Image.Image] = {}

    # One registration per source animation, reused by every cell that draws it.
    registrations: dict[str, Registration] = {}

    def place(row: int, column: int, state: str, spec: FrameSpec, standard_too: bool) -> None:
        name, index, dy = spec
        animation = sources.get(name)
        if animation is None:
            raise SystemExit(f"unknown source animation {name!r}")
        if index >= len(animation):
            raise SystemExit(f"{name} has {len(animation)} frames; frame {index} requested")
        if name not in registrations:
            registrations[name] = register(animation)
        cell, info = compose_cell(animation, index, registrations[name], dy)
        extended.alpha_composite(cell, (column * CELL_WIDTH, row * CELL_HEIGHT))
        if standard_too:
            standard.alpha_composite(cell, (column * CELL_WIDTH, row * CELL_HEIGHT))
        cells[(row, column)] = cell
        placements.append(
            Placement(
                row=row,
                column=column,
                state=state,
                source=spec[0],
                source_frame=spec[1],
                **info,
            )
        )

    for row in range(STANDARD_ROWS):
        state, used = ROW_LAYOUT[row]
        specs = ROW_FRAMES[state]
        if len(specs) != used:
            raise SystemExit(f"{state} needs {used} frames, mapping supplies {len(specs)}")
        for column, spec in enumerate(specs):
            place(row, column, state, spec, standard_too=True)

    for index, label in enumerate(LOOK_DIRECTION_LABELS):
        row = STANDARD_ROWS + index // COLUMNS
        column = index % COLUMNS
        place(row, column, f"look-{label}", LOOK_FRAMES[label], standard_too=False)

    # The v2 neutral/front look frame. Deliberately absent from the v1 atlas,
    # where (0, 6) counts as an unused cell and must stay transparent.
    place(*NEUTRAL_LOOK_CELL, "neutral-look", NEUTRAL_FRAME, standard_too=False)

    return BuildResult(
        extended=clear_transparent_rgb(extended),
        standard=clear_transparent_rgb(standard),
        placements=placements,
        cells=cells,
    )


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def alpha_nonzero(image: Image.Image) -> int:
    return sum(image.getchannel("A").histogram()[1:])


def validate(atlas: Image.Image, extended: bool) -> list[str]:
    errors: list[str] = []
    expected_height = EXTENDED_ATLAS_HEIGHT if extended else STANDARD_ATLAS_HEIGHT
    if (atlas.width, atlas.height) != (ATLAS_WIDTH, expected_height):
        errors.append(f"expected {ATLAS_WIDTH}x{expected_height}, got {atlas.width}x{atlas.height}")
    if atlas.mode != "RGBA":
        errors.append(f"expected RGBA, got {atlas.mode}")

    rows = atlas.height // CELL_HEIGHT
    for row in range(rows):
        state, used = ROW_LAYOUT[row]
        for column in range(COLUMNS):
            cell = atlas.crop(
                (
                    column * CELL_WIDTH,
                    row * CELL_HEIGHT,
                    (column + 1) * CELL_WIDTH,
                    (row + 1) * CELL_HEIGHT,
                )
            )
            pixels = alpha_nonzero(cell)
            is_used = column < used or (extended and (row, column) == NEUTRAL_LOOK_CELL)
            if is_used and pixels < 50:
                errors.append(f"{state} r{row}c{column} is empty or too sparse ({pixels}px)")
            if not is_used and pixels:
                errors.append(f"{state} r{row}c{column} is unused but has {pixels}px")

    data = atlas.tobytes()
    residue = sum(
        1
        for i in range(0, len(data), 4)
        if data[i + 3] == 0 and (data[i] or data[i + 1] or data[i + 2])
    )
    if residue:
        errors.append(f"{residue} transparent pixels carry non-zero RGB")
    return errors


def colors(image: Image.Image) -> set[tuple[int, int, int, int]]:
    data = image.convert("RGBA").tobytes()
    return {tuple(data[i : i + 4]) for i in range(0, len(data), 4)}


def check_no_interpolation(sources: dict[str, Animation], atlas: Image.Image) -> list[str]:
    """Every colour in the atlas must already exist in the source sprites.

    Any bilinear/bicubic resampling would invent in-between colours, so an exact
    palette match proves the nearest-neighbour path was taken.
    """
    source_colors: set[tuple[int, int, int, int]] = {(0, 0, 0, 0)}
    for animation in sources.values():
        for frame in animation.frames:
            source_colors |= colors(frame)

    extra = colors(atlas) - source_colors
    if extra:
        return [f"{len(extra)} colours in the atlas are absent from the source sprites"]
    return []


# --------------------------------------------------------------------------
# Preview artefacts
# --------------------------------------------------------------------------
PREVIEW_BACKGROUND = (43, 43, 51, 255)
PREVIEW_ALIASES = {
    "running": "running",
    "waiting": "needs_input",
    "review": "ready",
    "failed": "blocked",
    "idle": "idle",
}


def write_previews(result: BuildResult, preview_dir: Path) -> list[dict]:
    preview_dir.mkdir(parents=True, exist_ok=True)
    written: list[dict] = []
    for row in range(STANDARD_ROWS):
        state, used = ROW_LAYOUT[row]
        frames = []
        for column in range(used):
            flat = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), PREVIEW_BACKGROUND)
            flat.alpha_composite(result.cells[(row, column)])
            frames.append(flat.convert("P", palette=Image.Palette.ADAPTIVE))
        names = [f"{state}.gif"]
        alias = PREVIEW_ALIASES.get(state)
        if alias and alias != state:
            names.append(f"{alias}.gif")
        for name in names:
            path = preview_dir / name
            frames[0].save(
                path,
                save_all=True,
                append_images=frames[1:],
                duration=ROW_DURATIONS[state],
                loop=0,
                disposal=2,
                optimize=False,
            )
            written.append({"state": state, "path": path.name, "frames": len(frames)})

    # Contact sheet: every used cell of the final atlas, on a flat background.
    sheet = Image.new("RGBA", (ATLAS_WIDTH, EXTENDED_ATLAS_HEIGHT), PREVIEW_BACKGROUND)
    sheet.alpha_composite(result.extended)
    sheet.convert("RGB").save(preview_dir / "contact-sheet.png")
    written.append({"state": "contact-sheet", "path": "contact-sheet.png", "frames": 0})

    # Look-direction loop.
    look_frames = []
    for index in range(len(LOOK_DIRECTION_LABELS)):
        row = STANDARD_ROWS + index // COLUMNS
        column = index % COLUMNS
        flat = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), PREVIEW_BACKGROUND)
        flat.alpha_composite(result.cells[(row, column)])
        look_frames.append(flat.convert("P", palette=Image.Palette.ADAPTIVE))
    look_frames[0].save(
        preview_dir / "look_directions.gif",
        save_all=True,
        append_images=look_frames[1:],
        duration=200,
        loop=0,
        disposal=2,
        optimize=False,
    )
    written.append({"state": "look", "path": "look_directions.gif", "frames": len(look_frames)})
    return written


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def save_webp(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="WEBP", lossless=True, quality=100, method=6, exact=True)


def write_pet_package(image: Image.Image, package_dir: Path) -> Path:
    package_dir.mkdir(parents=True, exist_ok=True)
    spritesheet = package_dir / "spritesheet.webp"
    save_webp(image, spritesheet)
    manifest = {
        "id": PET_ID,
        "displayName": PET_DISPLAY_NAME,
        "description": PET_DESCRIPTION,
        "spriteVersionNumber": SPRITE_VERSION_NUMBER,
        "spritesheetPath": "spritesheet.webp",
    }
    (package_dir / "pet.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (package_dir / "CREDITS.txt").write_text(PET_CREDITS, encoding="utf-8")
    return spritesheet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--dist-dir", default=str(DIST_DIR))
    parser.add_argument("--skip-previews", action="store_true")
    args = parser.parse_args()

    source_dir = Path(args.source_dir).expanduser().resolve()
    dist_dir = Path(args.dist_dir).expanduser().resolve()

    sources = load_sources(source_dir)
    print("source animations: " + ", ".join(f"{k}={len(v)}f" for k, v in sources.items()))

    result = build_atlas(sources)

    errors = validate(result.extended, extended=True)
    errors += validate(result.standard, extended=False)
    errors += check_no_interpolation(sources, result.extended)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

    v2_png = dist_dir / "miku_codex_pet.png"
    v2_webp = dist_dir / "miku_codex_pet.webp"
    v1_png = dist_dir / "miku_codex_pet_v1.png"
    save_png(result.extended, v2_png)
    save_webp(result.extended, v2_webp)
    save_png(result.standard, v1_png)
    package_sheet = write_pet_package(result.extended, dist_dir / PET_ID)

    for path in (v2_png, v2_webp, v1_png, package_sheet):
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise SystemExit(f"{path.name} is {size} bytes, over the {MAX_FILE_BYTES} byte limit")
        print(f"wrote {path} ({size:,} bytes)")

    previews: list[dict] = []
    if not args.skip_previews:
        previews = write_previews(result, dist_dir / "preview")
        print(f"wrote {len(previews)} preview artefacts to {dist_dir / 'preview'}")

    report = {
        "ok": True,
        "spriteVersionNumber": SPRITE_VERSION_NUMBER,
        "scale": SCALE,
        "resample": "NEAREST",
        "baselineY": BASELINE_Y,
        "anchorX": ANCHOR_X,
        "atlas": {
            "v2": {
                "path": str(v2_png),
                "width": result.extended.width,
                "height": result.extended.height,
                "columns": COLUMNS,
                "rows": EXTENDED_ROWS,
                "cellWidth": CELL_WIDTH,
                "cellHeight": CELL_HEIGHT,
                "bytes": v2_png.stat().st_size,
            },
            "v1": {
                "path": str(v1_png),
                "width": result.standard.width,
                "height": result.standard.height,
                "rows": STANDARD_ROWS,
                "bytes": v1_png.stat().st_size,
            },
        },
        "package": str(dist_dir / PET_ID),
        "reducedMotionFrame": {
            "row": 0,
            "column": 0,
            "source": f"{REDUCED_MOTION_FRAME[0]} frame {REDUCED_MOTION_FRAME[1]}",
        },
        "rows": [
            {
                "row": row,
                "state": ROW_LAYOUT[row][0],
                "frames": [
                    {"source": spec[0], "frame": spec[1], "dy": spec[2]}
                    for spec in ROW_FRAMES[ROW_LAYOUT[row][0]]
                ],
                "durationsMs": ROW_DURATIONS[ROW_LAYOUT[row][0]],
            }
            for row in range(STANDARD_ROWS)
        ],
        "lookDirections": [
            {
                "degrees": float(label),
                "row": STANDARD_ROWS + index // COLUMNS,
                "column": index % COLUMNS,
                "source": LOOK_FRAMES[label][0],
                "frame": LOOK_FRAMES[label][1],
            }
            for index, label in enumerate(LOOK_DIRECTION_LABELS)
        ],
        "placements": [vars(placement) for placement in result.placements],
        "previews": previews,
    }
    report_path = dist_dir / "build-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {report_path}")
    print("validation: OK")


if __name__ == "__main__":
    main()
