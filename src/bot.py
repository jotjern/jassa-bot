import asyncio
import hashlib
import base64
import io
import json
import logging
import os
import random
import sys
import time
import traceback
from datetime import datetime
from distutils.util import strtobool
from urllib.parse import quote

import colorlog
import discord
import ffmpeg
import pymongo
import requests
import rule34
from bs4 import BeautifulSoup as bs
from discord.errors import HTTPException
from discord.ext import commands
from discord_together import DiscordTogether
from pymongo.errors import ServerSelectionTimeoutError

token = os.environ["BOT_TOKEN"]
ownerid = int(os.environ["OWNER_ID"])
tarkov_key = os.getenv("TARKOV_API")
if os.getenv("ERROR_DM") is not None:
    dm = bool(strtobool(os.getenv("ERROR_DM")))
else:
    dm = True
prefix = os.getenv("PREFIX", "+")
logging_level = os.getenv("LOGGING_LEVEL", "INFO")

# Disable logging from discord.py
logging.getLogger("discord").setLevel(logging.CRITICAL)
# Set up colorlog
handler = logging.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    fmt="%(log_color)s%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logger = logging.getLogger("bot")
logger.setLevel(logging_level)
logger.addHandler(handler)


rule34 = rule34.Sync()

intents = discord.Intents().default()
intents.members = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or(prefix), owner_id=ownerid, intents=intents)

# Emojis :)
ok = "✅"
no = "❌"
nsfw = "🔞"


# Connect to MongoDB and handle migration/creation of database
db_client = pymongo.MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=5000)

db = db_client.jasså
servers_coll = db.servers


async def add_servers_to_db():
    new_servers = []
    await bot.wait_until_ready()
    for server in bot.guilds:
        new_servers.append({
            "_id": server.id,
            "nickname_log_channel": None,
            "aliases": {},
        })
    insert_result = servers_coll.insert_many(new_servers, ordered=False)
    logger.info(f"Added {len(insert_result.inserted_ids)} servers to database")
    if len(bot.guilds) != len(insert_result.inserted_ids):
        logger.warning("Some servers were not added to the database!")


async def init_db():
    db_names = db_client.list_database_names()
    if "jasså" in db_names:
        logger.info("Connected to MongoDB")
    else:
        if os.path.isfile("/jassa-bot/aliases.json") or os.path.isfile("/jassa-bot/servers.json"):
            logger.warning("Old json files found, migrating to new MongoDB database")
            await add_servers_to_db()
            # Migrate stuff
            with open("/jassa-bot/servers.json", "r") as f:
                servers = json.load(f)
            for server in servers:
                servers_coll.update_one(
                    {"_id": int(server)},
                    {"$set": {"nickname_log_channel": servers[server]["nickname_log_channel"]}},
                    upsert=True
                )
            with open("/jassa-bot/aliases.json", "r") as f:
                aliases = json.load(f)
            for server in aliases:
                new_aliases = {}
                for alias, channel_id in aliases[server].items():
                    new_aliases[alias] = int(channel_id)
                servers_coll.update_one(
                    {"_id": int(server)},
                    {"$set": {"aliases": new_aliases}},
                    upsert=True
                )
            os.remove("/jassa-bot/servers.json")
            os.remove("/jassa-bot/aliases.json")
            logger.info("Successfully migrated to new MongoDB database, and removed old files")
        else:
            logger.warning("MongoDB database not found, creating new database")
            # Add all servers to database
            await add_servers_to_db()


# TODO: Add a task that selects a random user to change server icon
# TODO: Add pin command (custom pin channel, that works over the 50 cap)


if tarkov_key is not None:
    tarkov_market = True
    logger.info("Tarkov API enabled. (from https://tarkov-market.com)")
else:
    tarkov_market = False
    logger.warning("No tarkov-market API key found, price of items won't be available")

# Check for linux and folders
if sys.platform != "linux":
    logger.warning("Bot is not made for non Linux installations. Persistence may not work")
try:
    if os.path.isdir("/jassa-bot/output/optimized"):
        logger.info("All files are correct :). Persistence is enabled")
    else:
        os.makedirs("/jassa-bot/output/optimized")
        logger.info("Made output folders, persistence is now enabled")
