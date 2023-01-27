import discord


from modules.util.scraping.documentation.discord_py import DocScraper, SearchResults

from ..paginator import EmbedPaginator
from ..base import View
from playwright.async_api._generated import Browser
from discord.ext import commands
from modules.util.views.paginator import paginate, WrapList

class Select(discord.ui.Select):
    def __init__(self, parent: View, results: SearchResults):
        self._parent = parent
        
        super().__init__(
            placeholder="View documentation for...",
            options=[
                discord.SelectOption(label=result.name)
                for result in results.results[:25]
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        print(interaction.values)
        return await self.parent._callback(interaction)

class DocView(View):
    def __init__(
        self,
        browser: Browser,
        query: str,
        user: discord.User,
        *args, **kwargs
    ):
        self.user = user
        self.query = query
        
        self.docscraper = DocScraper(browser)
        
        self.message: discord.Message = None
        
        super().__init__(*args, **kwargs)
        
    async def update(self, index: int, interaction: discord.Interaction):
        return await super().update(index, interaction)
        
    async def _callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(interaction.values[0], ephemeral=True)

    async def start(self, context: commands.Context, exlude_references: bool = False):
        result = await self.docscraper.search(
            query=self.query,
            exlude_references=exlude_references
        )
        
        select = Select(self, result)
        self.add_item(select)
        
        wrapped_results = WrapList(result.results, length=8)
        embeds = []
        for results in wrapped_results:
            results_obj = SearchResults(
                results,
                query_time=result.query_time,
                query_results=result.query_results
            )
            
            embeds.append(results_obj.to_embed(color=context.bot.color))
        
        self.message = await super().start(
            context,
            embeds=embeds,
            timeout=30
        )

async def setup(bot):
    pass