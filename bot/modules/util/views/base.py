import discord
from copy import copy

class View(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def disable_all(
        self,
        interaction: discord.Interaction | discord.Message
    ):
        children = copy(self.children)
        for child in self.children:
            child.disabled = True
        if isinstance(interaction, discord.Interaction):
            if interaction.response.is_done():
                await interaction.edit_original_response(view=self)
            else:
                await interaction.response.edit_message(view=self)
        else:
            await interaction.edit(view=self)
        return children