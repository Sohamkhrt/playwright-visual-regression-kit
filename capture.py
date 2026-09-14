from __future__ import annotations

import argparse
import os
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from conftest import VIEWPORT, stabilize_page
from pages import SNAPSHOTS, SnapshotState


ROOT = Path(__file__).resolve().parent
BASELINES_DIR = ROOT / "baselines"
CURRENT_DIR = ROOT / "current"


def apply_optional_mutation(page: Page) -> None:
    """A deterministic test hook used to demonstrate a caught regression."""
    if os.getenv("VISUAL_TEST_MUTATION") != "1":
        return
    page.evaluate(
        """
        () => {
          const banner = document.createElement('div');
          banner.id = 'intentional-visual-regression';
          banner.textContent = 'INTENTIONAL REGRESSION';
          Object.assign(banner.style, {
            background: '#d00000', color: 'white', font: '700 24px sans-serif',
            padding: '18px', textAlign: 'center', width: '100%'
          });
          document.body.prepend(banner);
        }
        """
    )


def prepare_state(page: Page, state: SnapshotState) -> None:
    state.setup(page)
    apply_optional_mutation(page)
    page.evaluate("document.fonts && document.fonts.ready")


def capture_all(update_baseline: bool = False) -> None:
    BASELINES_DIR.mkdir(exist_ok=True)
    CURRENT_DIR.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for state in SNAPSHOTS:
                context = browser.new_context(
                    viewport=VIEWPORT,
                    device_scale_factor=1,
                    color_scheme="light",
                    locale="en-US",
                    timezone_id="UTC",
                    reduced_motion="reduce",
                )
                page = context.new_page()
                stabilize_page(page)
                prepare_state(page, state)
                baseline = BASELINES_DIR / f"{state.name}.png"
                destination = (
                    baseline
                    if update_baseline or not baseline.exists()
                    else CURRENT_DIR / f"{state.name}.png"
                )
                page.screenshot(path=str(destination), full_page=True)
                print(f"{state.name}: {destination.relative_to(ROOT)}")
                context.close()
        finally:
            browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture visual snapshots.")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Overwrite all baseline images instead of writing current images.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    capture_all(parse_args().update_baseline)