except PermissionError as e:
    logger.warning(e)
    logger.warning("Permission denied for /jassa-bot directory. Persistence will not work!")


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(f"{prefix}jasså"))
    bot.togetherControl = await DiscordTogether(token)
    logger.info(f"Logged in as {bot.user}")
    # TODO: Rework this
    try:
        await init_db()
    except ServerSelectionTimeoutError:
        logger.critical("Could not connect to MongoDB")


@bot.event
async def on_guild_join(guild: discord.Guild):
    db.servers.insert_one({
        "_id": guild.id,
        "nickname_log_channel": None,
        "aliases": {},
    })
    logger.info(f"Joined new guild: {guild.name}")


@bot.event
async def on_guild_remove(guild: discord.Guild):
    db.servers.delete_one({"_id": guild.id})
    logger.info(f"Removed from guild: {guild.name}")


@bot.event
async def on_command(ctx):
    logger.info(f"{ctx.message.author} called {ctx.command}")


@bot.event
async def on_command_error(ctx, error):
    await ctx.message.remove_reaction(ok, bot.user)
    error = getattr(error, 'original', error)
    if isinstance(error, commands.NSFWChannelRequired):
        await ctx.message.add_reaction(nsfw)
        # Only send meme response in the right discord server
        if ctx.guild.id == 461648348622094347:
            await ctx.send("IKKE I GENERAL DA! KUN I <#607395883239342080>")
        else:
            await ctx.send("This command is only available in channels marked NSFW")
    elif isinstance(error, commands.NotOwner):
        await ctx.message.add_reaction(no)
        await ctx.send("You have to be the bot owner to use this command")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.message.add_reaction(no)
        await ctx.send("This command is only available in a guild")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.message.add_reaction(no)
        if len(error.missing_perms) > 1:
            await ctx.send(f"You are missing the following permissions for this command: `{'`, `'.join(error.missing_perms)}`")
        else:
            await ctx.send(f"You need the `{error.missing_perms[0]}` permission to use this command")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.message.add_reaction(no)
        if len(error.missing_perms) > 1:
            await ctx.send(f"I am missing the following permissions for this command: `{'`, `'.join(error.missing_perms)}`")
        else:
            await ctx.send(f"I need the `{error.missing_perms[0]}` permission to use this command")
    elif not isinstance(error, commands.CommandNotFound):
        # Only error if not already handled
        matches = [no, nsfw]
        for reaction in ctx.message.reactions:
            if any(x in reaction.emoji for x in matches):
                return
        await ctx.message.add_reaction(no)
        await ctx.send("Unknown error")
        logger.error(f'"{error}" in {ctx.guild.name}: {ctx.channel.name}')
        if dm is True:
            owner = bot.get_user(int(ownerid))
            trace = traceback.format_exception(type(error), error, error.__traceback__)
            if "NoneType: None" in trace:
                trace = str(error)
            if len(trace) < 2000:
                await owner.send(
                    (f"**Guild:** {ctx.guild.name} **Channel:** {ctx.channel.name}"
                     f"**Command:** {ctx.command.name}"
                     f"**Time:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                     f"[Message link]({ctx.message.jump_url})\n```\n{trace}\n```")
                )
            else:
                await owner.send(f"{ctx.command.name} errored in {ctx.guild.name}, {ctx.channel.name} at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                await owner.send(file=discord.File(io.StringIO(trace), filename="traceback.txt"))
        traceback.print_exception(type(error), error, error.__traceback__)


@bot.command(aliases=["pog"])
async def ping(ctx):
    ping = round(bot.latency * 1000)
    await ctx.send(f"{ping}ms")
    logger.info(f"{ping}ms")


@bot.command(aliases=["jasså"])
async def jassa(ctx, args):
    await ctx.message.add_reaction(ok)
    async with ctx.channel.typing():
        name = hashlib.md5(args.encode()).hexdigest()
        filename = "/jassa-bot/output/" + name + ".mp4"
        optimized = "/jassa-bot/output/optimized/" + name + ".gif"

        if os.path.isfile(optimized):
            logger.info("Gif exists, sending file")
            await ctx.send(file=discord.File(optimized))
        else:
            start_time = time.time()
            logger.info("Making new gif")
            # Generate mp4 with text
            try:
                (
                    ffmpeg
                    .input('media/template.mp4')
                    .drawtext(fontfile="ProximaNova-Semibold.otf", text=args, x=160, y=656, fontsize=32.5, fontcolor="white", enable="between(t,0.5,5)")
                    .filter('fps', fps=19)
                    .filter('scale', "400", "trunc(ow/a/2)*2", flags="lanczos")
                    .output(filename)
                    .run(quiet=True)
                )
            except ffmpeg.Error as e:
                print('stdout:', e.stdout.decode('utf8'))
                print('stderr:', e.stderr.decode('utf8'))
                raise e
            # Convert mp4 to gif
            logger.info("Converting mp4 to gif")
            try:
                (
                    ffmpeg
                    .filter([
                        ffmpeg.input(filename),
                        ffmpeg.input("media/palette.png")
                    ],
                        filter_name="paletteuse",
                        dither="bayer"
                    )
                    .filter("fps", fps=19, round="up")
                    .output(optimized)
                    .run(quiet=True)
                )
            except ffmpeg.Error as e:
                print("stdout:", e.stdout.decode("utf8"))
                print("stderr:", e.stderr.decode("utf8"))
                raise e
            logger.info(f"Successfully generated gif with {args} in {time.time()-start_time} seconds")

            os.remove(filename)
            await ctx.send(file=discord.File(optimized))


@jassa.error
async def jassa_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send(f"Mangler navn (eller noe annet).\nRiktig bruk: `{prefix}jasså <navn>`")


@bot.command(aliases=["jassåaudio", "ja"])
async def jassaaudio(ctx, args, voice: str = "en_us_001"):
    await ctx.message.add_reaction(ok)
    async with ctx.channel.typing():
        name = hashlib.md5(args.encode()).hexdigest()
        filename = "/jassa-bot/output/" + name + ".mp4"
        mp3 = "/jassa-bot/output/" + name + ".mp3"
        out = "/jassa-bot/output/" + name + "_" + voice + ".mp4"

        if os.path.isfile(out):
            logger.info("mp4 exists, sending file")
            await ctx.send(file=discord.File(out))
        else:
            start_time = time.time()
            logger.info("Making new mp4")
            # Generate mp4 with text
            try:
                (
                    ffmpeg
                    .input('media/template.mp4')
                    .drawtext(fontfile="ProximaNova-Semibold.otf", text=args, x=160, y=656, fontsize=32.5, fontcolor="white", enable="between(t,0.5,5)")
                    .filter('fps', fps=19)
                    .filter('scale', "400", "trunc(ow/a/2)*2", flags="lanczos")
                    .output(filename)
                    .run(quiet=True, overwrite_output=True)
                )
            except ffmpeg.Error as e:
                print('stdout:', e.stdout.decode('utf8'))
                print('stderr:', e.stderr.decode('utf8'))
                raise e
            # Get audio an add it to mp4 (https://github.com/oscie57/tiktok-voice)
            tts_text = quote(f"Jasså {args} er du gira?")

            tts_url = f"https://api16-normal-useast5.us.tiktokv.com/media/api/text/speech/invoke/?text_speaker={voice}&req_text={tts_text}&speaker_map_type=0"

            r = requests.post(tts_url)

            vstr = [r.json()["data"]["v_str"]][0]
            msg = [r.json()["message"]][0]

            if msg != "success":
                logger.warning(f"{msg}")
                await ctx.message.remove_reaction(ok, bot.user)
                await ctx.message.add_reaction(no)
                await ctx.send(f"{msg}")
                return

            b64d = base64.b64decode(vstr)

            with open(mp3, "wb") as f:
                f.write(b64d)

            input_vid = ffmpeg.input(filename)
            input_audio = ffmpeg.input(mp3)

            try:
                (
                    ffmpeg
                    .concat(input_vid, input_audio, v=1, a=1)
                    .output(out)
                    .run(quiet=True, overwrite_output=True)
                )
            except ffmpeg.Error as e:
                print('stdout:', e.stdout.decode('utf8'))
                print('stderr:', e.stderr.decode('utf8'))
                raise e

            logger.info(
                f"Successfully generated mp4 with audio {args} in {time.time()-start_time} seconds")

            os.remove(filename)
            os.remove(mp3)
            await ctx.send(file=discord.File(out))


@jassaaudio.error
async def jassaaudio_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send(f"Mangler navn (eller noe annet).\nRiktig bruk: `{prefix}jassåaudio <navn>`")


# TODO: This only works with Novus
# @bot.command(
#     application_command_meta=commands.ApplicationCommandMeta(
#         options=[
#             discord.ApplicationCommandOption(
#                 name="text",
#                 type=discord.ApplicationCommandOptionType.string,
#                 description="The text to be read aloud by TikTok TTS"
#             ),
#             discord.ApplicationCommandOption(
#                 name="voice",
#                 type=discord.ApplicationCommandOptionType.string,
#                 description="The voice to be used by TikTok TTS",
#                 default="en_us_001",
#                 required=False,
#                 choices=
#             )
#         ]
#     )
# )
# async def tts(ctx, text: str, voice: str):
#     await ctx.send("Waow")
#
#
# async def main():
#     await bot.login(token)
#     await bot.register_application_commands()
#     await bot.connect()


@bot.command(aliases=["activites", "activity"])
@commands.guild_only()
async def together(ctx, name: str):
    if ctx.author.voice is None:
        await ctx.message.add_reaction(no)
        return await ctx.send("You have to be in a voice channel.")
    try:
        link = await bot.togetherControl.create_link(ctx.author.voice.channel.id, name)
    except discord.InvalidArgument as e:
        await ctx.message.add_reaction(no)
        return await ctx.send(str(e))
    await ctx.send(f"Click the blue link! (Not the Play button)\n{link}")
    await ctx.message.add_reaction(ok)


@together.error
async def together_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        app_list = []
        for app in DiscordTogether.default_choices:
            app_list.append(f"`{app}`")
        await ctx.send(
            "Please specify what application you want to use.\n"
            "Available applications:\n" + ", ".join(app_list)
        )


@bot.command()
@commands.guild_only()
@commands.bot_has_guild_permissions(manage_nicknames=True)
async def setnick(ctx, member: discord.Member, *, nickname: str = None):
    old_nick = member.display_name
    if nickname is not None and len(nickname) > 32:
        await ctx.message.add_reaction(no)
        return await ctx.send("Nickname can't be longer than 32 characters")
    if member == ctx.author and ctx.author.guild_permissions.manage_nicknames is False:
        await ctx.message.add_reaction(no)
        return await ctx.send("You can't change your own nickname")
    if member == ctx.guild.owner:
        await ctx.message.add_reaction(no)
        return await ctx.send("You can't change the server owner's name. (Discord doesn't allow it)")
    try:
        await member.edit(nick=nickname)
    except discord.Forbidden:
        await ctx.message.add_reaction(no)
        return await ctx.send("Missing permissions to change that user's nickname. Make sure my role is above theirs.")
    await ctx.message.add_reaction(ok)

    # Send to log
    server = db.servers.find_one({"_id": ctx.guild.id})
    log_id = server["nickname_log_channel"]
    if log_id is None:
        # If no log channel is set, just return
        return
    log_channel = bot.get_channel(log_id)
    if log_channel is None:
        # The channel that was set before, no longer exixts. Inform the user
        return await ctx.send(
            ("The nickname log channel no longer exists."
             f"Please set a new one with `{prefix}setnicklog`.")
        )
    # Generate embed
    embed = discord.Embed(
        description=f"**{ctx.author.mention} changed nickname of {member.mention}**",
        timestamp=datetime.utcnow(),
        color=discord.Colour.random(seed=member.id)
    )
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
    embed.add_field(name="Before", value=old_nick, inline=False)
    embed.add_field(name="After", value=nickname, inline=False)
    await log_channel.send(embed=embed)


@setnick.error
async def setnick_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.message.add_reaction(no)
        await ctx.send("Unable to find that member")
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send(f"Missing required argument.\nUsage: `{prefix}setnick <Username/Mention> <Optional: nickname>`")


@bot.command()
@commands.guild_only()
@commands.has_guild_permissions(manage_guild=True)
async def setnicklog(ctx, channel: discord.TextChannel = None):
    # Remove the current log channel
    if channel is None:
        # If there wasn't already a channel set, send command usage (since it was probably a user error)
        if db.servers.find_one({"_id": ctx.guild.id})["nickname_log_channel"] is None:
            await ctx.message.add_reaction(no)
            return await ctx.send(
                ("Unable to remove log channel, since none was set before.\n"
                 f"Usage: `{prefix}setnicklog <channel>`, to remove the channel again just use `{prefix}setnicklog`")
            )
        # Remove the channel from the database
        db.servers.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"nickname_log_channel": None}}
        )
        await ctx.message.add_reaction(ok)
        return await ctx.send("Removed nickname log channel")
    if channel.guild != ctx.guild:
        await ctx.send("Cannot set log channel outside of server")
        return await ctx.message.add_reaction(no)
    # Check if bot has permissions to send messages in channel
    if not channel.permissions_for(ctx.guild.me).send_messages:
        await ctx.send("I don't have permission to send messages in that channel")
        return await ctx.message.add_reaction(no)
    # Update the database
    db.servers.update_one({"_id": ctx.guild.id}, {
                          "$set": {"nickname_log_channel": channel.id}})
    await channel.send(f"Successfully set this as the log channel for the `{prefix}setnick` command")
    await ctx.message.add_reaction(ok)


