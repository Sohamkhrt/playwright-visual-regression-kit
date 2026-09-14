from __future__ import annotations

from collections.abc import Iterator
import json

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright


VIEWPORT = {"width": 1280, "height": 720}

STABILITY_CSS = """
*, *::before, *::after {
  animation-delay: 0s !important;
  animation-duration: 0s !important;
  animation-iteration-count: 1 !important;
  caret-color: transparent !important;
  scroll-behavior: auto !important;
  transition-delay: 0s !important;
  transition-duration: 0s !important;
}
"""


def stabilize_page(page: Page) -> None:
    """Install CSS before app code runs, and again in the current document."""
    script = """
        (() => {
          const css = __STABILITY_CSS__;
          const install = () => {
            const style = document.createElement('style');
            style.dataset.visualRegression = 'stability';
            style.textContent = css;
            (document.head || document.documentElement).appendChild(style);
          };
          if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', install, {once: true});
          } else {
            install();
          }
        })()
        """.replace("__STABILITY_CSS__", json.dumps(STABILITY_CSS))
    page.add_init_script(script)


@pytest.fixture(scope="session")
def playwright_instance() -> Iterator[Playwright]:
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Iterator[Browser]:
    launched = playwright_instance.chromium.launch(headless=True)
    yield launched
    launched.close()


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    context = browser.new_context(
        viewport=VIEWPORT,
        device_scale_factor=1,
        color_scheme="light",
        locale="en-US",
        timezone_id="UTC",
        reduced_motion="reduce",
    )
    current_page = context.new_page()
    stabilize_page(current_page)
    yield current_page
    context.close()
