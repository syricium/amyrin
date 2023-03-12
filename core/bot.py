import sys
import traceback
import discord
import yaml
import os
from discord.ext import commands
from aiohttp import ClientSession
from pathlib import Path
import logging
from git.repo import Repo

config = yaml.load(open("config.yml"), Loader=yaml.Loader)

if config["version"] not in ("development", "production"):
    raise TypeError('version key in config needs to be either "development" or "production"')

class Amyrin(commands.AutoShardedBot):
    session: ClientSession
    logger: logging.Logger
    
    def __init__(self) -> None:
        super().__init__(
            command_prefix="a!",
            intents=discord.Intents.all(),
            allowed_mentions=discord.AllowedMentions.none(),
            description=(
                "cool private bot by syrice#7165"
            )
        )
        
        self.owner_ids = {424548154403323934}
        
        self.config = config
        self.git = Repo()
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if self.is_development else logging.INFO)        
        
    @property
    def is_development(self) -> None:
        return self.config["version"] == "development"
        
    def setup_logger(self) -> None:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG if self.development else logging.INFO)
        
        handler = logging.StreamHandler(sys.stdout)
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(
            "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        self.logger = logger
        
    async def on_ready(self) -> None:
        self.logger.info("Ready")
        
    async def on_connect(self) -> None:
        self.logger.info("Connected")
        
    async def load_extensions(self) -> None:
        path = Path("exts")
        
        for file in path.glob("*.py"):
            name = str(file).replace(os.sep, ".")[:-3]
            try:
                await self.load_extension(name)
            except Exception as exc:
                self.logger.error(f'The following exception occured while trying to load extension "{name}":')
                traceback.print_exc()
            
    async def setup_hook(self) -> None:
        discord.utils.setup_logging()
        
        await self.load_extensions()