@setnicklog.error
async def setnicklog_error(ctx, error):
    if isinstance(error, commands.ChannelNotFound):
        await ctx.send("Unable to find channel. Please be more specific or use an ID or mention it with #")
        await ctx.message.add_reaction(no)


@bot.command(aliases=["shut", "shutyobitchassup", "shutyobitchass", "sybap"])
@commands.guild_only()
async def shutup(ctx):
    await ctx.message.add_reaction(ok)
    async with ctx.channel.typing():
        try:
            mention = ctx.message.mentions[0]
        except IndexError:
            # Get author from previous message if no one is mentioned
            history = await ctx.channel.history(limit=2).flatten()
            mention = history[1].author
        if ctx.message.role_mentions:
            await ctx.message.remove_reaction(ok, bot.user)
            await ctx.message.add_reaction(no)
            return await ctx.send("You mentioned a role. Please mention a user.")
        if mention == ctx.message.author:
            await ctx.message.remove_reaction(ok, bot.user)
            await ctx.message.add_reaction(no)
            return await ctx.send("Unable to find a user to mute (mention them)")
        if mention.bot:
            await ctx.message.remove_reaction(ok, bot.user)
            await ctx.message.add_reaction(no)
            return await ctx.send("Won't mute a bot ;)")
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role is None:
            await ctx.message.remove_reaction(ok, bot.user)
            await ctx.message.add_reaction(no)
            return await ctx.send("The role `Muted` does not exist. Has it been renamed?")
        # Make sure users don't accidentally get muted in VCs
        # TODO: Optimize this
        # * Disabled due to being WAY TOO SLOW
        # channels = ctx.guild.voice_channels
        # for channel in channels:
        #     # ? If user calling command is in a vc with the other, also do vc mute
        #     await channel.set_permissions(muted_role, speak=True)
        await ctx.message.author.add_roles(muted_role)
        await mention.add_roles(muted_role)
        await ctx.send("https://tenor.com/view/meryl-streep-shut-up-yell-gif-15386483")
    await asyncio.sleep(60)
    await ctx.message.author.remove_roles(muted_role)
    await mention.remove_roles(muted_role)


