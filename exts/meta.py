from discord.ext import commands
from core import Amyrin


class Cog(commands.Cog, name="Meta"):
    def __init__(self, bot: Amyrin) -> None:
        self.bot = bot
    
    @commands.command()
    async def ping(self, ctx: commands.Context):
        fmt_ping = int(self.bot.latency * 1000)
        await ctx.send(f"{fmt_ping}ms")
    
async def setup(bot: Amyrin):
    await bot.add_cog(Cog(bot=bot))