import discord
from discord.ext import commands
import datetime
import logging
import os
import psutil

logger = logging.getLogger(__name__)

# Set time the bot was loaded (used for uptime)
load_time = datetime.datetime.now()


class Meta(commands.Cog):
    """
    Commands for meta information (info about the bot)
    """
    # TODO: Custom help command
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["info", "stats"])
    async def about(self, ctx: commands.Context):
        """
        Returns a nice embed with info about the bot
        """

        embed = discord.Embed(color=0x039ea6)
        embed.set_author(name="Jasså Bot Info", icon_url=self.bot.user.avatar.url)
        embed.add_field(name=":crown: Owner:", value="Jøgen#0001")
        embed.add_field(name=":robot: Running commit:", value=self.get_git_commit())
        embed.add_field(name=":books: Library:", value=f"Novus {discord.__version__}")
        embed.add_field(name=":shield: Guilds:", value=len(self.bot.guilds))
        embed.add_field(name=":notebook_with_decorative_cover: Channels:", value=self.get_bot_channels(self))
        embed.add_field(name=":busts_in_silhouette: Users:", value=len(self.bot.users))
        embed.add_field(name=":envelope: Invite:", value=f"[Click here](https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=275364564048&scope=bot)")
        embed.add_field(name=":calendar_spiral: Uptime:", value=self.get_uptime())
        embed.add_field(name=":brain: Memory Usage:", value=f"{self.get_memory():.2f} MB")
        await ctx.send(embed=embed)

    def get_uptime():
        uptime_raw = datetime.datetime.now() - load_time
        seconds = uptime_raw.seconds
        minutes = seconds // 60
        hours = minutes // 60
        days = hours // 24
        weeks = days // 7
        # Make values readable
        uptime_str = ""
        if weeks > 0:
            uptime_str += f"{weeks}w "
        if days > 0:
            uptime_str += f"{days - (weeks * 7)}d "
        if hours > 0:
            uptime_str += f"{hours - (days * 24)}h "
        if minutes > 0:
            uptime_str += f"{minutes - (hours * 60)}m "
        if seconds > 0:
            uptime_str += f"{seconds - (minutes * 60)}s"
        # Only return the biggest 3 values
        return " ".join(uptime_str.split(" ")[:3])

    def get_git_commit():
        commit = os.getenv("GIT_COMMIT", "Unknown")
        logger.info(f"Git commit: {commit}")
        # If GIT_COMMIT is an empty string
        if commit == "":
            commit = "Unknown"
        if commit != "Unknown":
            # Convert to link and shorten hash
            short_hash = commit[:7]
            commit = f"[{short_hash}](https://github.com/Jorgen1040/jassa-bot/commit/{commit})"
        return commit

    def get_bot_channels(self):
        channel_count = 0
        for guild in self.bot.guilds:
            for channel in guild.channels:
                if channel.type == discord.ChannelType.text:
                    channel_count += 1
        return str(channel_count)

    def get_memory():
        process = psutil.Process(os.getpid())
        # Get memory usage in MB
        mem = process.memory_info().rss / 1024 / 1024
        return mem

    # def get_bot_info():
    #     with psutil.Process().oneshot() as proc:
    #         uptime = datetime.timedelta(seconds=datetime.datetime.now() - proc.create_time())
    #         cpu_time = datetime.timedelta(seconds=(cpu := proc.cpu_times().system + cpu.user))


def setup(bot: commands.Bot):
    bot.add_cog(Meta(bot))
