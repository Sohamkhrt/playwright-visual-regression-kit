from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from playwright.sync_api import Page


TODO_MVC_URL = "https://demo.playwright.dev/todomvc/#/"


@dataclass(frozen=True)
class SnapshotState:
    name: str
    setup: Callable[[Page], None]
    url: str = TODO_MVC_URL


def _reset(page: Page, url: str = TODO_MVC_URL) -> None:
    page.goto(url, wait_until="networkidle")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="networkidle")
    page.locator(".todoapp").wait_for(state="visible")


def empty_list(page: Page) -> None:
    _reset(page)


def one_item_added(page: Page) -> None:
    _reset(page)
    page.get_by_placeholder("What needs to be done?").fill("Write visual tests")
    page.get_by_placeholder("What needs to be done?").press("Enter")


def item_marked_complete(page: Page) -> None:
    one_item_added(page)
    page.get_by_label("Toggle Todo").check()


def item_deleted(page: Page) -> None:
    _reset(page)
    entry = page.get_by_placeholder("What needs to be done?")
    entry.fill("Keep this item")
    entry.press("Enter")
    entry.fill("Delete this item")
    entry.press("Enter")
    doomed = page.locator("li", has_text="Delete this item")
    doomed.hover()
    doomed.locator("button.destroy").click()


SNAPSHOTS = (
    SnapshotState("empty_list", empty_list),
    SnapshotState("one_item_added", one_item_added),
    SnapshotState("item_marked_complete", item_marked_complete),
    SnapshotState("item_deleted", item_deleted),
)