@bot.command(aliases=["q"])
async def quest(ctx, *, args: str):
    # TODO: Detect quests, and give quest objectives
    await ctx.message.add_reaction(ok)
    query = quote(args)
    search_url = "https://escapefromtarkov.gamepedia.com/Special:Search?scope=internal&search=" + query
    r = requests.get(search_url)
    results = bs(r.text, "html.parser")
    # Find the first search result
    if results.find("a", class_="unified-search__result__title"):
        result = results.find("a", class_="unified-search__result__title").get("href")
        r = requests.get(result)
        page = bs(r.text, "html.parser")
    else:
        page = results
    # Handle disambiguation pages
    if page.find("table", class_="plainlinks ambox ambox-green"):
        result = "https://escapefromtarkov.gamepedia.com" + \
            page.find("div", class_="mw-parser-output").find("a").get("href")
        r = requests.get(result)
        page = bs(r.text, "html.parser")
    title = page.find("h1", id="firstHeading").get_text().strip()
    if "Search results for" in title:
        try:
            await ctx.send(f"Unable to find {discord.utils.escape_markdown(args)}, try being more specific.")
        except HTTPException:
            await ctx.send("Unable to find item, try being more specific.")
        return
    embed = discord.Embed(title=title, url=r.url)

    # Get prices from tarkov-market.com if API key is set
    if tarkov_market:
        api = requests.get('https://tarkov-market.com/api/v1/item?q='
                           + title, headers={'x-api-key': tarkov_key})
        try:
            tarkov_item = api.json()[0]
        except IndexError:
            # If no results are found, state so
            embed.add_field(name="Price", value=f"No results found for {title}")
        else:
            name = tarkov_item["name"]
            price = format(tarkov_item["price"], ",")
            avg24h = format(tarkov_item["avg24hPrice"], ",")
            per_slot = format(int(tarkov_item["price"] / tarkov_item["slots"]), ",")
            market_link = tarkov_item["link"]
            trader_name = tarkov_item["traderName"]
            trader_price = format(tarkov_item["traderPrice"], ",")
            trader_currency = tarkov_item["traderPriceCur"]

            # Check if wiki and API name is same, if not display API name to avoid wrong price
            if name == title:
                name_string = "Price"
            else:
                name_string = f"Price ({name})"

            embed.add_field(
                name=name_string, value=f"**Current:** {price} ₽\n**Per slot:** {per_slot} ₽\n**24h average:** {avg24h} ₽\n**{trader_name}:** {trader_price} {trader_currency}\n[Data from tarkov-market.com]({market_link})")

    # TODO: Give some sort of error when the wiki page has weird formatting
    if page.find(id="Quests"):
        quests = page.find(id="Quests").find_parent(
            "h2").find_next_sibling("ul").find_all("li")
        quests_string = ""
        for quest in quests:
            text = quest.get_text()
            for href in quest.find_all("a"):
                quest_name = href.get_text()
                quest_url = "https://escapefromtarkov.gamepedia.com" + href.get("href")
                text = text.replace(quest_name, f"[{quest_name}]({quest_url})")
            if "in raid" in text:
                text = text.replace("in raid", "**in raid**")
            quests_string += text + "\n"
        if len(quests_string) > 1024:
            embed.add_field(
                name="Quests", value=f"Too many quests to show, see more [here]({r.url + '#Quests'})", inline=False)
        else:
            embed.add_field(name="Quests", value=quests_string, inline=False)

    if page.find(id="Hideout"):
        uses_element = page.find(id="Hideout").find_parent("h2").find_next_sibling()
        # If uses_element isn't "ul", there's probably no hideout uses
        if uses_element.name == "ul":
            uses_string = ""
            if uses_element.name == "p":
                uses_string = uses_element.text
            else:
                uses = uses_element.find_all("li")
                for use in uses:
                    uses_string += use.get_text() + "\n"
            if len(uses_string) > 1024:
                embed.add_field(
                    name="Hideout", value=f"Too many hideout uses to show, see more [here]({r.url + '#Hideout'})", inline=False)
            else:
                embed.add_field(name="Hideout", value=uses_string, inline=False)

    # TODO: Fix formatting for Trading and Crafting embed
    #       Fix weird formatting for multiple items (both with x amount and + another item)
    #       Formatting for additional notes (ex. "After completing his task ...")
    if page.find(id="Trading"):
        # If the Trading tab is empty, skip it
        try:
            trades = page.find(id="Trading").find_parent("h2").find_next_sibling(
                "table", class_="wikitable").find_all("tr")
        except AttributeError:
            pass
        else:
            trades_string = ""
            previous_level = ""
            for trade in trades:
                th = trade.find_all("th")
                trader_info = th[2].get_text().strip().split()
                trader = trader_info[0]
                trader_level = trader_info[1]
                barter_in = th[0].get_text().strip()
                barter_out = th[4].get_text().strip()
                if trader_level != previous_level:
                    trades_string += f"**{trader} {trader_level}:**\n"
                previous_level = trader_level
                trades_string += f"{barter_in} -> {barter_out}\n"
            if len(trades_string) > 1024:
                embed.add_field(
                    name="Trading", value=f"Too many trades to show, see more [here]({r.url + '#Trading'})", inline=False)
            else:
                embed.add_field(name="Trading", value=trades_string, inline=False)

    if page.find(id="Crafting"):
        # If the Crafting tab is empty, skip it
        try:
            crafts = page.find(id="Crafting").find_parent("h2").find_next_sibling(
                "table", class_="wikitable").find_all("tr")
        except AttributeError:
            pass
        else:
            crafts_string = ""
            previous_station = ""
            for craft in crafts:
                th = craft.find_all("th")
                station = th[2].find("big").get_text()
                time = th[2].get_text().strip().replace(station, "")
                craft_in = th[0].get_text().strip()
                craft_out = th[4].get_text().strip()
                if station != previous_station:
                    crafts_string += f"**{station}:**\n"
                previous_station = station
                crafts_string += f"{time}: {craft_in} -> {craft_out}\n"
            if len(crafts_string) > 1024:
                embed.add_field(
                    name="Crafting", value=f"Too many crafts to show, see more [here]({r.url + '#Crafting'})", inline=False)
            else:
                embed.add_field(name="Crafting", value=crafts_string, inline=False)

    # Check for icon
    icon = None
    if page.find("td", class_="va-infobox-icon"):
        icon = page.find("td", class_="va-infobox-icon").find("a",
                                                              class_="image").get("href")
    else:
        # TODO: Make it so that it retries until it finds an item
        if page.find("td", class_="va-infobox-mainimage-image"):
            icon = page.find(
                "td", class_="va-infobox-mainimage-image").find("a", class_="image").get("href")
        embed.set_footer(text="This might not be an item")

    if icon is not None:
        embed.set_thumbnail(url=icon)
    await ctx.send(embed=embed)


