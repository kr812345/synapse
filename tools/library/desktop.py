"""Brave desktop tools.

Playwright attaches to the Brave window already running on the virtual
display (PIP_BROWSER_CDP, default http://127.0.0.1:9222). Tests set
PIP_DESKTOP_DRIVER=fake.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Protocol

from tools.tool_registry import ToolInterface
from vault.approvals import ApprovalGate
from vault.store import VaultError, VaultStore


class DesktopDriver(Protocol):
    async def open(self, url: str) -> dict: ...
    async def snapshot(self) -> dict: ...
    async def click(self, selector: str) -> dict: ...
    async def type_text(self, selector: str, text: str) -> dict: ...


class FakeDesktop:
    """In-memory desktop used by tests and by local runs without Brave."""

    def __init__(self):
        self.url = ""
        self.clicks: list[str] = []
        self.typed: list[tuple[str, str]] = []
        self.elements = {
            "#user": "",
            "#password": "",
            "button": "Go",
        }

    async def open(self, url: str) -> dict:
        self.url = url
        return {"status": "ok", "url": url}

    async def snapshot(self) -> dict:
        visible = {key: ("filled" if key == "#password" and value else value) for key, value in self.elements.items()}
        return {"status": "ok", "url": self.url, "elements": visible}

    async def click(self, selector: str) -> dict:
        self.clicks.append(selector)
        return {"status": "ok", "selector": selector}

    async def type_text(self, selector: str, text: str) -> dict:
        self.typed.append((selector, text))
        if selector in self.elements:
            self.elements[selector] = text
        return {"status": "ok", "selector": selector, "characters": len(text)}


class PlaywrightDesktop:
    """Attach to Brave over the Chrome DevTools port."""

    def __init__(self, cdp_url: Optional[str] = None):
        self.cdp_url = cdp_url or os.environ.get("PIP_BROWSER_CDP", "http://127.0.0.1:9222")
        self._playwright = None
        self._browser = None
        self._page = None

    async def _page_handle(self):
        if self._page is not None:
            return self._page
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed") from exc
        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
        except Exception as exc:
            await self._playwright.stop()
            self._playwright = None
            raise RuntimeError(
                "Brave is not accepting connections on the desktop. Start pip-desktop."
            ) from exc
        context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
        self._page = context.pages[0] if context.pages else await context.new_page()
        return self._page

    async def open(self, url: str) -> dict:
        page = await self._page_handle()
        await page.goto(url)
        return {"status": "ok", "url": page.url}

    async def snapshot(self) -> dict:
        page = await self._page_handle()
        title = await page.title()
        return {"status": "ok", "url": page.url, "title": title}

    async def click(self, selector: str) -> dict:
        page = await self._page_handle()
        await page.click(selector)
        return {"status": "ok", "selector": selector}

    async def type_text(self, selector: str, text: str) -> dict:
        page = await self._page_handle()
        await page.fill(selector, "")
        await page.type(selector, text)
        return {"status": "ok", "selector": selector, "characters": len(text)}


_driver: Optional[DesktopDriver] = None


def get_driver() -> DesktopDriver:
    global _driver
    if _driver is not None:
        return _driver
    kind = os.environ.get("PIP_DESKTOP_DRIVER", "playwright")
    if kind == "fake":
        _driver = FakeDesktop()
    else:
        _driver = PlaywrightDesktop()
    return _driver


def set_driver(driver: Optional[DesktopDriver]) -> None:
    global _driver
    _driver = driver


class BrowserOpen(ToolInterface):
    name = "browser_open"
    description = "Open a URL in Pip's Brave window."
    parameters = {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
    required_permissions = ["desktop"]

    async def execute(self, url: str = "", **kwargs) -> Any:
        if not url:
            return {"status": "error", "message": "url is required"}
        try:
            return await get_driver().open(url)
        except Exception as exc:
            return {"status": "error", "message": str(exc)}


class BrowserSnapshot(ToolInterface):
    name = "browser_snapshot"
    description = "Read the current page in Pip's Brave window."
    parameters = {"type": "object", "properties": {}}
    required_permissions = ["desktop"]

    async def execute(self, **kwargs) -> Any:
        try:
            return await get_driver().snapshot()
        except Exception as exc:
            return {"status": "error", "message": str(exc)}


class BrowserClick(ToolInterface):
    name = "browser_click"
    description = "Click a selector in Pip's Brave window."
    parameters = {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}
    required_permissions = ["desktop"]

    async def execute(self, selector: str = "", **kwargs) -> Any:
        if not selector:
            return {"status": "error", "message": "selector is required"}
        try:
            return await get_driver().click(selector)
        except Exception as exc:
            return {"status": "error", "message": str(exc)}


class BrowserType(ToolInterface):
    name = "browser_type"
    description = "Type into a selector. The typed text is not returned."
    parameters = {
        "type": "object",
        "properties": {
            "selector": {"type": "string"},
            "text": {"type": "string"},
        },
        "required": ["selector", "text"],
    }
    required_permissions = ["desktop"]

    async def execute(self, selector: str = "", text: str = "", **kwargs) -> Any:
        if not selector:
            return {"status": "error", "message": "selector is required"}
        try:
            result = await get_driver().type_text(selector, text)
            result.pop("text", None)
            return result
        except Exception as exc:
            return {"status": "error", "message": str(exc)}


class BrowserFillLogin(ToolInterface):
    name = "browser_fill_login"
    description = "Fill a saved vault login into the open page. Waits for approval. Does not return the secret."
    parameters = {
        "type": "object",
        "properties": {
            "secret": {"type": "string"},
            "user_selector": {"type": "string"},
            "password_selector": {"type": "string"},
        },
        "required": ["secret", "user_selector", "password_selector"],
    }
    required_permissions = ["desktop"]

    def __init__(self, store: Optional[VaultStore] = None, gate: Optional[ApprovalGate] = None):
        self.store = store or VaultStore()
        self.gate = gate or ApprovalGate(self.store)

    async def execute(
        self,
        secret: str = "",
        user_selector: str = "",
        password_selector: str = "",
        **kwargs,
    ) -> Any:
        if not secret:
            return {"status": "error", "message": "secret is required"}
        record = self.gate.request("use-credential", secret, "fill a browser login")
        allowed = await self.gate.wait(record["id"], timeout=float(os.environ.get("PIP_APPROVAL_TIMEOUT", "120")))
        if not allowed:
            return {"status": "refused", "approval_id": record["id"], "secret": secret}
        try:
            raw = self.store.get(secret, purpose="action", approval_id=record["id"])
        except VaultError as exc:
            return {"status": "error", "message": str(exc), "approval_id": record["id"]}
        try:
            payload = json_login(raw)
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}
        driver = get_driver()
        await driver.type_text(user_selector, payload["username"])
        await driver.type_text(password_selector, payload["password"])
        return {
            "status": "ok",
            "approval_id": record["id"],
            "secret": secret,
            "filled": ["username", "password"],
        }


def json_login(raw: str) -> dict:
    import json

    data = json.loads(raw)
    if "username" not in data or "password" not in data:
        raise ValueError("login secret must include username and password")
    return {"username": str(data["username"]), "password": str(data["password"])}
