import ast
import asyncio
import inspect
import json
import os
import random
import re
import string
import sys
import textwrap
import traceback
from copy import copy
from datetime import datetime
from typing import AsyncGenerator, Dict

import discord
import import_expression
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from jishaku.repl import KeywordTransformer

from core.bot import amyrin
from modules.views.paginator import WrapList, paginate
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
        self.bot: amyrin = bot
        self.module_regex = re.compile(r"bot\/(?P<module>modules\/.+)\.py")
    
    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)

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
        commands.group,
        name="eval",
        aliases=["e"],
        examples=['{prefix}eval print("hot gay sex")'],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
        invoke_without_command=True,
    )
    async def _eval(self, ctx, *, code: codeblock_converter):
        def gen_eval_name():
            while True:
                name = "".join(random.choices(string.ascii_lowercase, k=6))
                if name not in self.bot.eval_tasks.keys():
                    return name

        async def handle_async_generator(func: AsyncGenerator):
            async for i in func():
                if i is not None:
                    await self.send(ctx, i)

        code = code.content
        
        # omg console.log in python 😱😰😰
        class console:
            @classmethod
            def log(cls, *args, **kwargs):
                print(*args, **kwargs)

        ref = None \
            if ctx.message.reference is None \
            else ctx.message.reference.resolved,
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
            "console": console,
            "ref": ref,
            "rf": ref
        }

        env.update(sys.modules.items())

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
                    task = asyncio.create_task(handle_async_generator(func))
                else:
                    task = asyncio.create_task(func())
                eval_name = gen_eval_name()
                self.bot.eval_tasks[eval_name] = (task, datetime.utcnow())
                task.add_done_callback(
                    lambda result: self.bot.eval_tasks.pop(eval_name, None)
                )
                await task
            except Exception as exc:
                result = "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )

        if result is not None and len(str(result.strip())) > 0:
            await self.send(ctx, result)

    @command(
        _eval.command,
        name="cancel",
        aliases=["c"],
        examples=["{prefix}eval cancel ffasbl"],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
    )
    async def cancel_eval(self, ctx: commands.Context, name: str):
        name = name.lower()

        if name == "all":
            if not self.bot.eval_tasks:
                return await ctx.send("There is no eval tasks currently running")

            results: Dict[str, Optional[Exception]] = {}

            for name, (task, time) in self.bot.eval_tasks.items():
                if task.cancelling() or task.done():
                    continue

                try:
                    task.cancel()
                except Exception as exc:
                    error = "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    )
                    results[name] = error
                else:
                    results[name] = None

            embed = discord.Embed(
                description="\n".join(
                    f"\N{WHITE HEAVY CHECK MARK} `{name}`"
                    if not error
                    else f"\N{CROSS MARK} `{name}`\n```py\n{error}\n```"
                    for name, error in results.items()
                ),
                color=self.bot.color,
            )

            return await ctx.send(embed=embed)

        if not self.bot.eval_tasks.get(name):
            return await ctx.send(f"Eval task does not exist")

        task, time = self.bot.eval_tasks[name]
        task: asyncio.Task

        if task.done():
            return await ctx.send("Task is already completed")

        if task.cancelling():
            return await ctx.send("Task is already cancelling")

        async with Updater(ctx):
            task.cancel()
        self.bot.eval_tasks.pop(name, None)

        await ctx.send(f"Successfully cancelled task")

    @command(
        _eval.command,
        name="tasks",
        aliases=["t", "l"],
        examples=["{prefix}eval tasks"],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
    )
    async def eval_tasks(self, ctx: commands.Context):
        if not self.bot.eval_tasks:
            return await ctx.send("There is no eval tasks currently running")

        tasks: Dict[str, Dict[asyncio.Task, datetime]] = self.bot.eval_tasks.items()
        wrapped_tasks = WrapList([(key, *value) for key, value in tasks], length=6)

        embeds = [
            discord.Embed(
                description="\n".join(
                    f"`{name}` invoked at {discord.utils.format_dt(time, 'F')}"
                    for name, task, time in tasks
                ),
                color=self.bot.color,
            )
            for tasks in wrapped_tasks
        ]

        await paginate(ctx, embeds, timeout=30)

    @command(
        commands.command,
        name="as",
        aliases=["su"],
        examples=["{prefix}as flowerpad#0001 help"],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
    )
    async def _as(self, ctx, user: discord.Member, *, command: str):
        prefix = await self.bot.get_formatted_prefix()
        msg = copy(ctx.message)
        msg.content = f"{prefix}{command}"
        msg.author = user
        await self.bot.process_commands(msg)

    @command(
        commands.command,
        aliases=["pull"],
        examples=["{prefix}update"],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
    )
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

    @command(
        commands.command,
        aliases=["rs"],
        examples=["{prefix}restart"],
        permissions=CommandPermissions(template=PermissionTemplates.text_command),
    )
    async def restart(self, ctx: commands.Context):
        await ctx.message.reply("Now restarting bot")

        with open("restart.json", "w") as f:
            data = {
                "guild": ctx.guild.id,
                "channel": ctx.channel.id,
                "message": ctx.message.id,
                "time": datetime.utcnow().timestamp(),
            }
            f.write(json.dumps(data, indent=4))
            f.close()

        ctx._message: discord.Message = None

        async def updater(message: str):
            if self._message:
                content = ctx._message.content
                content += "\n" + message
                ctx._message = await ctx._message.edit(content=content)
            else:
                ctx._message = await ctx.send(message)

        await self.bot.close(updater)


async def setup(bot):
    await bot.add_cog(Developer(bot))