@quest.error
async def quest_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send(f"Missing search query. Usage: `{prefix}quest <query>`")


@bot.command(aliases=["map"])
async def maps(ctx, *, args: str):
    async with ctx.channel.typing():
        query = quote(args)
        # TODO: Make this do a search for more reliable results
        url = "https://escapefromtarkov.gamepedia.com/wiki/" + query
        r = requests.get(url)
        results = bs(r.text, "html.parser")
        if results.find(id="Maps"):
            # Get all maps
            maps = results.find(id="Maps").find_parent("h2").find_next_siblings("p")
            await ctx.send(f"Maps found for **{args}** ({url}):")
            for map_img in maps:
                if "Interactive Map" in map_img.text:
                    # Skip the image if its from an Interactive Map
                    continue
                if map_img.find("a"):
                    map_url = map_img.find("a").get("href")
                    await ctx.send(map_url)
            await ctx.message.add_reaction(ok)
        else:
            await ctx.message.add_reaction(no)
            await ctx.send(f"Unable to find any maps for **{args}**")


@maps.error
async def maps_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send(f"Missing map name. Usage: `{prefix}maps <name>`")


@bot.command()
@commands.has_guild_permissions(administrator=True)
async def vcmute(ctx):
    # This command has only been tested with the Vexera Muted role
    await ctx.message.add_reaction(ok)
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role is None:
        return await ctx.send("The role `Muted` does not exist. Has it been renamed?")
    channels = ctx.guild.voice_channels
    perm = not channels[0].overwrites_for(muted_role).speak
    for channel in channels:
        await channel.set_permissions(muted_role, speak=perm)
    await ctx.send(f"Set Speak permission for the Muted role to {perm} in {len(channels)} voice channels")


