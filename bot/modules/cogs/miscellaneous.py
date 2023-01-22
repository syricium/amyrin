import os
import pathlib
from datetime import datetime

import discord
import humanize
import psutil
from discord.ext import commands

from core.bot import onyx


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: onyx = bot

    @commands.hybrid_command(name="ping", description="Get the ping of the bot")
    async def ping(self, ctx: commands.Context | discord.Interaction):
        websocket = round(self.bot.latency * 1000, 2)

        em = discord.Embed(title="Latency", color=self.bot.color)
        em.add_field(
            name=f"Websocket",
            value=f"```diff\n{websocket}ms```",
        )
        
        await ctx.send(embed=em)

    @commands.hybrid_command(name="about", description="Get info about oynx's file stats and host stats")
    @commands.cooldown(1, 20)
    async def about(self, ctx: commands.Context | discord.Interaction):
        path = pathlib.Path(os.getcwd())

        def line_count():
            files = classes = funcs = comments = lines = characters = 0
            directories = ["cogs", "core", "utils"]
            for directory in directories:
                p = pathlib.Path(path).joinpath(directory)
                for f in p.rglob(f"*.py"):
                    files += 1
                    with open(f) as of:
                        characters += len(open(f).read())
                        for line in of.readlines():
                            line = line.strip()
                            if line.startswith("class"):
                                classes += 1
                            if line.startswith("def"):
                                funcs += 1
                            if line.startswith("async def"):
                                funcs += 1
                            if "#" in line:
                                comments += 1
                            lines += 1
            return files, classes, funcs, comments, lines, characters

        if ctx.interaction:
            await ctx.interaction.response.defer()
        else:
            await ctx.typing()

        (
            files,
            classes,
            funcs,
            comments,
            lines,
            characters,
        ) = await self.bot.loop.run_in_executor(None, line_count)

        pid = os.getpid()
        process = psutil.Process(pid)

        delta_uptime = datetime.utcnow() - self.bot.uptime
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        em = discord.Embed(description=self.bot.description, color=self.bot.color)
        em.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        em.add_field(name="Developer", value=str(self.bot.owner))
        em.add_field(name="Uptime", value=f"{days}d, {hours}h, {minutes}m, {seconds}s")
        em.add_field(name="​", value="​")

        f_stats = {
            "Characters": characters,
            "Functions": funcs,
            "Comments": comments,
            "Classes": classes,
            "Files": files,
            "Lines": lines,
        }

        sorted_names = sorted(f_stats.keys())
        sorted_stats = {
            k: v
            for k, v in sorted(f_stats.items(), key=lambda item: item[1], reverse=True)
        }
        largest = sorted_names[-1]
        f_stats_fmt = {}
        for name, stat in sorted_stats.items():
            new_name = name + " ".join(range(len(largest) - len(name)))
            f_stats_fmt[new_name] = stat

        f_stats_str = "\n".join(f"{k}: {v}" for k, v in f_stats_fmt.items())

        em.add_field(
            name="File Statistics",
            value=f"""
```py
{f_stats_str}
```
            """,
            inline=True,
        )
        em.add_field(
            name="Host Statistics",
            value=f"""
```py
Process: {process.name()} ({process.pid})
Process started: {humanize.naturaltime(datetime.fromtimestamp(int(process.create_time())))}
CPU Usage: {psutil.cpu_percent()}%
Memory Usage: {psutil.virtual_memory().percent}%
Disk Used: {psutil.disk_usage(str(path)).percent}%
```
""",
        )
        
        await ctx.send(embed=em)


async def setup(bot):
    await bot.add_cog(Miscellaneous(bot))
