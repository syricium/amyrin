import ast
import asyncio
from copy import copy
import inspect
import os
import traceback
from typing import Any, AsyncGenerator, Callable, Coroutine
import discord
import textwrap
from discord.ext import commands
import import_expression
from core import Amyrin
from jishaku.repl.compilation import wrap_code
from jishaku.codeblocks import codeblock_converter, Codeblock
from jishaku.repl import KeywordTransformer

from utils import Updater, executor

def parse_code(code: str) -> ast.Module:
    fmt = f"""async def func():
    from importlib import import_module as {import_expression.constants.IMPORTER}
{textwrap.indent(code, '    ')}""" # type: ignore

    fmt: ast.Module = import_expression.parse(fmt) # type: ignore
    ast.fix_missing_locations(fmt)
    block: ast.AsyncFunctionDef = fmt.body[-1] # type: ignore
    KeywordTransformer().generic_visit(block)

    last = block.body[-1]

    if not isinstance(last, ast.Expr):
        return fmt

    if not isinstance(last.value, ast.Yield):
        assign = ast.Yield(last.value)
        ast.copy_location(assign, last)
        _yield = ast.Expr(assign)
        ast.copy_location(_yield, last)
        block.body[-1] = _yield

    return fmt

async def evaluate_code(ctx: commands.Context, env: dict, code: str):
    try:
        res = parse_code(code)
        comp = compile(res, filename="<eval>", mode="exec")
    except Exception as exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        result = f"```py\n{tb}```"
        return await ctx.send(result)

    """ Evaluating """
    result = None
    async with Updater(ctx):
        try:
            exec(comp, env)
            func: Callable = env.get("func") # type: ignore
            if inspect.isasyncgenfunction(func):
                return func
            else:
                await func()
        except Exception as exc:
            result = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )

        if result is not None and len(str(result.strip())) > 0:
            return result


async def handle_async_generator(
    ctx: commands.Context, func: Coroutine[Any, Any, AsyncGenerator], *args, **kwargs
):
    async for i in func(): # type: ignore
        if i is not None:
            await send(ctx, i, *args, **kwargs)


async def send(ctx: commands.Context, result, *args, **kwargs):
    if isinstance(result, list):
        if all(isinstance(i, discord.Embed) for i in result):
            return await ctx.send(embeds=result, *args, **kwargs)
        if all(isinstance(i, discord.Attachment) for i in result):
            return await ctx.send(
                files=[await i.to_file() for i in result], *args, **kwargs
            )
        if all(isinstance(i, discord.File) for i in result):
            return await ctx.send(files=result, *args, **kwargs)
        return await ctx.send(str(result), *args, **kwargs)
    if isinstance(result, discord.Embed):
        return await ctx.send(embed=result, *args, **kwargs)
    if isinstance(result, discord.Attachment):
        return await ctx.send(file=await result.to_file(), *args, **kwargs)
    if isinstance(result, discord.File):
        return await ctx.send(file=result, *args, **kwargs)
    if isinstance(result, str):
        if len(result.splitlines()) > 1:
            return await ctx.send(
                f"```py\n{str(result).replace('``', '`​`')}```", *args, **kwargs
            )
        return await ctx.send(result, *args, **kwargs)
    if isinstance(result, discord.ui.View):
        return await ctx.send(view=result, *args, **kwargs)
    if result is None:
        return

    return await ctx.send(str(result), *args, **kwargs)

class Cog(commands.Cog, name="Developer", command_attrs={"hidden": True}):
    def __init__(self, bot: Amyrin) -> None:
        self.bot = bot
        
    async def cog_check(self, ctx: commands.Context) -> bool:
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner
        return True
        
    @executor()
    def pull(self) -> ...:
        git = self.bot.git
        remote, branch = "origin", "rewrite" # you can change rewrite to main or master, depending on what branch your code is on
        
        remote = git.remote(remote)
        remote.pull(branch)
        
        diff = git.head.commit.diff(None, create_patch=True)
        
        updated_items: list[os.PathLike] = [
            item for item in diff
            if item.change_type == "M"
        ]
        
        return updated_items
        
        
    @commands.group(
        name="eval",
        aliases=["e"]
    )
    async def _eval(self, ctx: commands.Context, *, code: codeblock_converter): # type: ignore
        """Command to evaluate code with access to commonly used globals

        Parameters
        -----------
        code: str
            The code to evaluate, supports codeblocks
            
        Example
        -------
        {prefix}eval print("hi")
        """
        
        code: Codeblock = code # typing 😊😊😊😊😊😊😊😊😊
        
        ref = None if ctx.message.reference is None else ctx.message.reference.resolved
        env = {
            "discord": discord,
            "commands": commands,
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
            "ref": ref,
            "rf": ref,
        }
        
        """ Code Parsing """

        result = await evaluate_code(ctx, env, code.content)

        if inspect.isasyncgenfunction(result):
            return await handle_async_generator(ctx, result) # type: ignore

        if result is not None:
            await send(ctx, result)
            
    @commands.command(name="as", aliases=["su"])
    async def _as(self, ctx: commands.Context, user: discord.Member, *, command: str):
        """Command to simulate a user running a command
        
        Examples:
        
          {prefix}as Danny#0007 ping

        Parameters
        -----------
        user: discord.Member
            The member to run the command as
        command: str
            The command to simulate the user running
        """
        
        prefix = ctx.prefix # TODO: remember to make this work with per user prefixes if i ever implement them
        
        msg = copy(ctx.message)
        msg.content = prefix + command # type: ignore
        msg.author = user
        
        await self.bot.process_commands(msg)
        
    @commands.command(name="pull")
    async def _pull(self, ctx: commands.Context):
        """A command to pull the latest changes using git
        
        Examples:
        
          {prefix}pull
        """
        
        print("ran")
        result = await self.pull()
        print(result)
    
    
        
    
async def setup(bot: Amyrin):
    await bot.add_cog(Cog(bot=bot))