import ast
import asyncio
from copy import copy
import inspect
import os
import re
import sys
import textwrap
import traceback

import discord
import import_expression
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from jishaku.repl import KeywordTransformer

from core.bot import onyx
from modules.views.pull import PullView

from . import *

class Updater:
    def __init__(self, context: commands.Context):
        super().__init__()
        self.ctx = context
        self.message = context.message
        self.running = True
        self.loop = asyncio.get_running_loop()
        self.task = None

    async def queue(self, delay: float, coro, *args, **kwargs):
        await asyncio.sleep(delay)
        if not self.running:
            return
        return await coro(*args, **kwargs)

    async def __aenter__(self):
        self.task = self.loop.create_task(self.queue(1, self.message.add_reaction, "▶"))
        return self

    async def __aexit__(self, _type, val, tb):
        if self.task:
            self.task.cancel()
        self.running = False
        await self.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")


class Developer(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot):
        super().__init__()
        self.bot: onyx = bot
        self.module_regex = re.compile(r"bot\/(?P<module>modules\/.+)\.py")

    async def shell(self, code: str, wait: bool = True):
        proc = await asyncio.subprocess.create_subprocess_shell(
            code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        if wait:
            await proc.wait()
        return tuple(i.decode() for i in await proc.communicate())

    def parse_code(self, code: str) -> ast.Module:
        code = f"""async def func():
    from importlib import import_module as {import_expression.constants.IMPORTER}
{textwrap.indent(code, '    ')}"""

        code: ast.Module = import_expression.parse(code)
        ast.fix_missing_locations(code)
        block: ast.AsyncFunctionDef = code.body[-1]
        KeywordTransformer().generic_visit(block)

        last = block.body[-1]

        if not isinstance(last, ast.Expr):
            return code

        if not isinstance(last.value, ast.Yield):
            assign = ast.Yield(last.value)
            ast.copy_location(assign, last)
            _yield = ast.Expr(assign)
            ast.copy_location(_yield, last)
            block.body[-1] = _yield

        return code

    async def send(self, ctx: commands.Context, result):
        if isinstance(result, list):
            if all(isinstance(i, discord.Embed) for i in result):
                return await ctx.send(embeds=result)
            if all(isinstance(i, discord.Attachment) for i in result):
                return await ctx.send(files=[await i.to_file() for i in result])
            if all(isinstance(i, discord.File) for i in result):
                return await ctx.send(
                    files=result,
                )
            return await ctx.send(str(result))
        if isinstance(result, discord.Embed):
            return await ctx.send(embed=result)
        if isinstance(result, discord.Attachment):
            return await ctx.send(file=await result.to_file())
        if isinstance(result, discord.File):
            return await ctx.send(file=result)
        if isinstance(result, str):
            return await ctx.send(f"```py\n{str(result).replace('``', '`​`')}```")
        if isinstance(result, discord.ui.View):
            return await ctx.send(view=result)
        if result is None:
            return

        return await ctx.send(str(result))

    @command(
        commands.command,
        name="eval",
        aliases=["e"],
        examples=['{prefix}eval print("hot gay sex")'],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
    )
    @commands.is_owner()
    async def _eval(self, ctx, *, code: codeblock_converter):
        code = code.content

        env = {
            "author": ctx.message.author,
            "bot": self.bot,
            "channel": ctx.message.channel,
            "find": discord.utils.find,
            "ctx": ctx,
            "get": discord.utils.get,
            "guild": ctx.message.guild,
            "message": ctx.message,
            "msg": ctx.message,
            "src": inspect.getsource,
            "srcls": inspect.getsourcelines,
            "commands": commands,
            "rf": None
            if ctx.message.reference is None
            else ctx.message.reference.resolved,
        }

        for k, v in sys.modules.items():
            env[k] = v

        """ Code Parsing """

        try:
            res = self.parse_code(code)
            code = compile(res, filename="<eval>", mode="exec")
        except Exception as exc:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            result = f"```py\n{tb}```"
            return await ctx.send(result)

        """ Evaluating """
        result = None
        async with Updater(ctx):
            try:
                exec(code, env)
                func = env.get("func")
                if inspect.isasyncgenfunction(func):
                    async for i in func():
                        if i is not None:
                            await self.send(ctx, i)
                else:
                    result = await eval("func()", env)
            except Exception as exc:
                result = "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )

        if result is not None and len(str(result.strip())) > 0:
            await self.send(ctx, result)
            
    @command(
        commands.command,
        name="as",
        aliases=["su"],
        examples=["{prefix}as flowerpad#0001 help"],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
    )
    @commands.is_owner()
    async def _as(self, ctx, user: discord.Member, *, command: str):
        msg = copy(ctx.message)
        msg.content = f"{self.bot.command_prefix}{command}"
        msg.author = user
        await self.bot.process_commands(msg)

    @command(
        commands.command,
        aliases=["pull"],
        examples=["{prefix}update"],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
    )
    @commands.is_owner()
    async def update(self, ctx: commands.Context):
        async with ctx.typing():
            result = await self.shell("git pull --force --stat")

        output = "\n".join(i.strip() for i in result)

        if output.lower() == "already up to date.":
            return await ctx.send("Already up to date")

        modules = [x.replace(os.sep, ".") for x in self.module_regex.findall(output)]
        reloaded = "\n".join(modules)
        description = f"```sh\n{output}```"
        if reloaded:
            description += f"\n\nChanged Modules:\n{reloaded}"

        embed = discord.Embed(description=description, color=self.bot.color)
        await ctx.send(embed=embed, view=PullView(ctx, modules=modules))


async def setup(bot):
    await bot.add_cog(Developer(bot))
