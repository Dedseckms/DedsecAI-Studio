"""Rebuild native installer artwork from the Studio palette. Requires Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DEST=Path(__file__).resolve().parent/'artwork'
DEST.mkdir(exist_ok=True)
GREEN='#9de8ba';WHITE='#f2f2f5';MUTED='#939c96';BG='#101114'

def font(size,bold=False):
    candidates=[('C:/Windows/Fonts/seguisb.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf'),
                ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for path in candidates:
        if Path(path).exists():return ImageFont.truetype(path,size)
    return ImageFont.load_default(size=size)

def logo(size):
    im=Image.new('RGBA',(512,512));d=ImageDraw.Draw(im)
    d.rounded_rectangle((12,12,500,500),radius=108,fill='#14251d',outline='#507960',width=5)
    rows=['101010','10   10','10    01','10    10','10    01','10   10','101010']
    for y,row in enumerate(rows):
        for x,ch in enumerate(row):
            if ch!=' ':d.text((79+x*50,65+y*49),ch,font=font(43,True),fill=GREEN if (x+y)%2 else '#d6ffe4')
    d.ellipse((416,440,432,456),fill=GREEN)
    return im.resize((size,size),Image.Resampling.LANCZOS)

icon=logo(256)
icon.save(DEST/'studio.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
side=Image.new('RGB',(328,628),BG);d=ImageDraw.Draw(side)
for x in range(0,328,32):d.line((x,0,x,628),fill='#17241d')
for y in range(0,628,32):d.line((0,y,328,y),fill='#17241d')
side.paste(logo(132),(32,48),logo(132))
d.text((32,208),'DedsecAI',font=font(37,True),fill=WHITE)
d.text((32,252),'Studio',font=font(37),fill=GREEN)
d.line((32,326,292,326),fill='#35473b',width=2)
for i,text in enumerate(['CHAT + MEMORY','CODE WITH PI','IMAGES + GPU']):
    d.text((32,360+i*45),text,font=font(19),fill='#b9d4c6')
d.text((32,554),'YOUR HARDWARE.',font=font(17),fill=MUTED)
d.text((32,580),'YOUR AI.',font=font(17),fill=GREEN)
side.resize((164,314),Image.Resampling.LANCZOS).save(DEST/'sidebar.bmp')
head=Image.new('RGB',(300,114),BG);head.paste(logo(80),(200,16),logo(80))
d=ImageDraw.Draw(head);d.text((12,30),'STUDIO',font=font(23,True),fill=GREEN)
head.resize((150,57),Image.Resampling.LANCZOS).save(DEST/'header.bmp')
icon.save(DEST/'studio.png')
