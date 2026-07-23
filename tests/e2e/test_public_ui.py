from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page

ROOT = Path(__file__).resolve().parents[2]


def _document() -> tuple[str, str, str]:
    html = (ROOT / "app/templates/public/index.html").read_text(encoding="utf-8")
    html = (
        html.replace("{{ poll_interval_ms }}", "60000")
        .replace('<link rel="stylesheet" href="/static/public.css">', "")
        .replace('<script src="/static/public.js" defer></script>', "")
        .replace("<head>", '<head><base href="http://example.test/">')
    )
    css = (ROOT / "app/static/public.css").read_text(encoding="utf-8")
    javascript = (ROOT / "app/static/public.js").read_text(encoding="utf-8")
    return html, css, javascript


def test_confirmation_and_rank_reveal(page: Page) -> None:
    initial = {
        "summary": {
            "top10HitCount": 1,
            "hitRanks": [7],
            "answeredCount": 1,
            "totalCount": 3,
            "updatedAt": None,
        },
        "categories": [
            {
                "id": 1,
                "name": "ハンバーグ",
                "menus": [
                    {"id": "a", "name": "未回答メニュー", "answered": False},
                    {"id": "b", "name": "回答済みメニュー", "answered": True, "rank": 7},
                    {"id": "c", "name": "別メニュー", "answered": False},
                ],
            }
        ],
    }
    answered = {
        **initial,
        "summary": {
            "top10HitCount": 2,
            "hitRanks": [1, 7],
            "answeredCount": 2,
            "totalCount": 3,
            "updatedAt": "now",
        },
        "categories": [
            {
                "id": 1,
                "name": "ハンバーグ",
                "menus": [
                    {"id": "a", "name": "未回答メニュー", "answered": True, "rank": 1},
                    {"id": "b", "name": "回答済みメニュー", "answered": True, "rank": 7},
                    {"id": "c", "name": "別メニュー", "answered": False},
                ],
            }
        ],
    }
    state = {"answered": False}

    def route_api(route) -> None:  # type: ignore[no-untyped-def]
        if route.request.url.endswith("/api/state"):
            body = answered if state["answered"] else initial
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
            return
        if route.request.url.endswith("/api/guesses"):
            state["answered"] = True
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "results": [
                            {
                                "menuId": "a",
                                "menuName": "未回答メニュー",
                                "rank": 1,
                                "isTop10": True,
                                "newlyAnswered": True,
                            }
                        ],
                        "summary": answered["summary"],
                    }
                ),
            )
            return
        route.continue_()

    html, css, javascript = _document()
    page.route("**/api/**", route_api)
    page.set_content(html)
    page.add_style_tag(content=css)
    page.add_script_tag(content=javascript)
    page.locator(".menu-card").first.wait_for()

    assert page.locator("#reveal-overlay").is_hidden()
    page.get_by_text("未回答メニュー", exact=True).click()
    page.get_by_role("button", name="順位を確認する").click()
    assert page.locator("#confirm-dialog").is_visible()

    page.get_by_role("button", name="順位発表へ").click()
    page.locator("#reveal-overlay:not([hidden])").wait_for()
    assert page.locator("#reveal-menu").inner_text() == "未回答メニュー"
    page.wait_for_function("document.querySelector('#reveal-rank').textContent === '1位'")
    page.wait_for_function("document.querySelector('#reveal-overlay').hidden === true")

    assert page.get_by_text("2 / 10", exact=True).is_visible()
    assert page.get_by_text("1位", exact=True).count() >= 1
    answered_card = page.locator(".menu-card", has_text="未回答メニュー")
    assert "answered" in answered_card.get_attribute("class")
