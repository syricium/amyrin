from core.bot import onyx
from discord.ext import commands
from modules.util.views.song import SongView

from . import *


class Utility(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: onyx = bot

    @command(
        description="Look up a song and it's lyrics",
        examples=["{prefix}song despacito"]
    )
    async def song(
        self,
        ctx: commands.Context,
        query: str = commands.param(description="The name of the song to look up"),
    ):
        view = SongView(ctx, query)
        await view.start()


async def setup(bot):
    await bot.add_cog(Utility(bot))
