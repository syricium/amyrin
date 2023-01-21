import os
import random
import string
import tempfile
from typing import NamedTuple, Optional
from urllib.parse import quote

from discord.ext import commands
from playwright.async_api import Page, async_playwright

""" i might soon continue development of this, but it seems too finnicky and annoying to get all the panels """


class SnippetRCResponse(NamedTuple):
    name: str
    text: str
    url: str


class ScreenshotResponse(NamedTuple):
    temp_dir: tempfile.TemporaryDirectory
    path: os.PathLike


class GoogleParser:
    def __init__(self, browser=None) -> None:
        self._playwright = None
        self._browser = browser

        self._selectors = {
            "CookiePopup": {
                "Popup": ".dbsFrd",
                "Decline": "#W0wltc",
                "Accept": "#L2AGLb",
            },
            "CalculationRichCard": {
                "existence": ".ifM9O",
                "calculationText": ".vUGUtc",
                "calculationResult": "#cwos",
            },
            "SnippetRichCard1": {
                "existence": ".ifM9O",
                "name": "div.g:nth-child(2) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > a:nth-child(1) > h3:nth-child(2)",
                "text": ".V3FYCf > div:nth-child(1) > div:nth-child(1) > span:nth-child(1) > span:nth-child(1)",
                "url": "div.g:nth-child(2) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > a:nth-child(1)",
            },
        }

    async def _remove_cookie_popup(self, page: Page) -> None:
        cookie_popup = self._selectors["CookiePopup"]

        cookie_popup_selector = page.locator(cookie_popup["Popup"])
        cookie_accept_selector = page.locator(cookie_popup["Accept"])

        if (await cookie_popup_selector.is_visible()) and (
            await cookie_accept_selector.is_visible()
        ):
            await cookie_accept_selector.click()

    async def _check_snippet_rich_card_1(
        self, page: Page
    ) -> Optional[SnippetRCResponse]:
        snippet_rc = self._selectors["SnippetRichCard1"]
        snippet_rc_existence = page.locator(snippet_rc["existence"])

        if (await snippet_rc_existence.count() == 1) and not (
            await snippet_rc_existence.is_visible()
        ):
            return

        snippet_name = page.locator(snippet_rc["name"])
        snippet_text = page.locator(snippet_rc["text"])
        snippet_url = page.locator(snippet_rc["url"])

        snippet_name_content = snippet_text_content = None

        if (await snippet_name.count() == 1) and (await snippet_name.is_visible()):
            snippet_name_content = await snippet_name.text_content()

        if (await snippet_text.count() == 1) and (await snippet_text.is_visible()):
            snippet_text_content = await snippet_text.text_content()

        if (
            snippet_name is None
            or snippet_name_content is None
            or snippet_text is None
            or snippet_text_content is None
            or snippet_url is None
            or await snippet_url.count() != 1
            or await snippet_url.get_attribute("href") is None
        ):
            return

        return SnippetRCResponse(
            name=snippet_name_content,
            text=snippet_text_content,
            url=await snippet_url.get_attribute("href"),
        )

    async def search(
        self, query: str, language: str = "en"
    ) -> Optional[ScreenshotResponse | SnippetRCResponse]:
        page = await self._browser.new_page()

        new_query = quote(query)
        await page.goto(
            "https://www.google.com/search" f"?hl={language}" f"&q={new_query}"
        )

        await self._remove_cookie_popup(page)
        snippet_rc = await self._check_snippet_rich_card_1(page=page)

        if snippet_rc is not None:
            return snippet_rc

        temp_dir = tempfile.TemporaryDirectory()
        fn = "".join(random.choices(string.ascii_letters, k=12)) + ".jpg"
        path = os.path.join(temp_dir.name, fn)
        await page.screenshot(path=path, type="jpeg")

        await page.close()
        return ScreenshotResponse(temp_dir=temp_dir, path=path)

    async def initialize(self):
        if not self._browser:
            print("no browser")
            self._browser = await self._setup_browser()

    async def _setup_browser(self):
        playwright = await async_playwright().start()
        return await playwright.chromium.launch()


async def setup(bot: commands.Bot):
    bot.gp = GoogleParser(bot.browser)
    await bot.gp.initialize()


async def teardown(bot: commands.Bot):
    bot.gp = None
