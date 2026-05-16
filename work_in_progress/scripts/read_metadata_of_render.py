import os
from PIL import Image
import re

folder = r"C:\Users\v-adespain\Desktop\TAKE_NUKE_LOCAL\WIP_adespain\adespain\port\final_sequences\warthog"

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]

files = sorted([
    f for f in os.listdir(folder)
    if f.lower().endswith(".png")
], key=natural_sort_key)

for i, file in enumerate(files):
    if file.endswith(".png"):
        img = Image.open(os.path.join(folder, file))
        print(file, "→", img.info.get("FrameNumber"))