import re
from typing import Optional
import discord
from discord.ext import commands
from core import Amyrin

FORMAT_REGEX = re.compile(r"{([^{}]+)}")

class HelpCommand(commands.DefaultHelpCommand):
    def _format_page(self, page: str) -> str:
        FORMAT_DICT = {
            "prefix": self.context.clean_prefix
        }
        
        matches = FORMAT_REGEX.findall(page)
        if not matches:
            return page
        
        exists = {}
        
        for match in matches:
            if match in FORMAT_DICT.keys():
                exists[match] = FORMAT_DICT.get(match)
                
        return page.format(**exists)
            
    
    @discord.utils.copy_doc(commands.DefaultHelpCommand.send_pages)
    async def send_pages(self) -> None:
        destination = self.get_destination()
        for page in self.paginator.pages:
            fmt_page = self._format_page(page)
            await destination.send(fmt_page)
            
    async def command_callback(
        self, ctx: commands.Context, /, *, command: Optional[str] = None
    ) -> None:
        """base command_callback function but made case insensitive
        """
        
        await self.prepare_help_command(ctx, command)

        bot: commands.Bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        cog = discord.utils.find(lambda x: x[0].lower() == command, bot.cogs.items())
        if cog is not None:
            return await self.send_cog_help(cog[1])

        maybe_coro = discord.utils.maybe_coroutine

        keys = command.split(" ")
        cmd = bot.all_commands.get(keys[0].lower())
        if cmd is None:
            string = await maybe_coro(
                self.command_not_found, self.remove_mentions(keys[0])
            )
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)  # type: ignore
            except AttributeError:
                string = await maybe_coro(
                    self.subcommand_not_found, cmd, self.remove_mentions(key)
                )
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(
                        self.subcommand_not_found, cmd, self.remove_mentions(key)
                    )
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)
        
    
async def setup(bot: Amyrin):
    bot._original_help_command = bot.help_command # type: ignore
    bot.help_command = HelpCommand()
    
async def teardown(bot: Amyrin):
    bot.help_command = getattr(bot, "_original_help_command", None)