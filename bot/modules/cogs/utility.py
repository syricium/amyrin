import os
from io import BytesIO

import magic
from aiohttp import FormData
from discord.ext import commands

from core.bot import onyx
from modules.util.converters import FileConverter, URLObject
from modules.util.executor import executor
from modules.views.song import SongView

from . import *


class Utility(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: onyx = bot

    @executor()
    def _detect_content_type(self, buffer: BytesIO):
        return magic.from_buffer(buffer)

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
        name="cdn",
        description="Upload a file to the syrice mediaserver",
        examples=[
            "{prefix}cdn https://cdn.discordapp.com/attachments/381963689470984203/1068926488453332993/sQWxQyB.jpg"
        ],
    )
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
