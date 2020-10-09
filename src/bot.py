from xml.etree.ElementTree import tostringlist
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


# logger = logging.getLogger('discord')
# logger.setLevel(logging.INFO)
# handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
# handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
# logger.addHandler(handler)

rule34 = rule34.Sync()

#client = discord.Client()
bot = commands.Bot(command_prefix='+', owner_id=140586848819871744)
#logging.basicConfig(level=logging.INFO)

# Emojis :)
ok = "✅"
no = "❌"
nsfw = "🔞"

# Check for folders
if os.path.isdir("/jassa-bot/output/optimized"):
    print("All files are correct :)")
else: 
    os.system("mkdir -p /jassa-bot/output/optimized")
    print("Made output folders")


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game("+jasså"))
    print(f"Logged in as {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    print(error)
    if isinstance(error, commands.NSFWChannelRequired):
        await ctx.message.add_reaction(nsfw)
        await ctx.send("IKKE I GENERAL DA! KUN I <#607395883239342080>")

@bot.command()
async def ping(ctx):
    ping = round(bot.latency * 1000)
    await ctx.send(f"{ping}ms")
    print(f"{ping}ms")

@bot.command(aliases=['jassa'])
async def jasså(ctx, args):
    await ctx.message.add_reaction(ok)
    name = hashlib.md5(args.encode()).hexdigest()
    filename = "/jassa-bot/output/"+name+".mp4"
    optimized ="/jassa-bot/output/optimized/"+name+".gif"

    if os.path.isfile(optimized): 
        print("Gif allerede lagd, sender fil")
        await ctx.send(file=discord.File(optimized))
    else:
        #await ctx.send("Lager ny gif nå :)")
        video = VideoFileClip(os.path.abspath("tmp/jassa_template.mp4")).subclip(0,3)

        txt_clip = ( TextClip(args,fontsize=33,color='white',font='ProximaNova-Semibold.otf')
                    .set_position((160,655))
                    .set_duration(3) )

        result = CompositeVideoClip([video, txt_clip]) 
        result.write_videofile(filename)
        # New better ffmpeg options
        os.system("ffmpeg -y -i "+filename+" -i tmp/palette.png -lavfi 'fps=19,scale=480:-1:flags=lanczos,paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle' "+optimized)
        
        await ctx.send(file=discord.File(optimized))
        print(f"Successfully generated gif with {args}")

@jasså.error
async def jasså_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send("Mangler navn (eller noe annet).\nRiktig bruk: `+jasså <navn>`")

@bot.command(aliases=['rule34'])
@commands.is_nsfw()
async def r34(ctx, *, args):
    # FIX THIS
    #tags = ", ".join(args)
    # Check for illegal tags
    if ("cub" or "loli" or "shota" or "child" or "underage" or "shotacon") in args:
        await ctx.message.add_reaction(nsfw)
        await ctx.send("NEI TOS")
    else:
        tags = args
        print(f"Rule34: Searching for {tags}")
        #await ctx.send("Ok horny")
        await ctx.message.add_reaction(ok)
        xml_url = rule34.URLGen(args)
        print(f"Got API url for {tags}: {xml_url}")
        xml = bs(requests.get(xml_url).text, "lxml")
        urls = []
        for post in xml.findAll("post"):
            file_url = post.attrs['file_url']
            urls += [file_url]
        count = len(urls)
        count_text = str(count)
        if count >= 100: 
            count_text = "100+"
        if count >= 1:
            randomUrl = random.choice(urls)
            await ctx.send(f"Found {count_text} results, here is one of them")
            await ctx.send(randomUrl)
            print(f"Rule34: Sent {randomUrl} with tag(s): {tags}")
        else:
            print(f"Rule34: No posts were found with the tag(s): {tags}")
            await ctx.send(f"No posts were found with the tag(s): {tags}")

@r34.error
async def r34_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send("Missing tags to search for.\nUsage: `+r34/rule34 <tags>` or for multiple tags `+r34/rule34 <tag1> <tag2> ...`")

@bot.command()
@commands.is_owner()
async def close(ctx):
    ctx.add_reaction(ok)
    await bot.close()

bot.run("NzUxNTM0MzUzNDAxNTEyMDg4.X1Ke6A.5eSTvnxyy_sEhu8EMfdiK30VBzI")