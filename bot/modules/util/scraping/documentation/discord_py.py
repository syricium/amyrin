import ast
import asyncio
import inspect
import os
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TypedDict
from urllib.parse import ParseResult, urljoin, urlparse

import discord
from bs4 import BeautifulSoup, SoupStrainer, Tag
from fuzzywuzzy import fuzz
from humanfriendly import format_timespan
import humanfriendly
from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError
from playwright.async_api._generated import Browser
from sphobjinv import DataObjStr, Inventory

from modules.util.executor import executor
from modules.util.timer import Timer


class Response:
    def __bool__(self):
        return any(
            getattr(self, str(attr)) for attr in dir(self) if not attr.startswith("_")
        )


@dataclass(frozen=True)
class RTFSItem:
    name: str
    url: str


class RTFSResults:
    def __init__(self, results: set[str, str, bool]) -> None:
        self.results: List[RTFSItem] = results

    def __list__(self):
        return self.results

    def to_embed(self, color: Optional[int] = None):
        description = "\n".join(
            f"[`{result.name}`]({result.url})" for result in self.results
        )

        embed = discord.Embed(description=description, color=color)

        return embed


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
        description = f"```py\n{self.full_name}\n```\n{self.description}".strip()

        embed = discord.Embed(
            title=self.name, url=self.url, description=description, color=color
        )
        embed.set_author(
            name="discord.py documentation",
            icon_url="https://cdn.discordapp.com/attachments/381963689470984203/1068553303908155442/sW87z7N.png",
        )

        for name, field in self.fields.items():
            embed.add_field(name=name, value=field, inline=False)
            
        time = humanfriendly.format_timespan(self.time)
        embed.set_footer(text=f"Scraped in {time}")

        return embed


class SearchResults:
    def __init__(self, results: set[str, str, bool], query_time: int) -> None:
        self.results = results
        self.query_time = query_time

    def __list__(self):
        return self.results

    def to_embed(self, color: Optional[int] = None):
        description = "\n".join(f"[`{name}`]({url})" for name, url, _ in self.results)

        embed = discord.Embed(description=description, color=color)

        query_time = format_timespan(self.query_time)
        embed.set_footer(text=f"Fetched in {query_time}")

        return embed


