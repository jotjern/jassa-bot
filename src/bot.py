from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import os
import logging
import coloredlogs
import discord
from discord.ext import commands
import hashlib
import rule34
import requests
from bs4 import BeautifulSoup as bs
import random
import time
import sys
import json
import stat
from urllib.parse import quote
import traceback
import io
from datetime import datetime


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
coloredlogs.install(
    level="INFO",
    fmt="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
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
    if not os.path.isfile("/jassa-bot/aliases.json"):
        logging.info("Missing aliases.json, making file")
        with open("/jassa-bot/aliases.json", "a") as f:
            f.write("{}")
        os.chmod("/jassa-bot/aliases.json", stat.S_IRWXO)
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
    if not isinstance(error, commands.CommandNotFound):
        logging.error(f'"{error}" in {ctx.guild.name}: {ctx.channel.name}')
        owner = bot.get_user(int(ownerid))
        trace = traceback.format_exc()
        if len(trace) < 2000:
            await owner.send(f"**Guild:** {ctx.guild.name} **Channel:** {ctx.channel.name} **Time:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n```\n{trace}\n```")
        else:
            await owner.send(f"Errored in {ctx.guild.name}, {ctx.channel.name} at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            await owner.send(file=discord.File(io.StringIO(trace), filename="traceback.txt"))
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
        logging.info(f"Successfully generated gif with {args} in {stop_time-start_time} seconds")


@jassa.error
async def jassa_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send("Mangler navn (eller noe annet).\nRiktig bruk: `+jasså <navn>`")


@bot.command(aliases=["q"])
async def quest(ctx, *, args: str):
    await ctx.message.add_reaction(ok)
    # Get quests, trades and hideout importance
    # Get images and display it in an embed
    # query = args.replace(" ", "+")
    query = quote(args)
    search_url = "https://escapefromtarkov.gamepedia.com/Special:Search?search=" + query
    r = requests.get(search_url)
    results = bs(r.text, "html.parser")
    if results.find("a", class_="unified-search__result__title"):
        result = results.find("a", class_="unified-search__result__title").get("href")
        r = requests.get(result)
        page = bs(r.text, "html.parser")
    else:
        page = results
    title = page.find("h1").get_text()
    if "Search results for" in title:
        await ctx.send(f"Unable to find {discord.utils.escape_markdown(args)}, try being more specific.")
        return
    embed = discord.Embed(title=title, url=r.url)
    if page.find(id="Quests"):
        quests = page.find(id="Quests").find_parent("h2").find_next_sibling("ul").find_all("li")
        quests_string = ""
        for quest in quests:
            quest_name = quest.find("a").get_text()
            quest_url = "https://escapefromtarkov.gamepedia.com" + quest.find("a").get("href")
            text = quest.get_text()
            if "in raid" in text:
                text = text.replace("in raid", "**in raid**")
            text = text.replace(quest_name, f"[{quest_name}]({quest_url})")
            quests_string += text + "\n"
        embed.add_field(name="Quests", value=quests_string, inline=False)
    if page.find(id="Hideout"):
        uses = page.find(id="Hideout").find_parent("h2").find_next_sibling("ul").find_all("li")
        uses_string = ""
        for use in uses:
            uses_string += use.get_text() + "\n"
        embed.add_field(name="Hideout", value=uses_string, inline=False)
    if page.find(id="Trading"):
        trades = page.find(id="Trading").find_parent("h2").find_next_sibling("table").find_all("tr")
        trades_string = ""
        for trade in trades:
            th = trade.find_all("th")
            trader = th[2].get_text().strip()
            barter_in = th[0].get_text().strip()
            barter_out = th[4].get_text().strip()
            trades_string += f"**{trader}:** {barter_in} -> {barter_out} \n"
        embed.add_field(name="Trading", value=trades_string, inline=False)
    if page.find(id="Crafting"):
        crafts = page.find(id="Crafting").find_parent("h2").find_next_sibling("table").find_all("tr")
        crafts_string = ""
        for craft in crafts:
            th = craft.find_all("th")
            crafter = th[2].get_text().strip()
            craft_in = th[0].get_text().strip()
            craft_out = th[4].get_text().strip()
            crafts_string += f"**{crafter}:** {craft_in} -> {craft_out} \n"
        embed.add_field(name="Crafting", value=crafts_string, inline=False)
    icon = None
    if page.find("td", class_="va-infobox-icon"):
        icon = page.find("td", class_="va-infobox-icon").find("img").get("src")
    else:
        # TODO: Make it so that it retries until it finds an item
        if page.find("td", class_="va-infobox-mainimage-image"):
            icon = page.find("td", class_="va-infobox-mainimage-image").find("img").get("src")
        embed.set_footer(text="This might not be an item")

    # TODO: Fix embed being too big (larger than 1024)
    if icon is not None:
        embed.set_thumbnail(url=icon)
    await ctx.send(embed=embed)


@quest.error
async def quest_error(ctx, error):
    await ctx.message.add_reaction(no)
    await ctx.send("Unknown error when processing command. ||<@140586848819871744>||")


@bot.command(aliases=["mv"])
@commands.has_guild_permissions(move_members=True)
async def moveall(ctx, *, channel: str):
    await ctx.message.add_reaction(ok)
    with open("/jassa-bot/aliases.json", "r") as f:
        aliases = json.load(f)
    try:
        channel = aliases[str(ctx.guild.id)][channel]
        channel = bot.get_channel(int(channel))
    except KeyError:
        channel = discord.utils.find(lambda x: x.name == channel, ctx.guild.voice_channels)

    for member in ctx.message.author.voice.channel.members:
        await member.move_to(channel)
        logging.info(f"Moved {member} to {channel} in {ctx.guild}")


@moveall.error
async def moveall_error(ctx, error):
    await ctx.message.add_reaction(no)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing voice channel ID/name to move to. Usage: `+moveall <vc id/name>`")
    if isinstance(error, commands.ChannelNotFound):
        await ctx.send("Unable to find channel")
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions for this command (Move Members)")


@bot.command(aliases=["mvalias", "movealias"])
@commands.has_guild_permissions(administrator=True)
async def alias(ctx, alias: str, channel: discord.VoiceChannel = None):
    await ctx.message.add_reaction(ok)
    with open("/jassa-bot/aliases.json", "r") as f:
        aliases = json.load(f)
    try:
        aliases[str(ctx.guild.id)]
    except KeyError:
        print("Guild ID not already in list, adding it")
        aliases[str(ctx.guild.id)] = {}

    if channel is None:
        await ctx.send(f"Removed alias for channel ID {aliases[str(ctx.guild.id)][alias]}")
        aliases[str(ctx.guild.id)].pop(alias)
    else:
        alias_list = {}
        alias_list[alias] = str(channel.id)
        aliases[str(ctx.guild.id)].update(alias_list)
        await ctx.send("Added alias for channel")

    with open("/jassa-bot/aliases.json", "w") as f:
        json.dump(aliases, f, indent=4)


@alias.error
async def alias_error(ctx, error):
    await ctx.message.add_reaction(no)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing alias and/or channel ID. Usage: `+alias <alias> <channel ID/name in quotes>`")
    if isinstance(error, commands.ChannelNotFound):
        await ctx.send("Unable to find channel")


@bot.command(aliases=["lb", "rolelb"])
async def roleleaderboard(ctx, arg: str = None):
    try:
        await ctx.message.add_reaction(ok)
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
        sorted_list = {k: v for k, v in sorted(roles.items(), key=lambda item: item[1], reverse=True)}
        embed = discord.Embed(colour=discord.Colour.gold())
        value_string = ""
        role_place = 1
        for item in sorted_list.items():
            if role_place == limit:
                break
            username = discord.utils.escape_markdown(item[0], ignore_links=False)
            current = f"{role_place}. {username}: {item[1]} roles\n"
            if len(value_string) + len(current) >= 1024:
                await ctx.send("Too many users, displaying as many as possible")
                break
            else:
                value_string += current
            role_place += 1
        embed.add_field(name="Role leaderboard", value=value_string)
        await ctx.send(embed=embed)
    except ValueError:
        await ctx.message.add_reaction(no)
        await ctx.message.remove_reaction(ok, bot.user)
        await ctx.send("Command only accepts either numbers or `full` as arguments")


@roleleaderboard.error
async def lb_error(ctx, error):
    # TODO: Figure out how to catch a Python error via .error instead of using try/catch
    await ctx.message.add_reaction(no)


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
        await ctx.send("Missing tags to search for.\nUsage: `+r34/rule34 <tags>` or for multiple tags `+r34/rule34 <tag1> <tag2> ...`")


@bot.command()
@commands.is_owner()
async def close(ctx):
    ctx.add_reaction("👋")
    await bot.close()


bot.run(token)
