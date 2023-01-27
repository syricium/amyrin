from core.bot import onyx
from discord.ext import commands

from . import *
from modules.util.scraping.documentation.discord_py import DocScraper


class Documentation(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: onyx = bot
        
        self.scrapers = {
            "discord.py": DocScraper(self.bot.bcontext)
        }

    @command(
        commands.hybrid_group,
        aliases=[
            "docs", "rtfm", "rtfd"
        ],
        description="Search the documentation of a programming language and/or module",
        examples=["{prefix}rtfm commands.bot"]
    )
    async def documentation(self, ctx: commands.Context, query: str = commands.param(description="The query you want to search for in the default (discord.py) documentation")):
        await self.discord_py(ctx, query)
        
    @command(
        documentation.command,
        name="latest",
        aliases=[
            "dpy", "d.py"
        ],
        description="Search the documentation of discord.py",
        examples=["{prefix}rtfm dpy commands.bot"]
    )
    async def discord_py(self, ctx: commands.Context, query: str = commands.param(description="The query you want to search for in the discord.py documentation")):
        scraper = self.scrapers["discord.py"]
        
        results = await scraper.search(query, limit=8)
        await ctx.reply(
            embed=results.to_embed(color=self.bot.color)
        )


async def setup(bot):
    await bot.add_cog(Documentation(bot))
