# credits to https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612

import sys
import traceback

import discord
from discord.ext import commands


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if hasattr(ctx.command, "on_error"):
            return

        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound,)
        error = getattr(error, "original", error)

        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f"{ctx.command} has been disabled.")

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(
                    f"{ctx.command} can not be used in Private Messages."
                )
            except discord.HTTPException:
                pass
            
        elif isinstance(error, commands.MissingRequiredArgument):
            param = error.param
            await ctx.send(f"Missing parameter `{param.name}`", ephemeral=True)

        elif isinstance(error, commands.BadArgument):
            if ctx.command.qualified_name == "tag list":
                await ctx.send("I could not find that member. Please try again.")

        else:
            print(
                "Ignoring exception in command {}:".format(ctx.command), file=sys.stderr
            )
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )


async def setup(bot):
    await bot.add_cog(CommandErrorHandler(bot))