@bot.command(aliases=["mv"])
@commands.guild_only()
@commands.has_guild_permissions(move_members=True)
async def moveall(ctx, *, channel: str):
    # TODO: Do this after migrating to Novus
    # try:
    #     # Try to find channel from ID, mention or string
    #     await commands.run_converters(ctx, commands.VoiceChannelConverter, channel)
    # except ChannelNotFound:
    #     # If it fails, try to find channel from alias
    #     aliases = db.servers.find_one({"_id": ctx.guild.id})["aliases"]
    #     try:
    #         channel = ctx.bot.get_channel(aliases[channel])
    #     except KeyError:
    #         return await ctx.send(
    #             ("Channel not found. Please use the ID, mention or full name of the channel.\n"
    #             f"Use `{prefix}alias` to set an alias.")
    #         )

    if ctx.author.voice is None:
        return await ctx.send("You need to be in a voice channel to run this command")

    # Get aliases from the database
    aliases = db.servers.find_one({"_id": ctx.guild.id})["aliases"]

    try:
        # If channel is an alias, get the actual channel
        channel = aliases[channel]
        channel = ctx.guild.get_channel(channel)
    except KeyError:
        # If no alias was found, try to find the channel
        channel = discord.utils.find(
            lambda x: x.name == channel, ctx.guild.voice_channels)

    if channel is None:
        await ctx.message.add_reaction(no)
        return await ctx.send("Unable to find channel")
    for member in ctx.author.voice.channel.members:
        await member.move_to(channel)
        logger.info(f"Moved {member} to {channel} in {ctx.guild}")
    await ctx.message.add_reaction(ok)


