import traceback
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional
import re
from playwright.async_api._generated import Browser
from urllib.parse import quote

"im continuing development at some point maybe, there just barely is a point in making a google scraper when google.com exists and is not hard to use"

class Response:
    def __bool__(self):
        return any(
            getattr(self, str(attr)) for attr in dir(self) if not attr.startswith("_")
        )


@dataclass(unsafe_hash=True, frozen=True)
class Website(Response):
    """
    A class that represents a website returned by the scraper
    """

    title: str
    href: str
    description: str


@dataclass(unsafe_hash=True, frozen=True)
class Link(Response):
    text: str
    href: str


@dataclass(unsafe_hash=True, frozen=True)
class Description(Response):
    text: str
    link: Link


@dataclass(unsafe_hash=True, frozen=True)
class DescriptionAttribute(Response):
    key: Link
    value: str


@dataclass(unsafe_hash=True, frozen=True)
class ComplementaryResult(Response):
    title: str
    subtitle: str
    description: Description
    attributes: List[DescriptionAttribute]
    image: str = None


@dataclass(unsafe_hash=True, frozen=True)
class FeaturedSnippet(Response):
    title: str
    description: str
    link: Link


@dataclass(unsafe_hash=True, frozen=True)
class CalculatorResult(Response):
    equation: str
    answer: str


@dataclass(unsafe_hash=True, frozen=True)
class Currency(Response):
    value: str
    currencytype: str


@dataclass(unsafe_hash=True, frozen=True)
class CurrencyResponse(Response):
    currencyinput: Currency
    currencyoutput: Currency

    when: str


@dataclass(unsafe_hash=True, frozen=True)
class Time(Response):
    time: str
    date: str
    where: str


@dataclass(unsafe_hash=True, frozen=True)
class Definition(Response):
    definition: str
    example: str


@dataclass(unsafe_hash=True, frozen=True)
class WordType(Response):
    wordtype: str
    definitions: List[Definition]


@dataclass(unsafe_hash=True, frozen=True)
class DefinitionResponse(Response):
    word: str
    pronunciation: str
    definitions: List[WordType]


@dataclass(unsafe_hash=True, frozen=True)
class WeatherResponse(Response):
    where: str
    when: str
    description: str
    celcius: int
    fahrenheit: int

    asset: str


@dataclass(unsafe_hash=True, frozen=True)
class Phrase(Response):
    lang: str
    text: str
    pronunciation: str


@dataclass(unsafe_hash=True, frozen=True)
class TranslationResponse(Response):
    source: Phrase
    target: Phrase


@dataclass(unsafe_hash=True, frozen=True)
class Unit(Response):
    unit: str
    value: str


@dataclass(unsafe_hash=True, frozen=True)
class ConversionResponse(Response):
    type_: str

    source: Unit
    target: Unit

    formula: str


@dataclass(unsafe_hash=True, frozen=True)
class Stats(Response):
    results: int
    time: float


@dataclass(unsafe_hash=True, frozen=True)
class SearchResults(Response):
    metrics: str

    websites: List[Website]
    complementary_result: ComplementaryResult
    snippet: FeaturedSnippet
    calculator: CalculatorResult
    currency: CurrencyResponse
    local_time: Time
    definition: DefinitionResponse
    event_time: str
    weather: WeatherResponse
    translation: TranslationResponse
    unit_conversion: ConversionResponse


