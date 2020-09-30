from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import os
import logging
import discord
from discord.ext import commands
import hashlib
import rule34

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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def jasså(ctx, args):
    await ctx.message.add_reaction(ok)
    #if args == discord.User: 
    #    name = ctx.
    
    

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
        #result.write_gif(filename,fps=25, program='ffmpeg')
        result.write_videofile(filename)
        # New better ffmpeg options
        os.system("ffmpeg -y -i "+filename+" -i tmp/palette.png -lavfi 'fps=19,scale=480:-1:flags=lanczos,paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle' "+optimized)
        
        await ctx.send(file=discord.File(optimized))
        print("Successfully generated gif with "+args)

@bot.command(aliases=['r34', 'rule34'])
async def _r34(ctx, *, args):
    await ctx.send("Ok horny")
    #await ctx.send(rule34.getImages(args, randomPID=True))
    await ctx.send(f"Sorry no pron found for {args}")

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