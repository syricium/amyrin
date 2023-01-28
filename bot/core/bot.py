import importlib
import logging
import logging.handlers
import os
import traceback
from datetime import datetime
from textwrap import indent
from typing import Literal, Optional

import aiohttp
import discord
import mystbin
from core.context import Context
from discord.ext import commands, ipc
from discord.ext.commands import Greedy
from dotenv import load_dotenv
from modules.util.documentation.parser import DocParser
from playwright.async_api import async_playwright
from playwright.async_api._generated import Browser

load_dotenv()

debug = (
    True if not os.getenv("DEBUG") else False if os.getenv("DEBUG") == "false" else True
)


class onyx(commands.Bot):
    def __init__(self, *args, **kwargs) -> commands.Bot:
        super().__init__(*args, **kwargs)
        self.uptime = datetime.utcnow()
        self.myst = mystbin.Client(token=os.getenv("MYSTBIN_API"))

        self.debug = debug

        self.owner_id = 424548154403323934
        self.owner_ids = (424548154403323934,)
        self.session = (
            None  # aiohttp.ClientSession instance, later defined in self.setup_hook
        )
        self.logger = None  # logging.Logger instance, later defined in self.startup
        self.expr_states = {}  # expr.py states, in use in modules.util.views.calculator

        self.playwright = None  # playwright instance, later defined in self.setup_hook
        self.browser: Browser = (
            None  # playwright chromium instance, later defined in self.setup_hook
        )
        self.docparser: DocParser = None  # DocParser instance, later defined in modules.util.documentation.parser

        self.ipc = ipc.Server(
            self, host="0.0.0.0", secret_key=os.getenv("IPC_SECRET_KEY")
        )

        self.color = (
            0x2F3136  # color used for embeds and whereever else it would be appropiate
        )

    @property
    def owner(self) -> discord.User:
        return self.get_user(self.owner_id)

    async def is_owner(self, user: discord.User) -> bool:
        return user.id == self.owner_id or user.id in self.owner_ids

    def sync_is_owner(self, user: discord.User) -> bool:
        return user.id == self.owner_id or user.id in self.owner_ids

    async def on_connect(self) -> None:
        self.logger.info("Connected to discord gateway")

    async def setup_hook(self) -> None:
        discord.utils.setup_logging()

        self.session = aiohttp.ClientSession()

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=not self.debug)
        self.bcontext = await self.browser.new_context()

        rootdir = os.getcwd()
        direc = os.path.join(rootdir, "modules")
        for root, _, files in os.walk(direc):
            prefix = root[len(rootdir) + 1 :].replace("\\", "/").replace("/", ".")

            parent = prefix.split(".")[-1]  # get the parent of the file
            if parent == "__pycache__":  # ignore pycache folders
                continue

            for file in files:  # iterate through all files in a subdirectory
                if not file.endswith(".py"):
                    continue
                fn = file[:-3]
                name = f"{prefix}.{fn}"
                try:
                    imp = importlib.import_module(name)
                except Exception as exc:
                    exc = "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    )

                    self.logger.error(f"Error occured loading module {name}:\n{exc}")
                else:
                    if hasattr(imp, "setup"):
                        try:
                            await self.load_extension(name)
                        except Exception as exc:
                            exc = "".join(
                                traceback.format_exception(
                                    type(exc), exc, exc.__traceback__
                                )
                            )

                            self.logger.error(
                                f"Error occured loading module {name}:\n{exc}"
                            )
                        else:
                            self.logger.info(f"Succesfully loaded module {name}")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if self.debug and not await self.is_owner(message.author):
            return

        await self.process_commands(message)

    async def on_ready(self) -> None:
        info = {
            "Statistics": {"Users": len(self.users), "Guilds": len(self.guilds)},
            "Modules": {
                "Commands": len(list(self.walk_commands())),
                "Events": len(self._listeners),
            },
        }

        self.logger.info(f"Logged in as {self.user}")

        for name, data in info.items():
            self.logger.info(name)
            for k, v in data.items():
                if k == list(data.keys())[-1]:
                    text = f"└─ {k}: {v}"
                else:
                    text = f"├─ {k}: {v}"
                self.logger.info(indent(text, "  "))

    async def close(self) -> None:
        tasks = {"bot": super().close, "session": self.session.close}

        for task, func in tasks.items():
            try:
                await func()
            except Exception as exc:
                exc = "\n".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )

                self.logger.error(f"Error occured closing {task} ({func}):\n{exc}")

        exit()

    async def get_context(self, message, *, cls=Context) -> Context:
        return await super().get_context(message, cls=cls)

    def setup_discord_logger(self) -> None:
        logger = logging.getLogger("discord")
        logger.setLevel(logging.INFO)
        logging.getLogger("discord.http").setLevel(logging.INFO)

        handler = logging.handlers.RotatingFileHandler(
            filename="logs/discord.log",
            encoding="utf-8",
            maxBytes=32 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        )
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(
            "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def setup_bot_logger(self) -> None:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler = logging.handlers.RotatingFileHandler(
            filename="logs/bot.log",
            encoding="utf-8",
            maxBytes=32 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        )
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(
            "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        self.logger = logger

    def setup_loggers(self) -> None:
        self.setup_discord_logger()
        self.setup_bot_logger()

    def startup(self) -> None:
        self.setup_loggers()

        token_key = "DISCORD_TOKEN"
        token = os.getenv(token_key)

        return self.run(token, log_handler=None)


intents = discord.Intents.all()

bot = onyx(
    command_prefix=commands.when_mentioned if not debug else "onyc",
    allowed_mentions=discord.AllowedMentions.none(),
    intents=intents,
    strip_after_prefix=True,
    case_insensitive=True,
)

# stole from https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f
@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(
    ctx: Context,
    guilds: Greedy[discord.Object],
    spec: Optional[Literal["~", "*", "^"]] = None,
) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")
