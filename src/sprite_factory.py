#!/usr/bin/env python3
"""Generate a fighter spritesheet, portrait, and JSON configuration."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps

try:
    from rembg import new_session, remove
except ImportError as exc:  # Dependency errors are reported by main().
    new_session = None
    remove = None
    REMBG_IMPORT_ERROR = exc
else:
    REMBG_IMPORT_ERROR = None


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TARGET_HEIGHT = 250
SPRITESHEET_PADDING = 2
ORDER_PREFIX = re.compile(r"^\d+[_-]+")
FRAME_SUFFIX = re.compile(r"[_-]\d{1,3}$")


@dataclass(frozen=True)
class PoseFrame:
    source: Path
    name: str
    action: str
    image: Image.Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove backgrounds, normalize poses, and create game assets."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("assets/raw_photos"),
        help="Source photograph directory (default: assets/raw_photos)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("assets/output"),
        help="Generated asset directory (default: assets/output)",
    )
    parser.add_argument(
        "--template",
        "-t",
        type=Path,
        default=Path("template_base.json"),
        help="Fighter configuration template (default: template_base.json)",
    )
    parser.add_argument("--model", default="u2net", help="rembg model (default: u2net)")
    return parser.parse_args()


def find_photos(input_dir: Path) -> list[Path]:
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    photos = sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ),
        key=lambda path: path.name.lower(),
    )
    if not photos:
        extensions = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"No supported images found in {input_dir} ({extensions}).")

    stems = [path.stem.casefold() for path in photos]
    duplicates = sorted({stem for stem in stems if stems.count(stem) > 1})
    if duplicates:
        raise ValueError(f"Duplicate image names found: {', '.join(duplicates)}.")
    return photos


def action_from_name(stem: str) -> str:
    name = FRAME_SUFFIX.sub("", ORDER_PREFIX.sub("", stem).casefold())
    if name.startswith("golpe_"):
        return "golpe"
    return name or "sin_clasificar"


def remove_backgrounds(
    photos: Iterable[Path], model_name: str
) -> list[PoseFrame]:
    if REMBG_IMPORT_ERROR is not None:
        raise RuntimeError(
            "rembg is not installed. Run: python -m pip install -r requirements.txt"
        ) from REMBG_IMPORT_ERROR

    session = new_session(model_name)
    frames: list[PoseFrame] = []
    for photo in photos:
        with Image.open(photo) as source:
            rgb = ImageOps.exif_transpose(source).convert("RGB")
        foreground = remove(rgb, session=session).convert("RGBA")
        frames.append(
            PoseFrame(
                source=photo,
                name=photo.stem,
                action=action_from_name(photo.stem),
                image=foreground,
            )
        )
    return frames


def trim_transparency(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("An image became fully transparent after background removal.")
    return image.crop(bbox)


def normalize_frame(frame: PoseFrame) -> PoseFrame:
    trimmed = trim_transparency(frame.image)
    scale = TARGET_HEIGHT / trimmed.height
    width = max(1, round(trimmed.width * scale))
    resized = trimmed.resize((width, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (width, TARGET_HEIGHT), (0, 0, 0, 0))
    canvas.alpha_composite(resized, (0, 0))
    return PoseFrame(frame.source, frame.name, frame.action, canvas)


def create_spritesheet(
    frames: Iterable[PoseFrame],
) -> tuple[Image.Image, dict[str, dict[str, int]]]:
    ordered = list(frames)
    max_width = max(frame.image.width for frame in ordered)
    columns = max(1, math.ceil(math.sqrt(len(ordered))))
    rows = math.ceil(len(ordered) / columns)
    sheet_width = columns * max_width + (columns + 1) * SPRITESHEET_PADDING
    sheet_height = rows * TARGET_HEIGHT + (rows + 1) * SPRITESHEET_PADDING
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
    coordinates: dict[str, dict[str, int]] = {}

    for index, frame in enumerate(ordered):
        column = index % columns
        row = index // columns
        x = SPRITESHEET_PADDING + column * (max_width + SPRITESHEET_PADDING)
        y = SPRITESHEET_PADDING + row * (TARGET_HEIGHT + SPRITESHEET_PADDING)
        frame_x = x + (max_width - frame.image.width) // 2
        sheet.alpha_composite(frame.image, (frame_x, y))
        coordinates[frame.name] = {
            "x": frame_x,
            "y": y,
            "width": frame.image.width,
            "height": frame.image.height,
        }
    return sheet, coordinates


def create_portrait(repose: PoseFrame) -> Image.Image:
    image = trim_transparency(repose.image)
    image_width, image_height = image.size
    head_height = max(1, round(image_height * 0.30))
    head_width = max(1, round(min(image_width * 0.48, image_height * 0.34)))
    left = max(0, round((image_width - head_width) / 2))
    top = max(0, round(image_height * 0.02))
    head = image.crop(
        (left, top, min(image_width, left + head_width), min(image_height, top + head_height))
    )

    size = max(head.width, head.height)
    portrait = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    portrait.alpha_composite(head, ((size - head.width) // 2, (size - head.height) // 2))
    return portrait.resize((256, 256), Image.Resampling.LANCZOS)


def calculate_hurtbox(frame: PoseFrame) -> dict[str, int]:
    bbox = frame.image.getchannel("A").getbbox()
    if bbox is None:
        return {"x": 0, "y": 0, "width": 0, "height": 0}
    left, top, right, bottom = bbox
    width = max(1, round((right - left) * 0.72))
    height = max(1, round((bottom - top) * 0.82))
    x = max(0, round(left + (right - left - width) / 2))
    y = max(0, round(top + (bottom - top) * 0.08))
    return {"x": x, "y": y, "width": width, "height": min(height, frame.image.height - y)}


def calculate_hitbox(frame: PoseFrame) -> dict[str, int]:
    action_frame = ORDER_PREFIX.sub("", frame.name.casefold())
    if not action_frame.startswith(("golpe_activo", "golpe_impacto")):
        return {"x": 0, "y": 0, "width": 0, "height": 0}

    bbox = frame.image.getchannel("A").getbbox()
    if bbox is None:
        return {"x": 0, "y": 0, "width": 0, "height": 0}
    left, top, right, bottom = bbox
    width = max(1, round((right - left) * 0.42))
    height = max(1, round((bottom - top) * 0.20))
    x = min(frame.image.width - 1, round(right * 0.78))
    y = max(0, round(top + (bottom - top) * 0.38))
    if x + width > frame.image.width:
        width = max(1, frame.image.width - x)
    return {"x": x, "y": y, "width": width, "height": min(height, frame.image.height - y)}


def load_template(template_path: Path) -> dict:
    if not template_path.is_file():
        raise FileNotFoundError(f"Template JSON not found: {template_path}")
    with template_path.open("r", encoding="utf-8") as handle:
        template = json.load(handle)
    if not isinstance(template, dict):
        raise ValueError("The configuration template must contain a JSON object.")
    return template


def build_config(
    template: dict,
    frames: list[PoseFrame],
    coordinates: dict[str, dict[str, int]],
    sheet: Image.Image,
) -> dict:
    config = dict(template)
    animations: dict[str, list[dict]] = {}

    for frame in frames:
        sprite = coordinates[frame.name]
        entry = {
            "name": frame.name,
            "source": frame.source.name,
            **sprite,
            "hurtbox": calculate_hurtbox(frame),
            "hitbox": calculate_hitbox(frame),
            "pivot": {"x": round(frame.image.width / 2), "y": TARGET_HEIGHT},
        }
        animations.setdefault(frame.action, []).append(entry)

    config["animations"] = animations
    config["spritesheet"] = "spritesheet.png"
    config["portrait"] = "portrait.png"
    config["canvas"] = {
        "width": sheet.width,
        "height": sheet.height,
        "pivot_y": TARGET_HEIGHT,
    }
    return config


def main() -> int:
    args = parse_args()
    try:
        photos = find_photos(args.input)
        frames = [normalize_frame(frame) for frame in remove_backgrounds(photos, args.model)]
        sheet, coordinates = create_spritesheet(frames)

        repose = next(
            (frame for frame in frames if frame.action == "reposo"),
            frames[0],
        )
        template = load_template(args.template)
        config = build_config(template, frames, coordinates, sheet)

        args.output.mkdir(parents=True, exist_ok=True)
        sheet.save(args.output / "spritesheet.png")
        create_portrait(repose).save(args.output / "portrait.png")
        with (args.output / "fighter_config.json").open("w", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)

        print(f"Generated {len(frames)} sprites: {args.output / 'spritesheet.png'}")
        print(f"Generated portrait: {args.output / 'portrait.png'}")
        print(f"Generated configuration: {args.output / 'fighter_config.json'}")
        return 0
    except (FileNotFoundError, RuntimeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