@moveall.error
async def moveall_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send(f"Missing voice channel ID/name to move to. Usage: `{prefix}moveall <vc id/name>`")
    if isinstance(error, commands.ChannelNotFound):
        await ctx.message.add_reaction(no)
        await ctx.send("Unable to find channel")


# TODO: Add an alias list command
@bot.command(aliases=["mvalias", "movealias"])
@commands.guild_only()
@commands.has_guild_permissions(administrator=True)
async def alias(ctx: commands.Context, alias: str, channel: discord.VoiceChannel = None):
    await ctx.message.add_reaction(ok)
    # Get the aliases object from the database
    aliases: dict = db.servers.find_one({"_id": ctx.guild.id})["aliases"]
    if channel is None:
        # Remove the alias
        await ctx.send(f"Removed alias for channel {ctx.bot.get_channel(aliases[alias]).mention}")
        aliases.pop(alias)
    else:
        # Add the alias
        aliases[alias] = channel.id
        await ctx.send(f"Added {alias} as alias for channel {channel.mention}")
    # Send the modified aliases object to the database
    # ? Convert the dict (object) to a list (array) to make it easier to edit ($pull and $push)
    db.servers.update_one({"_id": ctx.guild.id}, {"$set": {"aliases": aliases}})


@alias.error
async def alias_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send(f"Missing alias and/or channel ID. Usage: `{prefix}alias <alias> <channel ID/name in quotes>`")
    if isinstance(error, commands.ChannelNotFound):
        await ctx.message.add_reaction(no)
        await ctx.send("Unable to find channel")


