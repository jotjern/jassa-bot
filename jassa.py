from moviepy.editor import *
#import pygame

input = "Jørgen"

video = VideoFileClip("jasså template.mp4").subclip(0,3)

txt_clip = ( TextClip(input,fontsize=32,color='white',font='ProximaNova-Semibold')
             .set_position((155,655))
             .set_duration(3) )

result = CompositeVideoClip([video, txt_clip]) # Overlay text on video
#result.show(interactive = True)
result.write_gif("output/jassa "+input+".gif",fps=15, program='ffmpeg') # Many options...
#result.save_frame("test3.png")