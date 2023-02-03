import asyncio
import traceback
from typing import Callable, Dict, Literal
import discord
from discord.ext import commands

from core.bot import onyx
from modules.views.docs import DocView

from . import *
from modules.util.scraping.documentation.discord_py import DocScraper as DiscordScraper
from modules.util.converters import format_list

class Documentation(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: onyx = bot
        
        self.scrapers = {
            "discord.py": DiscordScraper(self.bot.bcontext, bot)
        }
        recache: commands.Group = self.recache
        recache.add_check(self._recache_check)
        for command in recache.walk_commands():
            command.add_check(self._recache_check(command.name))
        
    def _recache_check(
        self,
        command: Optional[Literal["rtfm", "rtfs", "documentation"]] = None
    ):
        async def func(ctx):
            async def task_running(message: str):
                msg = await ctx.send(message)
                
                reactions = ["\N{WHITE HEAVY CHECK MARK}", "\N{CROSS MARK}"]
                
                for reaction in reactions:
                    await msg.add_reaction(reaction)
                
                def check(reaction: discord.Reaction, user: discord.User):
                    return reaction.message == msg and user == ctx.author
                
                while True:
                    try:
                        reaction, user = await self.bot.wait_for(
                            "reaction_add",
                            timeout=30,
                            check=check
                        )
                    except asyncio.TimeoutError:
                        await msg.edit(content="Confirmation timed out.")
                        for reaction in reactions:
                            try:
                                await msg.remove_reaction(reaction, ctx.me)
                            except Exception:
                                pass
                        break
                    else:
                        print(reaction.emoji == reactions[0])
            
            scraper = self.scrapers["discord.py"]
        
            cache_map = {
                "documentation": (scraper._cache_all_documentations, scraper.strgcls._docs_caching_task),
                "rtfs": (scraper._build_rtfs_cache, scraper.strgcls._rtfs_caching_task),
                "rtfm": (scraper._build_rtfm_cache, scraper.strgcls._rtfm_caching_task)
            }
            
            if command is None:
                running = [name for name, (func, task) in cache_map.items() if not task.done()]
                if len(running) == 1:
                    await task_running(f"There {running[0]} startup caching task is not yet done, do you want to cancel it?")
                elif running:
                    all_running = format_list(running, seperator="and", brackets="`")
                    await task_running(f"The {all_running} startup caching tasks are not yet done, do you want to cancel it?")
            
            func, task = cache_map[command]
            task: asyncio.Task
            
            if not task.done():
                await task_running(f"The {command} startup caching task is not yet done, do you want to cancel it?")
            
            return True
        
        return func
        
    def _recache_updater(self, ctx: commands.Context):
        self._message: discord.Message = None
        self._prev_name = None
        async def updater(message: str, name: str):
            if not self._prev_name:
                self._prev_name = name
                
            if self._message:
                content = self._message.content
                if name != self._prev_name:
                    content += "\n"
                content += "\n" + message
                self._message = await self._message.edit(content=content)
                self._prev_name = name
            else:
                self._message = await ctx.send(message)
            return self._message
            
        return updater
    
    @command(
        commands.group,
        aliases=["rc"],
        description="Recache cached items",
        examples=["{prefix}recache"],
        hidden=True,
        invoke_without_command=True
    )
    @commands.is_owner()
    async def recache(self, ctx: commands.Context):
        scraper = self.scrapers["discord.py"]
        updater = self._recache_updater(ctx)
        
        funcs = {
            "RTFM": (scraper._build_rtfm_cache, scraper.strgcls._rtfm_caching_task),
            "RTFS": (scraper._build_rtfs_cache, scraper.strgcls._rtfs_caching_task),
            "Documentation": (scraper._cache_all_documentations, scraper.strgcls._docs_caching_task)
        }
        
        for name, (func, task) in funcs.items():
            if not task.done():
                await updater(
                    f"Skipped caching {name.lower()} due to the startup caching task not being done",
                    "documentation"
                )
                continue
            
            try:
                await func(recache=True, updater=updater)
            except Exception as exc:
                error = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                await ctx.send(f"{name} caching function failed with the following exception:\n```py\n{error}\n```")
                
        await updater("Done recaching all caches", "done")
        
    @command(
        recache.command,
        name="documentation",
        aliases=["docs", "d"],
        description="Recache documentation manuals",
        examples=["{prefix}recache documentation"],
        hidden=True
    )
    @commands.is_owner()
    async def recache_docs(self, ctx: commands.Context):
        scraper = self.scrapers["discord.py"]
        
        updater = self._recache_updater(ctx)        
        try:
            await scraper._cache_all_documentations(recache=True, updater=updater)
        except Exception as exc:
            fmt_exc = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            return await ctx.send(
                f"Caching function failed with the following exception:\n```py\n{fmt_exc}\n```"
            )
            
    @command(
        recache.command,
        name="rtfd",
        description="Recache rtfd cache",
        examples=["{prefix}recache rtfd"],
        hidden=True
    )
    @commands.is_owner()
    async def recache_rtfd(self, ctx: commands.Context):
        scraper = self.scrapers["discord.py"]
        
        updater = self._recache_updater(ctx)        
        try:
            await scraper._build_rtfs_cache(recache=True, updater=updater)
        except Exception as exc:
            fmt_exc = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            return await ctx.send(
                f"Caching function failed with the following exception:\n```py\n{fmt_exc}\n```"
            )
            
    @command(
        recache.command,
        name="rtfm",
        description="Recache rtfm cache",
        examples=["{prefix}recache rtfm"],
        hidden=True
    )
    @commands.is_owner()
    async def recache_rtfm(self, ctx: commands.Context):
        scraper = self.scrapers["discord.py"]
        
        updater = self._recache_updater(ctx)        
        try:
            await scraper._build_rtfm_cache(recache=True, updater=updater)
        except Exception as exc:
            fmt_exc = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            return await ctx.send(
                f"Caching function failed with the following exception:\n```py\n{fmt_exc}\n```"
            )

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
            await ctx.interaction.response.defer()
        
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
            await ctx.interaction.response.defer()
        
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
            await ctx.interaction.response.defer()
            
        scraper = self.scrapers["discord.py"]

        view = DocView(ctx, scraper, query, self.bot.color)
        await view.start()


async def setup(bot):
    await bot.add_cog(Documentation(bot))
