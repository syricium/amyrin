import importlib
import os
import re
import traceback
from typing import Dict, List, Optional

import discord
from discord.ext import commands

from .base import TrashView, View


class PullView(View):
    def __init__(
        self, context: commands.Context, output: str, modules: List[str]
    ) -> None:
        super().__init__()
        self.context = context
        self._output = output
        self.modules = modules

        if not modules:
            del self.children[0]

    async def on_error(
        self, exc: Exception, item: discord.ui.Item, interaction: discord.Interaction
    ) -> None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        await interaction.response.send_message(tb, view=TrashView(self.context.author))

    async def reload_modules(self) -> Dict[str, Optional[Exception]]:
        reloaded = {}
        for module in self.modules:
            try:
                await self.context.bot.reload_extension(module)
            except commands.ExtensionNotLoaded:
                imp = importlib.import_module(module)
                importlib.reload(imp)
                reloaded[module] = None #
            except Exception as exc:
                error = traceback.format_exception(type(exc), exc, exc.__traceback__)
                reloaded[module] = "\n".join(error)
            else:
                reloaded[module] = None

        return reloaded

    @discord.ui.button(style=discord.ButtonStyle.grey, label="Reload")
    async def reload(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user.id != self.context.author.id:
            return

        res = await self.reload_modules()

        msg = "\n".join(
            f"✅ `{k}`" if not v else f"❌ `{k}`\n```{v}```" for k, v in res.items()
        )
        embed = discord.Embed(title="Reloaded Cogs", description=msg)
        await interaction.response.send_message(embed=embed)
        await self.disable_all(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, label="Restart")
    async def restart(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user != self.context.author:
            return

        await interaction.response.defer()
        await self.disable_all(interaction)
        await self.context.bot.close()
