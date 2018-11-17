#!/usr/bin/env python
import os
from PIL import Image, ImageOps

LIGHT_THEME_ICONS_PATH = "./assets/icons/light_theme"
DARK_THEME_ICONS_PATH = "./assets/icons/dark_theme"
for fn in os.listdir(LIGHT_THEME_ICONS_PATH):
  # invert RGB, keep A
  im = Image.open(os.path.join(LIGHT_THEME_ICONS_PATH, fn))
  im = im.convert("RGBA")
  r,g,b,a = im.split()
  rgb_im = Image.merge("RGB", (r,g,b))
  inverted_rgb_im = ImageOps.invert(rgb_im)
  ir,ig,ib = inverted_rgb_im.split()
  inverted = Image.merge("RGBA", (ir, ig, ib, a))
  inverted.save(os.path.join(DARK_THEME_ICONS_PATH, fn))

#ThatWasEasy
