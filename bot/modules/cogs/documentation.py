import discord
from discord.ext import commands

from core.bot import onyx
from modules.util.scraping.documentation.discord_py import \
    DocScraper as DiscordScraper
from modules.views.docs import DocView

from . import *


class Documentation(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: onyx = bot

        self.scrapers = {"discord.py": DiscordScraper(self.bot.bcontext)}

    @command(
        commands.hybrid_group,
        aliases=["rtfd"],
        description="Search the documentation of a module",
        examples=["{prefix}rtfm commands.bot"],
    )
    async def rtfm(
        self,
        ctx: commands.Context,
        query: str = commands.param(
            description="The query you want to search for in the default (discord.py) documentation"
        ),
    ):
        await self.rtfm_discord_py(ctx, query)


    @command(
        rtfm.command,
        name="latest",
        aliases=["dpy", "d.py"],
        description="Search the documentation of discord.py",
        examples=["{prefix}rtfm dpy commands.bot"],
    )
    async def rtfm_discord_py(
        self,
        ctx: commands.Context,
        query: str = commands.param(
            description="The query you want to search for in the discord.py documentation"
        ),
    ):
        if ctx.interaction:
            await ctx.interaction.defer()
        
        scraper = self.scrapers["discord.py"]

        results = await scraper.search(query, limit=8)
        await ctx.reply(embed=results.to_embed(color=self.bot.color))

    @command(
        commands.hybrid_group,
        description="Search the source code of a module",
        examples=["{prefix}rtfm commands.bot"],
    )
    async def rtfs(
        self,
        ctx: commands.Context,
        query: str = commands.param(
            description="The query you want to search for in the default (discord.py) source code"
        ),
    ):
        await self.rtfs_discord_py(ctx, query)

    @command(
        rtfs.command,
        name="latest",
        aliases=["dpy", "d.py"],
        description="Search the source code of discord.py",
        examples=["{prefix}rtfm dpy commands.bot"],
    )
    async def rtfs_discord_py(
        self,
        ctx: commands.Context,
        query: str = commands.param(
            description="The function or class you want to search for in the discord.py source code"
        ),
    ):
        if ctx.interaction:
            await ctx.interaction.defer()
        
        scraper = self.scrapers["discord.py"]

        global message
        ctx._message: discord.Message = None

        async def update(text: str):
            if ctx._message:
                return await ctx._message.edit(content=text)
            else:
                ctx._message = await ctx.reply(text)

        results = await scraper.rtfs_search(query, limit=8, updater=update)
        
        if ctx._message:
            func = ctx._message.edit
        else:
            func = ctx.send
        
        await func(
            content=None, embed=results.to_embed(color=self.bot.color)
        )
        
    @command(
        commands.hybrid_group,
        aliases=["docs"],
        description="Get documentation of a module",
        examples=["{prefix}rtfm commands.bot"],
    )
    async def documentation(
        self,
        ctx: commands.Context,
        query: str = commands.param(
            description="The query you want to search for in the default (discord.py) documentation"
        ),
    ):
        await self.docs_discord_py(ctx, query)


    @command(
        documentation.command,
        name="latest",
        aliases=["dpy", "d.py"],
        description="Get documentation of a discord.py module",
        examples=["{prefix}docs dpy commands.bot"],
    )
    async def docs_discord_py(
        self,
        ctx: commands.Context,
        query: str = commands.param(
            description="The query you want to search for in the discord.py documentation"
        ),
    ):
        if ctx.interaction:
            await ctx.interaction.defer()
            
        scraper = self.scrapers["discord.py"]

        view = DocView(ctx, scraper, query, self.bot.color)
        await view.start()


async def setup(bot):
    await bot.add_cog(Documentation(bot))
