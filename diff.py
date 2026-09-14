from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parent
DEFAULT_THRESHOLD_PERCENT = 0.5
DEFAULT_CHANNEL_TOLERANCE = 16

# Coordinates are (left, top, right, bottom), in CSS/device pixels at scale 1.
# Example: "dashboard": [(1080, 0, 1280, 80)] to ignore a live timestamp.
EXCLUSION_BOXES: dict[str, list[tuple[int, int, int, int]]] = {
    "empty_list": [],
    "one_item_added": [],
    "item_marked_complete": [],
    "item_deleted": [],
}


@dataclass(frozen=True)
class DiffResult:
    name: str
    passed: bool
    diff_percent: float
    changed_pixels: int
    compared_pixels: int
    diff_path: Path
    size_mismatch: bool


def _rgba_canvas(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.paste(image.convert("RGBA"), (0, 0))
    return canvas


def compare_images(
    name: str,
    baseline_path: Path,
    current_path: Path,
    *,
    diff_dir: Path | None = None,
    threshold_percent: float = DEFAULT_THRESHOLD_PERCENT,
    channel_tolerance: int = DEFAULT_CHANNEL_TOLERANCE,
    exclusion_boxes: Iterable[tuple[int, int, int, int]] | None = None,
) -> DiffResult:
    if not baseline_path.exists():
        raise FileNotFoundError(
            f"Missing baseline {baseline_path}. Run: python capture.py --update-baseline"
        )
    if not current_path.exists():
        raise FileNotFoundError(f"Missing current screenshot {current_path}")

    with Image.open(baseline_path) as baseline_source, Image.open(current_path) as current_source:
        size_mismatch = baseline_source.size != current_source.size
        size = (
            max(baseline_source.width, current_source.width),
            max(baseline_source.height, current_source.height),
        )
        baseline = _rgba_canvas(baseline_source, size)
        current = _rgba_canvas(current_source, size)

    raw_diff = ImageChops.difference(baseline, current)
    mask = Image.new("L", size, 0)
    raw_pixels = raw_diff.load()
    mask_pixels = mask.load()
    for y in range(size[1]):
        for x in range(size[0]):
            mask_pixels[x, y] = (
                255 if max(raw_pixels[x, y]) > channel_tolerance else 0
            )

    excluded = list(exclusion_boxes if exclusion_boxes is not None else EXCLUSION_BOXES.get(name, []))
    mask_draw = ImageDraw.Draw(mask)
    for box in excluded:
        mask_draw.rectangle(box, fill=0)

    changed_pixels = mask.histogram()[255]
    excluded_mask = Image.new("L", size, 255)
    excluded_draw = ImageDraw.Draw(excluded_mask)
    for box in excluded:
        excluded_draw.rectangle(box, fill=0)
    compared_pixels = excluded_mask.histogram()[255]
    diff_percent = 100.0 * changed_pixels / compared_pixels if compared_pixels else 0.0

    visualization = baseline.convert("RGB").point(lambda value: int(value * 0.35))
    red = Image.new("RGB", size, (255, 28, 28))
    visualization.paste(red, mask=mask)
    if mask.getbbox():
        box = mask.getbbox()
        ImageDraw.Draw(visualization).rectangle(box, outline=(255, 220, 0), width=3)

    output_dir = diff_dir or ROOT / "diffs"
    output_dir.mkdir(parents=True, exist_ok=True)
    diff_path = output_dir / f"{name}_diff.png"
    visualization.save(diff_path)

    return DiffResult(
        name=name,
        passed=diff_percent <= threshold_percent,
        diff_percent=diff_percent,
        changed_pixels=changed_pixels,
        compared_pixels=compared_pixels,
        diff_path=diff_path,
        size_mismatch=size_mismatch,
    )
