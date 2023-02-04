from discord.ext import commands

from core.bot import amyrin


class Checks(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: amyrin = bot
        self.bot.add_check(self.debug_check)

    async def debug_check(self, ctx: commands.Context):
        if not self.bot.debug:
            return True

        if not await self.bot.is_owner(ctx.author):
            prefix = await self.bot.get_formatted_prefix(False)

            await ctx.reply(
                "You are trying to use the debug version of the bot, which only my owner can, "
                f"the prefix of the stable version is {prefix} (ex: {prefix} help)"
            )
            return False
        elif ctx.interaction:
            return False

        return True


async def setup(bot):
    await bot.add_cog(Checks(bot))
