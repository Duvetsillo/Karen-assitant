"""Original local geometry for the Windows executable and tray icon."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

root = Path(__file__).resolve().parents[1] / 'assets'
root.mkdir(exist_ok=True)
size = 512
im = Image.new('RGBA', (size, size))
d = ImageDraw.Draw(im)
d.polygon([(147,195),(94,117),(102,40),(139,60),(186,155)], fill='#b8bcf5')
d.polygon([(365,195),(418,117),(410,40),(373,60),(326,155)], fill='#b8bcf5')
d.rounded_rectangle((75,132,437,440),radius=138,fill='#a9e6f5',outline='#e8ffff',width=5)
d.ellipse((103,177,151,217),fill='#e8ffff')
d.rounded_rectangle((111,241,401,360),radius=51,fill='#263b60')
d.ellipse((159,254,215,328),fill='#d6ffff')
d.ellipse((297,254,353,328),fill='#d6ffff')
for x in (176,314):
    d.ellipse((x,271,x+26,316),fill='#314573')
    d.ellipse((x-2,267,x+12,283),fill='white')
d.arc((234,313,278,345),0,180,fill='#c9faff',width=5)
d.polygon([(256,385),(239,396),(256,411),(273,396)],fill='#e6ffff')
im.save(root/'karen.png')
im.save(root/'karen.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
