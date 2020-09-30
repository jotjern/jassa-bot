from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import os
import logging
import discord
from discord.ext import commands
import hashlib
import rule34
from urllib.request import urlopen
from xml.etree.ElementTree import parse
import random

# logger = logging.getLogger('discord')
# logger.setLevel(logging.INFO)
# handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
# handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
# logger.addHandler(handler)

rule34 = rule34.Sync()

#client = discord.Client()
bot = commands.Bot(command_prefix='+')
#logging.basicConfig(level=logging.INFO)

# Emojis :)
ok = "✅"
no = "❌"
nsfw = "🔞"

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game("+jasså"))
    print(f"Logged in as {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NSFWChannelRequired):
        await ctx.message.add_reaction(nsfw)
        await ctx.send("IKKE I GENERAL DA! KUN I <#607395883239342080>")

@bot.command()
async def jasså(ctx, args):
    await ctx.message.add_reaction(ok)
    name = hashlib.md5(args.encode()).hexdigest()
    filename = "output/"+name+".mp4"
    optimized ="output/optimized/"+name+".gif"

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
        os.system("ffmpeg -y -i "+filename+" -i tmp/palette.png -lavfi 'fps=10,scale=480:-1:flags=lanczos,paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle' "+optimized)
        
        await ctx.send(file=discord.File(optimized))
        print("Successfully generated gif with "+args)

@jasså.error
async def jasså_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send("Mangler navn (eller noe annet).\nRiktig bruk: `+jasså <navn>`")

@bot.command(aliases=['r34', 'rule34'])
@commands.is_nsfw()
async def _r34(ctx, *, tags):
    #await ctx.send("Ok horny")
    await ctx.message.add_reaction(ok)
    xml_url = rule34.URLGen(tags)
    url = urlopen(xml_url)
    xmldoc = parse(url)
    urls = []
    for post in xmldoc.getroot():
        file_url = post.get('file_url')
        urls += [file_url]
    count = len(urls)
    if (count == 100): 
        count = "100+"
    try:
        if (count == 0):
            await ctx.send(random.choice(urls))
        await ctx.send(f"Found {count} results, here is one of them")
        await ctx.send(random.choice(urls))
    except IndexError:
        await ctx.send(f"No posts were found with the tag(s): {tags}")

@_r34.error
async def r34_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(no)
        await ctx.send("Missing tags to search for.\nUsage: `+r34/rule34 <tags>` or for multiple tags `+r34/rule34 <tag1> <tag2> ...`")

@bot.command()
async def close(ctx):
    ctx.add_reaction(ok)
    await bot.close()

@bot.command()
async def pog(ctx, args):
    name = hashlib.md5(args.encode()).hexdigest()
    await ctx.send(name)
    await ctx.message.add_reaction(ok)
    

bot.run("NzUxNTM0MzUzNDAxNTEyMDg4.X1Ke6A.5eSTvnxyy_sEhu8EMfdiK30VBzI")