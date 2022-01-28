import discord
from discord.ext import commands
import os
from discord_together import DiscordTogether
import logging
import colorlog

# Environment variables
token = os.environ["BOT_TOKEN"]
ownerid = int(os.environ["OWNER_ID"])
tarkov_key = os.getenv("TARKOV_API")
prefix = os.getenv("PREFIX", "+")
logging_level = os.getenv("LOGGING_LEVEL", "INFO")


# Set up colorlog
colorlog.default_log_colors["DEBUG"] = "cyan"
colorlog.basicConfig(
    level=logging_level,
    format="%(log_color)s%(asctime)s - %(name)s - [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
# Remove spammy logging from discord
logging.getLogger("discord").setLevel(logging.WARNING)


intents = discord.Intents.default()
intents.members = True


bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(prefix),
    owner_id=ownerid,
    intents=intents,
    allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=False)
)


# Cogs to load
initial_extensions = [
    "cogs.error_handler",
    "cogs.meta",
    "cogs.fun",
    "cogs.utility",
    "cogs.tarkov",
    "cogs.nsfw"
]


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(f"{prefix}help"))
    bot.togetherControl = await DiscordTogether(token)


if __name__ == '__main__':
    # Load cogs
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            logger.error(f"Failed to load extension {extension}: {e.name}")

    bot.run(token)