class DocScraper:
    def __init__(self, browser: Optional[Browser] = None):
        self._browser = browser

        self._base_url = "https://discordpy.readthedocs.io/en/stable/"
        self._inv_url = urljoin(self._base_url, "objects.inv")
        self._inv: Inventory = None

        self._rtfs_commit: Optional[str] = None
        self._rtfs_cache: Optional[
            List[
                TypedDict(
                    "rtfs",
                    {
                        "name": str,
                        "file": str,
                        "position": set[int, int],  # start and end position
                    },
                )
            ]
        ] = {}

        self._rtfs_repo = (
            "discord.py",
            "https://github.com/Rapptz/discord.py",
            "discord",
        )

    async def _shell(self, command: str) -> str:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=60,
        )

        stdout, stderr = await proc.communicate()

        return stdout.decode(), stderr.decode()

    def _rtfs_index_file(self, filepath: os.PathLike) -> None:
        repo, _, _ = self._rtfs_repo

        def append_item(name: str, file: os.PathLike, position: set[int, int]):
            repos_path = os.path.join(os.getcwd(), "rtfs_repos")
            repo_path = os.path.join(repos_path, repo)
            filepath = file[len(repo_path) :]
            path = filepath.split("/")[:-1]

            if "" in path:
                path.remove("")

            name = ".".join(path) + "." + name

            name = name.replace("discord.ext.", "").replace("discord.", "")

            data = {"name": name, "file": filepath, "position": position}
            if not self._rtfs_cache:
                self._rtfs_cache = []
            self._rtfs_cache.append(data)

        with open(filepath) as f:
            code = f.read()

        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("_"):
                    continue

                class_position = (node.lineno, node.end_lineno)
                append_item(node.name, filepath, class_position)

                for child in node.body:
                    if (
                        not isinstance(child, ast.AsyncFunctionDef)
                        and not isinstance(child, ast.FunctionDef)
                        or child.name.startswith("_")
                    ):
                        continue

                    child_position = (child.lineno, child.end_lineno)

                    name = f"{node.name}.{child.name}"
                    append_item(name, filepath, child_position)

    @executor()
    def _rtfs_index_directory(self, path: os.PathLike):
        for root, _, files in os.walk(path):
            for file in files:
                filepath = os.path.join(root, file)

                if not file.endswith(".py"):
                    continue

                if file.startswith("_"):
                    continue

                self._rtfs_index_file(filepath)

    async def _build_rtfs_cache(self):
        repo, url, dir_name = self._rtfs_repo

        rtfs_repos = os.path.join(os.getcwd(), "rtfs_repos")
        rtfs_repo = os.path.join(rtfs_repos, repo)
        path = os.path.join(rtfs_repo, dir_name)

        if not os.path.isdir(path):
            await self._shell(f"git clone {url} {rtfs_repo}")

        await self._rtfs_index_directory(path)

    async def rtfs_search(
        self,
        query: str,
        limit: Optional[int] = None,
        updater: Callable = None,
    ) -> List[RTFSItem]:
        async def update(message: str):
            if updater is None:
                return

            if inspect.iscoroutinefunction(updater):
                return await updater(message)
            return updater(message)

        if self._rtfs_cache == {}:
            await update("Building cache")
            await self._build_rtfs_cache()

        results = []

        _, repo_url, repo_path = self._rtfs_repo
        full_repo_url = repo_url + f"/tree/master"

        for item in self._rtfs_cache:
            name = item.get("name")
            file = item.get("file")
            start, end = item.get("position")

            file_url = urlparse(full_repo_url + file)._replace(
                fragment=f"L{start}-L{end}"
            )

            item = RTFSItem(name, file_url.geturl())
            results.append(item)

        matches = sorted(
            results, key=lambda x: fuzz.ratio(query, x.name), reverse=True
        )[:limit]

        return RTFSResults(matches)

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

    async def _get_soup(self, url: str, *args, **kwargs) -> BeautifulSoup:
        content = await self._get_html(url, *args, **kwargs)

        return BeautifulSoup(content, "html.parser")

    def _build_url(self, partial_url: str) -> str:
        return self._base_url + partial_url

    def _get_text(
        self, element: Tag, parsed_url: ParseResult, template: str = "[{}]({})"
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

    async def get_documentation(self, url: str) -> Documentation:
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
                value: Tag = [x for x in field.next_siblings if isinstance(x, Tag)][
                    0
                ].find("p")

                elements = []
                for element in value.contents:
                    text = self._get_text(element, parsed_url, template="[`{}`]({})")

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
                examples.append(child.find("pre").text)

            if version_modified := documentation.find("span", class_="versionmodified"):
                description.append(f"*{version_modified.text}*")

            description = "\n\n".join(description).replace("Example:", "").strip()

            if full_name.endswith("¶"):
                full_name = full_name[:-1]

        return Documentation(
            full_name=full_name,
            name=name,
            description=description,
            examples=examples,
            url=url,
            fields=fields,
            time=timer.time,
        )

    @executor()
    def _get_search(
        self, query: str
    ) -> set[str, str, bool]:
        if not hasattr(self, "_inv") or self._inv is None:
            self._inv = Inventory(url=self._inv_url)

        def get_name(obj: DataObjStr) -> str:
            name = obj.name if obj.dispname == "-" else obj.dispname
            if obj.domain == "std":
                name = f"{obj.role}: {name}"

            if self._inv.project == "discord.py":
                name = name.replace("discord.ext.commands.", "").replace("discord.", "")

            return name

        def build_uri(obj: DataObjStr) -> str:
            location = obj.uri
            
            if location.endswith('$'):
                location = location[:-1] + obj.name
                
            return urljoin(self._base_url, obj.uri)

        query = re.sub(r'^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)', r'\1', query)

        matches = sorted(
            self._inv.objects,
            key=lambda x: fuzz.ratio(query, x.name),
            reverse=True
        )

        return [
            (get_name(item), build_uri(item), bool(item.domain == "std"))
            for item in matches
        ]

    async def search(self, query: str, limit: int = None, exclude_std: bool = False) -> SearchResults:
        with Timer() as timer:
            results = await self._get_search(query=query)

        if exclude_std:
            results = [result for result in results if not result[2]]

        return SearchResults(results=results[:limit], query_time=timer.time)


async def setup(bot):
    pass
