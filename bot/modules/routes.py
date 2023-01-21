from typing import Dict
from discord.ext import commands
from discord.ext.ipc.server import Server
from discord.ext.ipc.objects import ClientPayload
import os

class Routes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_load(self) -> None:
        if self.bot.ipc is not None and not self.bot.ipc.started:
            await self.bot.ipc.start()

    async def cog_unload(self) -> None:
        await self.bot.ipc.stop()
        self.bot.ipc = None

    @Server.route()
    async def get_users_and_guilds(self, data: ClientPayload) -> Dict:
        users = len(self.bot.users)
        guilds = len(self.bot.guilds)
        return {
            "users": users,
            "guilds": guilds
        }

async def setup(bot):
    await bot.add_cog(Routes(bot))