from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page

from capture import BASELINES_DIR, CURRENT_DIR, prepare_state
from diff import DEFAULT_THRESHOLD_PERCENT, compare_images
from pages import SNAPSHOTS, SnapshotState


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "visual-results.json"
RESULTS_PATH.unlink(missing_ok=True)


def _record_result(result: dict[str, object]) -> None:
    existing: list[dict[str, object]] = []
    if RESULTS_PATH.exists():
        existing = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    existing.append(result)
    RESULTS_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")


@pytest.mark.parametrize("state", SNAPSHOTS, ids=lambda state: state.name)
def test_visual_snapshot(page: Page, state: SnapshotState) -> None:
    baseline = BASELINES_DIR / f"{state.name}.png"
    if not baseline.exists():
        pytest.fail(
            f"Baseline is missing: {baseline}. "
            "Run `python capture.py --update-baseline` and commit baselines/."
        )

    prepare_state(page, state)
    CURRENT_DIR.mkdir(exist_ok=True)
    current = CURRENT_DIR / f"{state.name}.png"
    page.screenshot(path=str(current), full_page=True)
    result = compare_images(state.name, baseline, current)
    _record_result(
        {
            "name": result.name,
            "passed": result.passed,
            "diff_percent": round(result.diff_percent, 6),
            "changed_pixels": result.changed_pixels,
            "compared_pixels": result.compared_pixels,
            "size_mismatch": result.size_mismatch,
            "diff_path": str(result.diff_path.relative_to(ROOT)),
        }
    )
    assert result.passed, (
        f"{state.name}: {result.diff_percent:.4f}% pixels changed "
        f"(allowed {DEFAULT_THRESHOLD_PERCENT:.4f}%); diff: {result.diff_path}"
    )
