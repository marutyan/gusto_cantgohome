from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright


@pytest.fixture
def page() -> Iterator[Page]:
    with sync_playwright() as playwright:
        system_chromium = Path("/usr/bin/chromium")
        launch_options = {"headless": True}
        if system_chromium.exists():
            launch_options["executable_path"] = str(system_chromium)
            launch_options["args"] = ["--no-sandbox"]
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        yield page
        browser.close()
