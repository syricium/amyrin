import random
import string
from io import StringIO

import discord
from discord.ext import commands
from modules.util.imaging.converter import ImageConverter


class Context(commands.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    async def to_image(self, content: str = None):
        return await ImageConverter().convert(self, (content or self.message.content))

    async def send(self, content: str = None, *args, **kwargs):
        if content is not None:
            if len(content) > 2000:
                buf = StringIO()
                buf.write(content)
                buf.seek(0)
                msg = await super().send(
                    content="Message was over 2000 characters, so it has been turned into a text file",
                    file=discord.File(buf, filename="message.txt"),
                    *args,
                    **kwargs,
                )
                return await msg.edit(
                    content=msg.content
                    + f"\nOpen in browser: https://api.syrice.pink/api/v1/read?url={msg.attachments[0].url}"
                )

        return await super().send(content, *args, **kwargs)

    async def string_to_file(
        self, content: str = None, filename: str = "message.txt"
    ) -> discord.File:
        if filename == "random":
            filename = "".join(random.choices(string.ascii_letters, k=24))

        buf = StringIO()
        buf.write(content)
        buf.seek(0)
        return discord.File(buf, filename=filename)

    async def send_as_file(
        self,
        content: str = None,
        message_content: str = None,
        filename: str = "message.txt",
        *args,
        **kwargs,
    ) -> discord.Message:

        file = self.string_to_file(content, filename=filename)

        return await super().send(
            content=message_content,
            file=file,
            *args,
            **kwargs,
        )

async def setup(bot):
    pass