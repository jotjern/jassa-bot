import discord
from discord.ext import commands
import logging
from cogs.utils import constants as const
from discord_together.discordTogetherMain import defaultApplications


logger = logging.getLogger(__name__)


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        ping = round(self.bot.latency * 1000)
        await ctx.send(f"{ping}ms")
        logger.info(f"{ping}ms")

    @commands.command(aliases=["activites", "activity"])
    @commands.guild_only()
    async def together(self, ctx: commands.Context, name: str):
        if ctx.author.voice is None:
            await ctx.message.add_reaction(const.NO)
            return await ctx.send("You have to be in a voice channel.")
        try:
            link = await self.bot.togetherControl.create_link(ctx.author.voice.channel.id, name)
        except discord.InvalidArgument as e:
            await ctx.message.add_reaction(const.NO)
            return await ctx.send(str(e))
        await ctx.send(f"Click the blue link! (Not the Play button)\n{link}")
        await ctx.message.add_reaction(const.OK)

    @together.error
    async def together_error(ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.message.add_reaction(const.NO)
            app_list = []
            for app in defaultApplications:
                app_list.append(f"`{app}`")
            await ctx.send(
                "Please specify what application you want to use.\n"
                "Available applications:\n" + ", ".join(app_list)
            )


def setup(bot: commands.Bot):
    bot.add_cog(Utility(bot))