@bot.command(aliases=["lb", "rolelb", "leaderboard"])
async def roleleaderboard(ctx, arg: str = None):
    try:
        await ctx.message.add_reaction(ok)
        if arg is None:
            limit = 11
        elif arg == "full":
            limit = -999999
        elif arg == "0":
            await ctx.message.add_reaction(no)
            await ctx.message.remove_reaction(ok, bot.user)
            return await ctx.send("Number must be more than `0`")
        else:
            limit = int(arg) + 1
        members_list = ctx.guild.members
        roles = {}
        for member in members_list:
            roles[member.display_name] = len(member.roles)
        sorted_list = {k: v for k, v in sorted(
            roles.items(), key=lambda item: item[1], reverse=True)}
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


@bot.command(aliases=["rule34"])
@commands.is_nsfw()
async def r34(ctx, *, tags):
    # Check for illegal tags
    if ("cub" or "loli" or "shota" or "child" or "underage" or "shotacon") in tags:
        await ctx.message.add_reaction(nsfw)
        await ctx.send("NEI TOS")
    else:
        logger.info(f"Rule34: Searching for {tags}")
        await ctx.message.add_reaction(ok)
        # TODO: Swap to use getImages instead
        xml_url = rule34.URLGen(tags + "+-cub -loli -underage -shotacon -shota")
        logger.info(f"Got API url for {tags}: {xml_url}")
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
            logger.info(f"Rule34: Sent {random_url} with tag(s): {tags}")
        else:
            logger.info(f"Rule34: No posts were found with the tag(s): {tags}")
            await ctx.send(
                f"No posts were found with the tag(s): {discord.utils.escape_markdown(discord.utils.escape_mentions(tags))}"
            )


@r34.error
async def r34_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send(
            ("Missing tags to search for.\n"
             f"Usage: `{prefix}r34/rule34 <tags>` or for multiple tags "
             f"`{prefix}r34/rule34 <tag1> <tag2> ...`\n"
             "If your tag has spaces in it use underscores (`_`) instead.")
        )


@bot.command()
@commands.is_owner()
async def close(ctx):
    ctx.add_reaction("👋")
    await bot.close()


bot.run(token)
