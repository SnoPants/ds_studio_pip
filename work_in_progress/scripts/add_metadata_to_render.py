from PIL import Image, PngImagePlugin
import os
import re

folder = r"C:\Users\v-adespain\Desktop\TAKE_NUKE_LOCAL\WIP_adespain\adespain\port\warthog\p2"

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]

files = sorted([
    f for f in os.listdir(folder)
    if f.lower().endswith(".png")
], key=natural_sort_key)

start_frame = int(input("Enter starting frame: "))

for i, file in enumerate(files):
    path = os.path.join(folder, file)
    frame = start_frame + i

    img = Image.open(path)

    meta = PngImagePlugin.PngInfo()
    if img.info:
        for k, v in img.info.items():
            meta.add_text(k, str(v))

    meta.add_text("FrameNumber", str(frame))

    img.save(path, pnginfo=meta)

    print(f"{file} → FrameNumber={frame}")