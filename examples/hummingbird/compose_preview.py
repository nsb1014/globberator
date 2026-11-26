"""Place the color render on a soft sky backdrop and assemble the clay review."""
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "hummingbird"
source=Image.open(OUT/"hummingbird-alpha.png").convert("RGBA")
width,height=source.size
sky=Image.new("RGB",(width,height))
pix=sky.load()
for y in range(height):
    for x in range(width):
        central=max(0.,1-math.hypot((x-width*.55)/width,(y-height*.40)/height))
        t=y/height
        pix[x,y]=(round(158+27*t+8*central),round(187+20*t+6*central),round(211+12*t+5*central))
sky=sky.convert("RGBA")
sky.alpha_composite(source)
sky.convert("RGB").save(OUT/"hummingbird.png")
views=OUT/"views"
if len(list(views.glob("*.png")))==8:
    frames=list(sorted(views.glob("*.png")))
    grid=Image.new("RGB",(1160,636),(31,35,40))
    draw=ImageDraw.Draw(grid)
    font="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    draw.text((16,14),"Hummingbird · exported clay views",font=ImageFont.truetype(font,25),fill=(229,232,235))
    for i,frame in enumerate(frames):
        x,y=16+i%4*286,58+i//4*285
        upload=Image.open(frame).convert("RGBA")
        bg=Image.new("RGBA",upload.size,(31,35,40,255))
        bg.alpha_composite(upload)
        grid.paste(bg.convert("RGB").resize((270,263),Image.Resampling.LANCZOS),(x,y))
        azimuth=("Front","Front diagonal","Left","Rear left","Back","Rear right","Right","Front right")
        draw.text((x,y+265),azimuth[i],font=ImageFont.truetype(font,14),fill=(209,213,217))
    grid.save(OUT/"clay-turnaround.png")
