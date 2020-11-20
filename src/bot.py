from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import os
import logging
import discord
from discord.ext import commands
import hashlib
import rule34
import requests
from bs4 import BeautifulSoup as bs
import random
import time
import sys
from dotenv import load_dotenv

if os.path.isfile("./.env"):
    print("[DEV] .env file found, using them")
    load_dotenv()
token = os.environ["BOT_TOKEN"]
ownerid = os.environ["OWNER_ID"]

logger = logging.getLogger("discord")
logger.setLevel(logging.CRITICAL)
logging.Formatter()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

rule34 = rule34.Sync()

bot = commands.Bot(command_prefix="+", owner_id=ownerid)

# Emojis :)
ok = "✅"
no = "❌"
nsfw = "🔞"

# Check for linux and folders
if sys.platform != "linux":
    logging.warning(
        "Bot is not made for non Linux installations. Persistence may not work"
    )
try:
    if os.path.isdir("/jassa-bot/output/optimized"):
        logging.info("All files are correct :). Persistence is enabled")
    else:
        os.makedirs("/jassa-bot/output/optimized")
        logging.info("Made output folders, persistence is now enabled")
except PermissionError as e:
    logging.warning(e)
    logging.warning(
        "Permission denied for /jassa-bot directory. Persistence will not work!"
    )


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game("+jasså"))
    logging.info(f"Logged in as {bot.user}")


@bot.event
async def on_command_error(ctx, error):
    logging.warning(error)
    if isinstance(error, commands.NSFWChannelRequired):
        await ctx.message.add_reaction(nsfw)
        # Only send meme response in the right discord server
        if ctx.guild.id == 461648348622094347:
            await ctx.send("IKKE I GENERAL DA! KUN I <#607395883239342080>")
        else:
            await ctx.send("This command is only available in channels marked NSFW")


@bot.command(aliases=["pog"])
async def ping(ctx):
    ping = round(bot.latency * 1000)
    await ctx.send(f"{ping}ms")
    logging.info(f"{ping}ms")


@bot.command(aliases=["jasså"])
async def jassa(ctx, args):
    await ctx.message.add_reaction(ok)
    name = hashlib.md5(args.encode()).hexdigest()
    filename = "/jassa-bot/output/" + name + ".mp4"
    optimized = "/jassa-bot/output/optimized/" + name + ".gif"

    if os.path.isfile(optimized):
        logging.info("Gif exists, sending file")
        await ctx.send(file=discord.File(optimized))
    else:
        logging.info("Making new gif")
        start_time = time.time()
        video = VideoFileClip(os.path.abspath("media/jassa_template.mp4")).subclip(0, 3)

        txt_clip = (
            TextClip(args, fontsize=33, color="white", font="ProximaNova-Semibold.otf")
            .set_position((160, 655))
            .set_duration(3)
        )

        result = CompositeVideoClip([video, txt_clip])
        result.write_videofile(filename)
        # New better ffmpeg options
        os.system(
            "ffmpeg -y -i "
            + filename
            + " -i media/palette.png -lavfi 'fps=19,scale=480:-1:flags=lanczos,paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle' "
            + optimized
        )

        await ctx.send(file=discord.File(optimized))
        stop_time = time.time()
        logging.info(
            f"Successfully generated gif with {args} in {stop_time-start_time} seconds"
        )


@jassa.error
async def jassa_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send("Mangler navn (eller noe annet).\nRiktig bruk: `+jasså <navn>`")

@bot.command()
async def move(ctx, args):
    # TODO: Make this command move ALL users in same vc as the one giving command, also require move members permission in Discord server
    await ctx.message.add_reaction(ok)
    user = ctx.message.author
    channel = discord.utils.find(lambda x: x.id == int(args), ctx.guild.voice_channels)
    logging.info(channel)
    await user.move_to(channel)

@bot.command(aliases=["rule34"])
@commands.is_nsfw()
async def r34(ctx, *, tags):
    # Check for illegal tags
    if ("cub" or "loli" or "shota" or "child" or "underage" or "shotacon") in tags:
        await ctx.message.add_reaction(nsfw)
        await ctx.send("NEI TOS")
    else:
        logging.info(f"Rule34: Searching for {tags}")
        await ctx.message.add_reaction(ok)
        xml_url = rule34.URLGen(tags + "+-cub -loli -underage -shotacon -shota")
        logging.info(f"Got API url for {tags}: {xml_url}")
        xml = bs(requests.get(xml_url).text, "lxml")
        urls = []
        for post in xml.findAll("post"):
            file_url = post.attrs["file_url"]
            urls += [file_url]
        count = len(urls)
        count_text = str(count)
        if count >= 100:
            count_text = "100+"
        if count >= 1:
            random_url = random.choice(urls)
            await ctx.send(f"Found {count_text} results, here is one of them")
            await ctx.send(random_url)
            logging.info(f"Rule34: Sent {random_url} with tag(s): {tags}")
        else:
            logging.info(f"Rule34: No posts were found with the tag(s): {tags}")
            await ctx.send(f"No posts were found with the tag(s): {tags}")


@r34.error
async def r34_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send(
            "Missing tags to search for.\nUsage: `+r34/rule34 <tags>` or for multiple tags `+r34/rule34 <tag1> <tag2> ...`"
        )


@bot.command()
@commands.is_owner()
async def close(ctx):
    ctx.add_reaction("👋")
    await bot.close()


bot.run(token)
