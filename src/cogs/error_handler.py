import discord
from discord.ext import commands
import logging
from cogs.utils import constants as const
import os
import traceback
import datetime
import io

logger = logging.getLogger(__name__)


if os.getenv("ERROR_DM") is not None:
    error_dm: str = os.getenv("ERROR_DM")
    if error_dm.lower() in ("yes", "y", "true", "t", "1"):
        dm = True
    elif error_dm.lower() in ("no", "n", "false", "f", "0"):
        dm = False
    else:
        logger.warning("Invalid ERROR_DM value, defaulting to True")
        dm = True
else:
    dm = True


class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        await ctx.message.remove_reaction(const.OK, self.bot.user)
        error = getattr(error, 'original', error)
        if isinstance(error, commands.NSFWChannelRequired):
            await ctx.message.add_reaction(const.NSFW)
            # Only send meme response in the right discord server
            if ctx.guild.id == 461648348622094347:
                await ctx.send("IKKE I GENERAL DA! KUN I <#607395883239342080>")
            else:
                await ctx.send("This command is only available in channels marked NSFW")
        elif isinstance(error, commands.NotOwner):
            await ctx.message.add_reaction(const.NO)
            await ctx.send("You have to be the bot owner to use this command")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.message.add_reaction(const.NO)
            await ctx.send("This command is only available in a guild")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.message.add_reaction(const.NO)
            if len(error.missing_permissions) > 1:
                await ctx.send(f"You are missing the following permissions for this command: `{'`, `'.join(error.missing_permissions)}`")
            else:
                await ctx.send(f"You need the `{error.missing_permissions[0]}` permission to use this command")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.message.add_reaction(const.NO)
            if len(error.missing_permissions) > 1:
                await ctx.send(f"I am missing the following permissions for this command: `{'`, `'.join(error.missing_permissions)}`")
            else:
                await ctx.send(f"I need the `{error.missing_permissions[0]}` permission to use this command")
        elif not isinstance(error, commands.CommandNotFound):
            # Only error if not already handled
            matches = [const.NO, const.NSFW]
            for reaction in ctx.message.reactions:
                if any(x in reaction.emoji for x in matches):
                    return
            await ctx.message.add_reaction(const.NO)
            await ctx.send("Unknown error")
            logger.error(f'"{error}" in {ctx.guild.name}: {ctx.channel.name}')
            if dm is True:
                owner = self.bot.get_user(self.bot.owner_id)
                trace = traceback.format_exception(type(error), error, error.__traceback__)
                if "NoneType: None" in trace:
                    trace = str(error)
                if len(trace) < 1500:
                    await owner.send(
                        (f"**Guild:** {ctx.guild.name} **Channel:** {ctx.channel.name} "
                         f"**Command:** {ctx.command.name} "
                         f"**Time:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
                         f"[Message link]({ctx.message.jump_url})\n```\n{trace}\n```")
                    )
                else:
                    await owner.send(f"{ctx.command.name} errored in {ctx.guild.name}, {ctx.channel.name} at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                    await owner.send(file=discord.File(io.StringIO(trace), filename="traceback.txt"))
            traceback.print_exception(type(error), error, error.__traceback__)


def setup(bot: commands.bot):
    bot.add_cog(ErrorHandler(bot))
