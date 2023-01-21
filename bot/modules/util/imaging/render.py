import asyncio
import copy
import functools
import io
import os
import random
import time

import discord
import humanize
import pilmoji
import requests
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ..executor import executor


class Timer:
    def __init__(self):
        self._start = None
        self._end = None

    def start(self):
        self._start = time.perf_counter()

    def stop(self):
        self._end = time.perf_counter()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __int__(self):
        return int(self.time)

    @property
    def time(self):
        return round((self._end - self._start) * 1000, 3)


def is_animated(image: io.BytesIO):
    img = Image.open(image)
    return img.is_animated


class ImageResult:
    def __init__(self, image: io.BytesIO, render_time: int, **kwargs):
        self.image = image
        self.render_time = render_time
        self.kwargs = kwargs

    def __getattr__(self, name: str):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            return self.kwargs.get(name, None)

    @property
    def file(self):
        if is_animated(copy.copy(self.image)):
            return discord.File(self.image, filename="image.gif")
        return discord.File(self.image, filename="image.png")


def progress_bar(progress: int):
    with Timer() as timer:
        progress = progress / 100
        buffer = io.BytesIO()
        bar = Image.new("RGBA", (411, 40))
        draw = ImageDraw.Draw(bar)
        x, y = (0, 0)
        w, h = (350, 39)
        color = (51, 51, 51)
        draw.ellipse((x + w, y, x + h + w, y + h), fill=color)
        draw.ellipse((x, y, x + h, y + h), fill=color)
        draw.rectangle((x + (h / 2), y, x + w + (h / 2), y + h), fill=color)
        if progress <= 0:
            progress = 0.01
        if progress > 1:
            progress = 1
        w = w * progress
        color = (random.randint(1, 255), random.randint(1, 255), random.randint(1, 255))
        draw.ellipse((x + w, y, x + h + w, y + h), fill=color)
        draw.ellipse((x, y, x + h, y + h), fill=color)
        draw.rectangle((x + (h / 2), y, x + w + (h / 2), y + h), fill=color)
        
        bar.save(buffer, format="png")
        buffer.seek(0)
    return ImageResult(buffer, timer.time)


def rounden(image: io.BytesIO):
    with Timer() as timer:
        img = Image.open(image)
        mask = Image.open("./assets/circle_mask.png").convert("L")

        img = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
        img.putalpha(mask)

        buffer = io.BytesIO()
        img.save(buffer, format="png")
        buffer.seek(0)
    return ImageResult(buffer, timer.time)


def welcome_card(user: discord.Member, members: int):
    with Timer() as timer:
        # Defining
        buffer = io.BytesIO()
        avatar = io.BytesIO(requests.get(user.avatar.with_format("png").url).content)
        mask = Image.open("./assets/welcome_mask.png").convert("L")
        image = Image.open(
            f"./assets/welcome/{random.choice(os.listdir('./assets/welcome'))}"
        ).convert("RGB")
        profile_picture = Image.open(avatar).resize((131, 131)).convert("RGB")
        profile_mask = Image.open("./assets/profile_mask.png").convert("L")
        draw = ImageDraw.Draw(image)

        # Set Up Images
        image = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
        image.putalpha(mask)

        # Profile Picture
        profile_picture = ImageOps.fit(
            profile_picture, profile_mask.size, centering=(0.5, 0.5)
        )
        profile_picture.putalpha(profile_mask)
        profile_picture = profile_picture.resize((131, 131))
        image.paste(profile_picture, (30, 34), profile_picture)

        # Name Text
        draw = pilmoji.Pilmoji(image)
        font = ImageFont.truetype("./assets/fonts/OpenSans.ttf", 30)
        name = user.name
        limit = 12
        if len(name) > limit:
            name = f"{name[:limit-3]}..."
        draw.text((177, 40), f"Welcome, {name}!", font=font)

        # Member Text
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("./assets/fonts/ArialCE.ttf", 30)
        text1 = "We now have "
        amount = humanize.intcomma(members)
        text2 = f" members!"

        text1_pos = (177, 85)
        amount_pos = (text1_pos[0] + 190, text1_pos[1])
        text2_pos = (text1_pos[0] - 5, text1_pos[1] + 35)

        draw.text(text1_pos, text1, font=font)
        draw.text(amount_pos, amount, (245, 37, 37), font=font)
        draw.text(text2_pos, text2, font=font)

        image.save(buffer, format="png")
        buffer.seek(0)
        image.close()
        profile_picture.close()
        profile_mask.close()
    return ImageResult(buffer, timer.time)


def leveling_card(
    user: discord.Member, progress: int, current: int, max: int, background: str = None
):
    with Timer() as timer:
        # Defining
        buffer = io.BytesIO()
        avatar = io.BytesIO(requests.get(user.avatar.with_format("png").url).content)

        if background is not None:
            leveling_mask = Image.open("./assets/leveling_mask.png").convert("L")
            background = Image.open(io.BytesIO(requests.get(background).content))
            image = ImageOps.fit(background, leveling_mask.size, centering=(0.5, 0.5))
            image.putalpha(leveling_mask)
        else:
            image = Image.open("./assets/leveling_mask.png")
        profile_picture = Image.open(avatar).resize((131, 131)).convert("RGB")
        profile_mask = Image.open("./assets/profile_mask.png").convert("L")
        draw = ImageDraw.Draw(image)

        # Progress Bar
        bar = Image.open(progress_bar(progress).image)
        image.paste(bar, (170, 122), bar)

        # XP
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("./assets/fonts/ArialCE.ttf", 28)
        pos = [image.width - 85, 10]
        XP = f"{humanize.intcomma(current)}/{humanize.intcomma(max)} XP"
        for char in f"{humanize.intcomma(current)}{humanize.intcomma(max)}":
            pos[0] -= 13

        draw.text(tuple(pos), XP, font=font)

        # Profile Picture
        profile_picture = ImageOps.fit(
            profile_picture, profile_mask.size, centering=(0.5, 0.5)
        )
        profile_picture.putalpha(profile_mask)
        profile_picture = profile_picture.resize((131, 131))
        image.paste(profile_picture, (30, 34), profile_picture)

        # Name Text
        draw = pilmoji.Pilmoji(image)
        font = ImageFont.truetype("./assets/fonts/ArialCE.ttf", 30)
        name = user.name
        if len(name) > 15:
            name = f"{name[:12]}..."
        name = f"{name}#{user.discriminator}"
        draw.text((177, 73), name, font=font)

        image.save(buffer, format="png")
        buffer.seek(0)

        bar.close()
        image.close()
        profile_picture.close()
        profile_mask.close()
    return ImageResult(buffer, timer.time)


def mother():
    with Timer() as timer:
        buffer = io.BytesIO()
        img = Image.new("RGB", (500, 500), (0, 0, 0))
        frames = []

        for value in range(255)[::15]:
            color = img.getcolors()[0][1]
            thing = list(color)
            thing[random.randint(0, 2)] = value
            color = tuple(thing)
            img = Image.new("RGB", img.size, color)
            frames.append(img)

        frames[0].save(
            buffer,
            save_all=True,
            append_images=frames[1:],
            duration=5,
            format="gif",
            loop=0,
        )

        for frame in frames:
            frame.close()

        buffer.seek(0)
    return ImageResult(buffer, timer.time)

class Renders:
    leveling_card = leveling_card
    progress_bar = progress_bar
    mother = mother
    rounden = rounden
    welcome_card = welcome_card

async def render(render: property, *args, **kwargs):
    partial = functools.partial(render, *args, **kwargs)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial)

