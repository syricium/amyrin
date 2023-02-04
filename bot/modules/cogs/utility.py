from datetime import datetime
from email.quoprimime import quote
import os
from io import BytesIO
import re
import discord

import magic
from aiohttp import FormData
from discord.ext import commands

from core.bot import amyrin
from modules.util.converters import FileConverter, URLObject
from modules.util.executor import executor
from modules.views.song import SongView
from urllib.parse import quote_plus
from modules.views.paginator import paginate

from . import *

URBAN_DICTIONARY_HYPERLINK_REGEX = r"\[([^\]]+)\]"
URBAN_DICTIONARY_API_URL = "https://api.urbandictionary.com/v0/define"
URBAN_DICTIONARY_URL = "https://www.urbandictionary.com/define.php?term={}"
URBAN_DICTIONARY_AUTHOR_URL = "https://www.urbandictionary.com/author.php?author={}"

class Utility(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: amyrin = bot

    @executor()
    def _detect_content_type(self, buffer: BytesIO):
        return magic.from_buffer(buffer)
    
    @executor
    def classify_nudity(self, path: os.PathLike) -> float:
        ...
    
    def _format_ud_hyperlink(self, term: str):
        formatted_term = quote_plus(term)
        return URBAN_DICTIONARY_URL.format(formatted_term)
    
    def _format_ud_text(self, text: str):
        new_text = text
        for result in re.finditer(URBAN_DICTIONARY_HYPERLINK_REGEX, text):
            start = result.start()
            end = result.end()
            term = text[start+1:end-1]
            formatted_hyperlink = self._format_ud_hyperlink(term)
            hyperlink_text = f"[{term}]({formatted_hyperlink})"
            new_text = new_text.replace(text[start:end], hyperlink_text)
                
        return new_text
    
    def _format_ud_definitions(self, definitions: List[dict]) -> List[discord.Embed]:
        embeds = []
        for definition in definitions:
            word = definition["word"]
            text = self._format_ud_text(definition["definition"])
            author = definition["author"]
            author_url = URBAN_DICTIONARY_AUTHOR_URL.format(quote_plus(author))
            example = self._format_ud_text(definition["example"])
            written_on = datetime.fromisoformat(definition["written_on"])
            permalink = definition["permalink"]
            thumbs_up = definition["thumbs_up"]
            thumbs_down = definition["thumbs_down"]
            
            description = f"{text}\n\n**Example:**\n{example}"
            embed = discord.Embed(
                url=permalink,
                title=word,
                description=description,
                timestamp=written_on,
                color=self.bot.color
            )
            embed.set_footer(text=f"\N{THUMBS UP SIGN} {thumbs_up} | \N{THUMBS DOWN SIGN} {thumbs_down}")
            embed.set_author(
                name=author,
                url=author_url
            )
            
            embeds.append(embed)
            
        return embeds
    
    @command(
        aliases=["ud", "urban"],
        description="Look up a term in the urban dictionary",
        examples=["{prefix}ud bottom"],
    )
    async def urbandictionary(
        self,
        ctx: commands.Context,
        term: str = commands.param(description="The term you want to look up"),
    ):
        resp = await self.bot.session.get(
            URBAN_DICTIONARY_API_URL,
            params={"term": term}
        )
        
        if resp.status != 200:
            return await ctx.send("Failed to get term definition")
        
        data = await resp.json()
        definitions = data["list"]
        embeds: List[discord.Embed] = self._format_ud_definitions(definitions)
        
        await paginate(ctx, embeds, timeout=30)
                

    @command(
        description="Look up a song and it's lyrics",
        examples=["{prefix}song despacito"],
    )
    async def song(
        self,
        ctx: commands.Context,
        query: str = commands.param(description="The name of the song to look up"),
    ):
        view = SongView(ctx, query)
        await view.start()

    @command(
        commands.command,
        name="cdn",
        description="Upload a file to the syrice mediaserver",
        examples=[
            "{prefix}cdn https://cdn.discordapp.com/attachments/381963689470984203/1068926488453332993/sQWxQyB.jpg"
        ],
    )
    @commands.is_owner()
    async def cdn_upload(
        self,
        ctx: commands.Context,
        file: str = commands.param(
            description="Parameter if using a URL, you don't need to pass this if you add an attachment to your message",
            default=None,
        ),
    ):
        file: URLObject = await FileConverter().convert(ctx, file)

        async with ctx.typing():
            filedata = await file.read()
            buffer = BytesIO(filedata)
            content_type = await self._detect_content_type(filedata)
            form = FormData()
            form.add_field(
                "file", buffer, content_type=content_type, filename=file.filename
            )

            MS_KEY = os.getenv("MEDIASERVER_KEY")
            async with await self.bot.session.post(
                "https://ms.syrice.pink/upload",
                data=form,
                headers={"Authorization": f"Bearer {MS_KEY}"},
            ) as resp:
                data = await resp.json()

                if not data.get("error", False):
                    file_id = data.get("file_id")
                    message = f"https://ms.syrice.pink/view/{file_id}"
                else:
                    message = data.get(
                        "exception", "Error occured but exception key does not exist."
                    )

        return await ctx.send(message)


async def setup(bot):
    await bot.add_cog(Utility(bot))
