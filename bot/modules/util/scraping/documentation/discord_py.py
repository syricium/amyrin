import discord
import re
from dataclasses import dataclass
from typing import List, Optional, Dict
from urllib.parse import urlparse, urljoin, ParseResult

from bs4 import BeautifulSoup, Tag, SoupStrainer
from playwright.async_api._generated import Browser
from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError
from modules.util.timer import Timer
from humanfriendly import format_timespan
from sphobjinv import Inventory, DataObjStr
from modules.util.executor import executor
from fuzzywuzzy import fuzz

class Response:
    def __bool__(self):
        return any(
            getattr(self, str(attr)) for attr in dir(self) if not attr.startswith("_")
        )

@dataclass(frozen=True)
class Documentation:
    full_name: str
    name: str
    description: str
    examples: List[str]
    url: str
    fields: Dict[str, List[str]]
    time: Optional[int]
    
    def to_embed(self, color: Optional[int] = None):
        description = f"```py\n{self.full_name}\n```{self.description}".strip()
        
        embed = discord.Embed(
            title=self.name,
            url=self.url,
            description=description,
            color=color
        )
        embed.set_author(
            name="Discord.py Documentation",
            icon_url="https://cdn.discordapp.com/attachments/381963689470984203/1068553303908155442/sW87z7N.png"
        )
        
        for name, field in self.fields.items():
            embed.add_field(
                name=name,
                value=field,
                inline=False
            )
        
        return embed
    
class SearchResults:
    def __init__(
        self,
        results: set[str, str, bool],
        query_time: int
    ) -> None:
        self.results = results
        self.query_time = query_time
    
    def __list__(self):
        return self.results
    
    def to_embed(self, color: Optional[int] = None):
        description = "\n".join(
            f"[`{name}`]({url})"
            for name, url, _ in self.results
        )
        
        embed = discord.Embed(
            description=description,
            color=color
        )
        
        query_time = format_timespan(self.query_time)
        embed.set_footer(
            text=f"Fetched in {query_time}"
        )
        
        return embed


class DocScraper:
    def __init__(
        self,
        browser: Browser = None
    ):
        self._browser = browser

        self._base_url = "https://discordpy.readthedocs.io/en/stable/"
        self._inv_url = urljoin(self._base_url, "objects.inv")
        self._inv: Inventory = None
    
    async def _get_html(
        self, url: str, timeout: int = 0, wait_until: Optional[str] = None
    ) -> str:
        page = await self._browser.new_page()

        await page.goto(url)
            
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except PlaywrightTimeoutError:
            pass

        content = await page.content()
        await page.close()
        
        return content

    async def _get_soup(
        self, url: str, *args, **kwargs
    ) -> BeautifulSoup:
        content = await self._get_html(url, *args, **kwargs)
        
        return BeautifulSoup(content, "html.parser")

    def _build_url(self, partial_url: str) -> str:
        return self._base_url + partial_url
        
    def _get_text(
        self,
        element: Tag,
        parsed_url: ParseResult,
        template: str = "[{}]({})"
    ):
        if isinstance(element, Tag) and element.name == "a":
            tag_name = element.text
            tag_href = element["href"]
            
            parsed_href = urlparse(tag_href)
            if not parsed_href.netloc:
                raw_url = parsed_url._replace(params="", fragment="").geturl()
                tag_href = urljoin(raw_url, tag_href)
                
            
            text = template.format(tag_name, tag_href)
        else:
            text = element.text
            
        return text
    
    async def get_documentation(
        self,
        url: str
    ) -> Documentation:
        with Timer() as timer:
            strainer = SoupStrainer("section")
            
            parsed_url = urlparse(url)
            name = parsed_url.fragment
            
            content = await self._get_html(url)
            soup = BeautifulSoup(content, "lxml", parse_only=strainer)
            
            element = soup.find("dt", id=name)
            
            full_name = element.text
            documentation = element.parent.find("dd")
            description = []
            examples = []
            
            field_list = documentation.find("dl", class_="field-list simple")
            fields = {}
            for field in field_list.findChildren("dt"):
                field: Tag = field
                
                key = field.text
                value: Tag = [x for x in field.next_siblings if isinstance(x, Tag)][0] \
                    .find("p")
                
                elements = []
                for element in value.contents:
                    text = self._get_text(
                        element,
                        parsed_url,
                        template="[`{}`]({})"
                    )
                    
                    elements.append(text)
                    
                fields[key] = "".join(elements)
            
            for child in documentation.find_all("p", recursive=False):
                child: Tag = child
                
                # this is to stop getting the description after examples,
                # because those are too large, no idea if this will actually works
                if child.attrs.get("class"):
                    break
                
                elements = []
                for element in child.contents:
                    text = self._get_text(element, parsed_url)
                    
                    elements.append(text)
                    
                description.append("".join(elements))
                
            for child in documentation.find_all("div", class_="highlight"):
                examples.append(
                    child.find("pre") \
                        .text
                )
                
                
            if version_modified := documentation.find("span", class_="versionmodified"):
                description.append(f"*{version_modified.text}*")
                    
            description = "\n\n".join(description) \
                .replace("Example:", "") \
                .strip()
            
            if full_name.endswith("¶"):
                full_name = full_name[:-1]
            
        return Documentation(
            full_name=full_name,
            name=name,
            description=description,
            examples=examples,
            url=url,
            fields=fields,
            time=timer.time
        )
        
    @executor()
    def _get_search(self, query: str, limit: Optional[int] = None) -> set[str, str, bool]:
        if not hasattr(self, "_inv") or self._inv is None:
            self._inv = Inventory(url=self._inv_url)
            
        def get_name(obj: DataObjStr) -> str:
            name = obj.name if obj.dispname == "-" else obj.dispname
            if obj.domain == "std":
                name = f"{obj.role}: {name}"
            
            if self._inv.project == "discord.py":
                name = (name
                        .replace("discord.ext.commands.", "")
                        .replace("discord.", ""))
            
            return name
        
        def build_uri(obj: DataObjStr) -> str:
            if obj.domain == "std":
                return urljoin(self._base_url, obj.uri)
            
            parsed_uri = urlparse(obj.uri)
            new_uri = parsed_uri._replace(params="", fragment=obj.name)
            
            return urljoin(self._base_url, new_uri.geturl())
            
        matches = [(item, fuzz.partial_ratio(query, item.name)) for item in self._inv.objects]
        sorted_matches = sorted(matches, key=lambda x: x[1], reverse=True)[:limit]
        
        return [(get_name(item), build_uri(item), bool(item.domain == "std")) for item, _ in sorted_matches]
            
    
    async def search(
        self,
        query: str,
        limit: int = None
    ) -> SearchResults:
        with Timer() as timer:
            results = await self._get_search(
                query=query, limit=limit
            )
        
        return SearchResults(
            results=results,
            query_time=timer.time
        )
    
async def setup(bot):
    pass