class GoogleScraper:
    def __init__(
        self,
        browser: Browser = None,
        *,
        base_url: str = "https://www.google.com/",
        lang: str = "en",
        safe: bool = True,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
    ):
        self._browser = browser
        
        self.base_url = base_url
        self.lang = lang
        self.user_agent = user_agent
        self.safe = safe

    async def _get_search_html(
        self,
        query: str
    ) -> BeautifulSoup:
        page = await self._browser.new_page()
        formatted_query = quote(query)
        safe_search = "active" if self.safe else "images"
        
        await page.goto(
            f"{self.base_url}search"
            f"?q={formatted_query}"
            f"&hl={self.lang}"
            f"&safe={safe_search}"
        )
        
        cookie_popup = page.locator(".dbsFrd")
        cookie_accept = page.locator("#L2AGLb")
        
        if (await cookie_popup.is_visible()) and (await cookie_accept.is_visible()):
            await cookie_accept.click()
            
        await asyncio.sleep(5)
            
        await page.wait_for_load_state("domcontentloaded")
        
        content = await page.content()
        soup = BeautifulSoup(
            content, "html.parser"
        )
        
        with open("content.txt", "w", encoding="utf-8") as f:
            f.write(soup.prettify("utf-8").decode())
        
        await page.close()
        
        return soup

    async def _get_websites(self, soup: BeautifulSoup) -> Optional[List[Website]]:
        # get a list of all search results that redirect to websites
        websites = soup.find_all("div", class_="g Ww4FFb vt6azd tF2Cxc")
        if websites is None:
            websites = soup.find("div", class_="v7W49e").children

        # prepare a list for storing the results
        results = []

        # iterate through all website results
        for website in websites:
            # get the title of the website result or fallback to "failed to fetch 😢😢😢"
            try:
                title = website.find("h3", class_="LC20lb MBeuO DKV0Md")
                title = title.string.strip()
            except AttributeError:
                title = "failed to fetch 😢😢😢"

            # get the link to the website result
            href = website.find("a")["href"]
                
            # get the description of the website result
            try:
                # get the parent of the description element
                desc_elem = website.find("div", {"data-sokoban-feature": "nke7rc"})
                # get the span element of the website result that stores the description text
                text_elem = desc_elem.find("span")
                # store the description in a variable
                description = text_elem.text
            except AttributeError as exc:
                traceback.print_exception(type(exc), exc, exc.__traceback__)
                description = "No information is available for this page."

            # add the website result with all it's data to the results list
            results.append(Website(title, href, description))

        # return the website results as a list
        return list(results)

    async def _get_complementary_result(
        self, soup: BeautifulSoup
    ) -> Optional[ComplementaryResult]:
        try:
            card = soup.find("div", class_="osrp-blk") or \
                    soup.find("div", class_="sATSHe") or \
                    soup.find("div", jsname="xQjRM")
            top_card = soup.find("div", class_="HdbW6 MjUjnf VM6qJ")

            print("card")

            if top_card is not None:
                title = top_card.find(
                    "div", class_="PyJv1b gsmt PZPZlf"
                )  # Complementary result card title
                title = title.find("span").string if title else None
                
                image = top_card.find("div", class_="PZPZlf") # Complementary result card image
                image = image["data-lpage"] if image else None
            else:
                title = card.find(
                    "a", class_="Ui2TZ WCMfob oRJe3d"
                )  # Complementary result card title
                title = title.find("span").string if title else None
                
                image = card.find("g-img", class_="PZPZlf") # Complementary result card image
                image = image["data-lpage"] if image else None
                
            print(f"card: {card is None}")
            print(f"top_card: {top_card is None}")
                
            card = top_card if card is None else card

            subtitle = card.find("div", class_="wx62f PZPZlf x7XAkb") # Complementary result card subtitle
            subtitle = subtitle.string if subtitle else None

            website = card.find("a", class_="B1uW2d ellip PZPZlf")  # Official website
            website = (
                Link(website.find("span", class_="ellip").string, website["href"])
                if website
                else None
            )

            print(card.find_all("div", {"data-attrid": "description"}))
            description = card.find(
                "div", jsname="g7W7Ed"
            )  # Knowledge card description
            _dt = description.find_all("span")[0].string if description else None

            _dl = description.find("a") if description else None
            _dl = Link(_dl.string, _dl["href"]) if _dl else None

            description = Description(_dt, _dl)

            attributes = []

            for attribute in card.find_all("div", class_="wDYxhc"):
                name = attribute.find("span")
                name = name.find("a", class_="fl") if name else None

                if not name:
                    continue

                name = Link(
                    name.string, self.base_url + name["href"].split("&stick")[0]
                )

                value = attribute.find("span", class_="LrzXr kno-fv wHYlTd z8gr9e")
                value = value.get_text() if value else None

                attributes.append(DescriptionAttribute(name, value))

            if not any([title, subtitle, description, attributes, image]):
                return

            return ComplementaryResult(title, subtitle, description, attributes, image)
        except Exception as e:
            return e

    async def _get_featured_snippet(
        self, soup: BeautifulSoup
    ) -> Optional[FeaturedSnippet]:
        _ = soup.find("div", class_="ifM9O")

        if not _:
            return

        title = _.find("a", class_="FLP8od")
        title = title.string if title else None

        description = _.find("span", class_="hgKElc")
        description = description.get_text() if description else None

        a = _.find("div", class_="yuRUbf")
        _at = a.find("h3", class_="LC20lb MBeuO DKV0Md") if a else None
        _at = _at.string if _at else None

        _al = a.find("a") if a else None
        _al = _al["href"] if _al else None

        link = Link(_at, _al)

        return FeaturedSnippet(title, description, link)

    async def _get_calculator_result(
        self, soup: BeautifulSoup
    ) -> Optional[CalculatorResult]:
        ...

    async def _get_currency_conversion(
        self, soup: BeautifulSoup
    ) -> Optional[CurrencyResponse]:
        ...

    async def _get_local_time(self, soup: BeautifulSoup) -> Optional[Time]:
        ...

    async def _get_definition(
        self, soup: BeautifulSoup
    ) -> Optional[DefinitionResponse]:
        ...

    async def _get_event_time(self, soup: BeautifulSoup) -> Optional[str]:
        ...

    async def _get_weather_result(
        self, soup: BeautifulSoup
    ) -> Optional[WeatherResponse]:
        ...

    async def _get_translation(
        self, soup: BeautifulSoup
    ) -> Optional[TranslationResponse]:
        ...

    async def _get_unit_conversion(
        self, soup: BeautifulSoup
    ) -> Optional[ConversionResponse]:
        ...

    async def search(self, query: str) -> Optional[SearchResults]:
        soup = await self._get_search_html(query)

        websites = await self._get_websites(soup)
        complementary_result = await self._get_complementary_result(soup)
        snippet = await self._get_featured_snippet(soup)
        calculator = await self._get_calculator_result(soup)
        currency = await self._get_currency_conversion(soup)
        local_time = await self._get_local_time(soup)
        definition = await self._get_definition(soup)
        event_time = await self._get_event_time(soup)
        weather = await self._get_weather_result(soup)
        translation = await self._get_translation(soup)
        unit_conversion = await self._get_unit_conversion(soup)

        try:
            stats = soup.find("div", id="result-stats").get_text().strip("\xa0").strip()

            match = re.match(
                r"About (?P<results>[0-9,\.]+) results \((?P<time>[0-9.\,]+) seconds\)",
                stats,
                re.I,
            )

            if match is not None:
                results = (
                    match.group("results")
                    .replace(",", "")
                    .replace(".", "")
                )
                time = (
                    match.group("time")
                    .replace(",", ".")
                )
                
                stats = Stats(
                    int(results),
                    float(time),
                )
            else:
                stats = None
        except Exception:
            stats = None

        if not any(
            [
                websites,
                complementary_result,
                snippet,
                calculator,
                currency,
                local_time,
                definition,
                event_time,
                weather,
                translation,
                unit_conversion,
            ]
        ):
            return

        return SearchResults(
            stats,
            websites,
            complementary_result,
            snippet,
            calculator,
            currency,
            local_time,
            definition,
            event_time,
            weather,
            translation,
            unit_conversion,
        )
        
async def setup(bot):
    pass