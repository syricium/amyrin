import random
import string
from typing import List, Optional

import discord
from discord.ext import commands

from modules.util.scraping.documentation.discord_py import DocScraper, SearchResults

from .base import View

class DocSelectOption(discord.SelectOption):
    def __init__(self, url: str, *args, **kwargs) -> None:
        self.url = url
        
        super().__init__(*args, **kwargs)

class DocSelect(discord.ui.Select):
    def __init__(self, parent: View, results: SearchResults):

        self._parent = parent
        self.texts = {}

        for name, url, _ in results.results:
            if name not in self.texts.keys():
                self.texts[name] = url

        super().__init__(
            placeholder="Select option",
            options=[DocSelectOption(label=name, url=url) for name, url in self.texts.items()],
        )

    async def callback(self, interaction: discord.Interaction):
        option = discord.utils.get(self.options, label=self.values[0])
        await self._parent._callback(interaction, option)


class DocView(View):
    def __init__(
        self,
        context: commands.Context,
        scraper: DocScraper,
        query: str,
        color: int,
        *args, **kwargs
    ):
        super().__init__(timeout=30, *args, **kwargs)

        self.query = query
        self.scraper = scraper
        self.context = context
        self._color = color
        self._message: discord.Embed = None
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.context.author.id:
            await interaction.response.defer()
            return False
        return True
        
    async def _callback(self, interaction: discord.Interaction, option: DocSelectOption):
        await interaction.response.defer()
        await self._update(interaction, option.url)
        
    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        embed: discord.Embed = self._message.embeds[0]
        embed.set_author(name=embed.author.name + " | Timed out", icon_url=embed.author.icon_url)
        await self._message.edit(view=self, embed=embed)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        if interaction.response.is_done():
            func = interaction.followup.send
        else:
            func = interaction.response.send_message
        return await func(
            "Unknown error occured while scraping, maybe the sphinx inventory parser returned an invalid element",
            ephemeral=True
        )
        
    async def _send(self, interaction: discord.Interaction | commands.Context, *args, **kwargs) -> Optional[discord.Message]:
        if isinstance(interaction, commands.Context):
            self._message = await interaction.send(*args, **kwargs)
        elif isinstance(interaction, discord.Interaction):
            if interaction.response.is_done():
                await interaction.edit_original_response(*args, **kwargs)
            else:
                await interaction.response.send_message(*args, **kwargs)
        
    async def _update(self, interaction: discord.Interaction | commands.Context, url: str):
        async with interaction.channel.typing():
            docs = await self.scraper.get_documentation(url)
        
        embed = docs.to_embed(color=self._color)
        await self._send(interaction, embed=embed, view=self)
    
    async def start(self):
        ctx = self.context
        
        results = await self.scraper.search(self.query, limit=8, exclude_std=True)
        
        if not results:
            await self._send(ctx, content="No results found")
        
        select = DocSelect(self, results)
        self.add_item(select)
        
        await self._update(ctx, results.results[0][1])

    


async def setup(bot):
    pass
