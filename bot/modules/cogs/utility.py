from datetime import datetime
import json
import os
from io import BytesIO
import random
import re
import tempfile
import traceback
import discord
import humanfriendly

from discord.ext import commands

from core.bot import amyrin
from modules.util.converters import FileConverter, URLObject, format_list
from modules.util.executor import executor
from modules.util.media.exceptions import AgeLimited, FailedCompressionException, InvalidFormat, MediaException, ValidityCheckFailed
from modules.views.song import SongView
from urllib.parse import quote_plus
from modules.views.paginator import paginate
from modules.util.handlers.nginx import NginxHandlerExceededSizeLimit, NginxHandlerException
from modules.util.media.downloader import Downloader, FileDownload, URLDownload

from . import *
from .flags import DownloadFlags

URBAN_DICTIONARY_HYPERLINK_REGEX = r"\[([^\]]+)\]"
URBAN_DICTIONARY_API_URL = "https://api.urbandictionary.com/v0/define"
URBAN_DICTIONARY_URL = "https://www.urbandictionary.com/define.php?term={}"
URBAN_DICTIONARY_AUTHOR_URL = "https://www.urbandictionary.com/author.php?author={}"

class Utility(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: amyrin = bot
        
    async def _process_download(self, ctx, url: str, format: str, compress: bool):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.bot.get_context(ctx.message)

        if ctx.interaction:
            await ctx.interaction.response.defer()

        ctx.msg = None

        async def update(message: str):
            if ctx.interaction:
                if not ctx.interaction.response.is_done():
                    return await ctx.interaction.follow.send(message)
                return await ctx.interaction.edit_original_response(content=message)
            else:
                if not ctx.msg:
                    ctx.msg = await ctx.reply(message)
                else:
                    await ctx.msg.edit(content=message)

        nginx = self.bot.nginx

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                downloader = Downloader(
                    ctx,
                    url,
                    output=tmp_dir,
                    nginx=nginx,
                    format=format,
                    updater=update,
                    compress=compress
                )
            except InvalidFormat as exc:
                valid_formats = []
                for format, data in exc.valid_formats.items():
                    valid_formats.append(format)
                    for alias in data.get("aliases", []):
                        valid_formats.append(alias)

                fmt_formats = format_list(
                    valid_formats, seperator="and", brackets="`"
                )
                return await update(
                    f"Invalid format passed, valid formats are {fmt_formats}"
                )

            try:
                result = await downloader.download(
                    age_limit=18 if not ctx.channel.is_nsfw() else None
                )
            except FailedCompressionException:
                return await update(
                    "Failed to compress output file, please try running the command again in a server with a higher filesize limit (through server boosts)."
                )
            except ValidityCheckFailed as exc:
                return await update(str(exc))
            except NginxHandlerExceededSizeLimit as exc:
                limit = humanfriendly.format_size(nginx._limit, binary=True)
                size = humanfriendly.format_size(exc.size, binary=True)
                exceeded = humanfriendly.format_size(exc.exceeded, binary=True)
                return await update(f"Download ({size}) exceeds nginx server's filesize limit ({limit}) by {exceeded}.")
            except MediaException as exc:
                return await update(str(exc))
            except AgeLimited:
                return await update("This video is not able to be downloaded, as it exceeds the maximum age limit.")
            except json.JSONDecodeError as exc:
                if random.randint(1,1000) == 591:
                    reason = "of gas leak!?!??!?"
                else:
                    reason = "the URL is not supported by yt-dlp."
                return await update(f"Failed to parse validity checking result. This might be because {reason}")

            compressed: bool = result.compressed
            content_type_converted: bool = result.content_type_converted
            sizes = result.sizes

            content = []

            if compressed:
                old_size = sizes.get("old")
                new_size = sizes.get("new")

                fmt_old_size = humanfriendly.format_size(old_size)
                fmt_new_size = humanfriendly.format_size(new_size)

                compressed_by = 100 * (old_size - new_size) / old_size

                compression_time = result.compression_time
                fmt_compression_time = humanfriendly.format_timespan(compression_time)

                content.append(
                    f"✅ Output compression ratio was `{int(compressed_by)}%` and the compression took {fmt_compression_time} (old: `{fmt_old_size}` | new: `{fmt_new_size}`)"
                )

            if content_type_converted:
                content.append(
                    "❗️ Mimetype of output file was different to the desired output, this might be because the file didn't contain the necessary streams for the desired output"
                )

            if isinstance(result, FileDownload):
                content = None
                attachments = [discord.File(result.path)]#
            elif isinstance(result, URLDownload):
                content = result.url
                attachments = []

            if ctx.interaction:
                await ctx.interaction.edit_original_response(
                    content=content,
                    attachments=attachments,
                )
            else:
                await ctx.msg.edit(
                    content=content,
                    attachments=attachments,
                )
    
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
        
        if not definitions:
            return await ctx.send(f"No definitions found for term `{term}`")
        
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
        commands.group,
        name="nginx",
        description="Manage my nginx server",
        examples=[
            "{prefix}nginx https://cdn.discordapp.com/attachments/381963689470984203/1068926488453332993/sQWxQyB.jpg"
        ],
        hidden=True,
        invoke_without_command=True
    )
    @commands.is_owner()
    async def nginx(
        self,
        ctx: commands.Context,
        file: str = commands.param(
            description="Parameter if using a URL. You don't need to pass this if you add an attachment to your message",
            default=None,
        ),
    ):
        await self.nginx_upload(ctx, file)

    @command(
        nginx.command,
        name="add",
        aliases=["save", "upload"],
        description="Save a file to my nginx server",
        examples=[
            "{prefix}nginx add https://cdn.discordapp.com/attachments/381963689470984203/1068926488453332993/sQWxQyB.jpg"
        ],
        hidden=True
    )
    @commands.is_owner()
    async def nginx_upload(
        self,
        ctx: commands.Context,
        file: str = commands.param(
            description="Parameter if using a URL. You don't need to pass this if you add an attachment to your message",
            default=None,
        ),
    ):
        file: URLObject = await FileConverter().convert(ctx, file)

        buffer = BytesIO(await file.read())
        
        try:
            url = await self.bot.nginx.add(buffer, filename=file.filename)
        except NginxHandlerExceededSizeLimit as exc:
            exceeded = humanfriendly.format_size(exc.exceeded)
            
            await ctx.send(f"Given file exceeds file limit by {exceeded}.")
        except NginxHandlerException as exc:
            await ctx.send(str(exc))
        else:
            await ctx.send(str(url))
            
    @command(
        nginx.command,
        name="remove",
        aliases=["delete"],
        description="Delete a file from my nginx server",
        examples=[
            "{prefix}nginx remove qtD8v7H2uBV3ceLv.jpg"
        ],
        hidden=True
    )
    @commands.is_owner()
    async def nginx_remove(
        self,
        ctx: commands.Context,
        name: str = commands.param(
            description="Name for the file"
        ),
    ):
        try:
            await self.bot.nginx.remove(name)
        except NginxHandlerExceededSizeLimit as exc:
            exceeded = humanfriendly.format_size(exc.exceeded)
            
            await ctx.send(f"Given file exceeds file limit by {exceeded}.")
        except FileNotFoundError:
            await ctx.send(f"File {name} could not be found.")
        else:
            await ctx.send(f"Successfully deleted file `{name}`.")
            
    @command(
        commands.command,
        name="download",
        aliases=["dl"],
        description="Download a video or audio from a yt-dlp supported source.",
        examples=[
            "{prefix}download https://www.youtube.com/watch?v=gd-7Ye_vX1k"
        ],
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def download(self, ctx, url: str = commands.param(), flags: DownloadFlags = None):
        format = "mp4" if not flags else flags.format
        compress = False if not flags else flags.compress
        
        await self._process_download(ctx, url, format, compress)


async def setup(bot):
    await bot.add_cog(Utility(bot))
