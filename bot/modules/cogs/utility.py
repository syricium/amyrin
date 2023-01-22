from discord.ext import commands

from core.bot import onyx
from modules.util.views.song import SongView

class Utility(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: onyx = bot

    @commands.hybrid_command(name="song", description="Look up a song and it's lyrics")
    async def song(
        self,
        ctx: commands.Context,
        query: str
    ):
        view = SongView(ctx, query)
        await view.start()

async def setup(bot):
    await bot.add_cog(Utility(bot))
