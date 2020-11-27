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

# Check for and use dev environment variables
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

intents = discord.Intents().default()
intents.members = True

bot = commands.Bot(command_prefix="+", owner_id=ownerid, intents=intents)

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
async def on_command(ctx):
    logging.info(f"{ctx.message.author} called {ctx.command}")


@bot.event
async def on_command_error(ctx, error):
    await ctx.message.remove_reaction(ok, bot.user)
    logging.warning(error)
    if isinstance(error, commands.NSFWChannelRequired):
        await ctx.message.add_reaction(nsfw)
        # Only send meme response in the right discord server
        if ctx.guild.id == 461648348622094347:
            await ctx.send("IKKE I GENERAL DA! KUN I <#607395883239342080>")
        else:
            await ctx.send("This command is only available in channels marked NSFW")
    if isinstance(error, commands.NotOwner):
        await ctx.message.add_reaction(no)
        await ctx.send("You have to be the bot owner to use this command")


@bot.command(aliases=["pog"])
async def ping(ctx):
    ping = round(bot.latency * 1000)
    await ctx.send(f"{ping}ms")
    logging.info(f"{ping}ms")


@bot.command(aliases=["jasså"])
async def jassa(ctx, args):
    await ctx.message.add_reaction(ok)
    start_time = time.time()
    async with ctx.channel.typing():
        name = hashlib.md5(args.encode()).hexdigest()
        filename = "/jassa-bot/output/" + name + ".mp4"
        optimized = "/jassa-bot/output/optimized/" + name + ".gif"

        if os.path.isfile(optimized):
            logging.info("Gif exists, sending file")
            await ctx.send(file=discord.File(optimized))
        else:
            logging.info("Making new gif")
            video = VideoFileClip(os.path.abspath("media/jassa_template.mp4")).subclip(
                0, 3
            )

            txt_clip = (
                TextClip(
                    args, fontsize=33, color="white", font="ProximaNova-Semibold.otf"
                )
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
@commands.has_guild_permissions(move_members=True)
async def moveall(ctx, *, channel: discord.VoiceChannel):
    await ctx.message.add_reaction(ok)
    # TODO: Figure out how to set an alias for a channel, as of now this if statement doesn't do anything OR add command to add alias (save this to something? new command?)
    # * Stupid (possible) workaround to be able to use uhc alias, however removes possibility to just type names of channels
    # * channel = discord.utils.find(lambda x: x.id == int(args), ctx.guild.voice_channels)
    for members in ctx.message.author.voice.channel.members:
        await members.move_to(channel)
        logging.info(f"Moved {members} to {channel} in {ctx.guild}")


@moveall.error
async def moveall_error(ctx, error):
    await ctx.message.add_reaction(no)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "Missing voice channel ID/name to move to. Usage: `+moveall <vc id/name>`"
        )
    if isinstance(error, commands.ChannelNotFound):
        await ctx.send("Unable to find channel")
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "You don't have the required permissions for this command (Move Members)"
        )


@bot.command(aliases=["lb", "rolelb"])
async def roleleaderboard(ctx, arg: str = None):
    try:
        await ctx.message.add_reaction(ok)
        # ? Maybe use a switch statement here...
        if arg is None:
            limit = 11
        elif arg == "full":
            limit = -999999
        else:
            limit = int(arg) + 1
        members_list = ctx.guild.members
        roles = {}
        for member in members_list:
            roles[member.display_name] = len(member.roles)
        sorted_list = {
            k: v
            for k, v in sorted(roles.items(), key=lambda item: item[1], reverse=True)
        }
        embed = discord.Embed(colour=discord.Colour.gold())
        value_string = ""
        role_place = 1
        for item in sorted_list.items():
            if role_place == limit:
                break
            username = discord.utils.escape_markdown(item[0], ignore_links=False)
            value_string += f"{role_place}. {username}: {item[1]} roles\n"
            role_place += 1
        if len(value_string) <= 1024:
            embed.add_field(name="Role leaderboard", value=value_string)
            await ctx.send(embed=embed)
        else:
            await ctx.message.remove_reaction(ok, bot.user)
            await ctx.message.add_reaction(no)
            await ctx.send("Too many users to display, please try a lower value")
    except ValueError:
        await ctx.message.add_reaction(no)
        await ctx.message.remove_reaction(ok, bot.user)
        await ctx.send("Command only accepts either numbers or `full` as arguments")


@roleleaderboard.error
async def lb_error(ctx, error):
    # TODO: Figure out how to catch a Python error via .error instead of using try/catch
    await ctx.message.add_reaction(no)
    if isinstance(error, ValueError):
        await ctx.send("Command only accepts either numbers or `full` as arguments")
    else:
        await ctx.send("An error occurred")


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
