import asyncio
import os
import re
import traceback
from typing import List

import discord
from core.bot import onyx
from discord.ext import commands
from modules.util.views.pull import PullView

from . import *


class Developer(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: onyx = bot
        self.module_regex = re.compile(r"bot\/(?P<module>modules\/.+\.py)")

    def reload_modules(self, source: str):
        if "already up to date." in source.lower():
            raise TypeError("Already up to date")
        results: List[str] = self.module_regex.findall(source)
        reloaded = {}
        for result in results:
            result = result.replace(os.sep, ".")
            try:
                self.bot.reload_extension(result)
            except Exception as exc:
                error = traceback.format_exception(type(exc), exc, exc.__traceback__)
                reloaded[result] = error
            else:
                reloaded[result] = None

        return reloaded

    async def shell(self, code: str, wait: bool = True):
        proc = await asyncio.subprocess.create_subprocess_shell(
            code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        if wait:
            await proc.wait()
        return tuple(i.decode() for i in await proc.communicate())

    @command(
        commands.command,
        examples=["{prefix}pull"],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
    )
    @commands.is_owner()
    async def pull(self, ctx):
        result = await self.shell("git pull")

        if (
            isinstance(result[1], str)
            and "please commit your changes or stash them before you merge."
            in result[1].lower()
        ):
            await self.shell("git stash")
            result = await self.shell("git pull")

        output = "\n".join(i.strip() for i in result)

        if output.lower() == "already up to date.":
            return await ctx.send("Already up to date")

        modules = self.module_regex.findall(output)
        reloaded = "\n".join(modules)
        description = f"```sh\n{output}```"
        if reloaded:
            description += f"\n\nChanged Modules:\n{reloaded}"

        embed = discord.Embed(description=description)
        await ctx.send(embed=embed, view=PullView(ctx, output, modules=modules))


async def setup(bot):
    await bot.add_cog(Developer(bot))
