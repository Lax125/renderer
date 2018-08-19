#!/usr/bin/python

# gui.py: defines functionality of the GUI cause SoC told me to.
# SoC means Separation of Concerns. If I were designing a robot
# this would be the eyes, ears, limbs, hinges, and motors--i.e. the I and the O.

import sys, os

import tkinter as tk # GUI framework
from tkinter import filedialog # open file through GUI
from PIL import Image, ImageTk # handle bitmap files

import time, math # FOR DEMO
import numpy as np
##from colour import Color
# NOTE TO SELF: Whoops, the colour module is too slow.
import random

from functools import partial # heh heh heh
import functools

## DEBUG FUNCTIONS
def _debug_delay():
  '''For debug: delay'''
  print("DEBUG: sleeping for 5 seconds...")
  time.sleep(5.0)
  print("DEBUG: stopped sleeping.")
## ===============

def ignoreargs(func, count): # MUAHAHAHAHAH
    @functools.wraps(func)
    def newfunc(*args, **kwargs):
        return func(*(args[count:]), **kwargs)
    return newfunc

SCRIPT_DIR = sys.path[0]
def abs_path(rel_path):
  '''Get absolute path from relative path'''
  global SCRIPT_DIR
  return os.path.join(SCRIPT_DIR, rel_path)

def constrain_float(f):
  '''Constrain floating-point number to [0.0, 1.0]'''
  return min(max(0.0, f), 1.0)

def get_sin_array(n):
  t = time.time()
  sinusoid_floats = [0.5*(math.sin((2*math.pi*i)/n + 1*t) + 1.0) for i in range(n)]
  return sinusoid_floats

def ease_sine(n):
  return (-math.cos(n * math.pi) + 1.0)/2

def hue_to_colour(h):
  norm_h = (h%1.0)*6
  rem = norm_h%1.0
  if norm_h < 1:
    red = 1.0
    green = rem
    blue = 0.0
  elif norm_h < 2:
    red = 1.0 - rem
    green = 1.0
    blue = 0.0
  elif norm_h < 3:
    red = 0.0
    green = 1.0
    blue = rem
  elif norm_h < 4:
    red = 0.0
    green = 1.0 - rem
    blue = 1.0
  elif norm_h < 5:
    red = rem
    green = 0.0
    blue = 1.0
  elif norm_h < 6:
    red = 1.0
    green = 0.0
    blue = 1.0 - rem

  R = "{0:02x}".format(math.floor(red * 255))
  G = "{0:02x}".format(math.floor(green * 255))
  B = "{0:02x}".format(math.floor(blue * 255))
  return "#" + R + G + B

class DummyFrame(tk.Frame):
  '''A frame automatically packed in another frame. Used to segment the GUI.'''
  def __init__(self, parent, dimensions, packside, expanding=False, fillaxis=tk.BOTH):
    '''Initialise DummyFrame'''
    w, h = dimensions
    tk.Frame.__init__(self, parent, width=w, height=h)
    self.pack_propagate(expanding)
    self.pack(side=packside, fill=fillaxis, expand=expanding)

class MainApp(tk.Frame):
  '''A TkInter Frame with GUI for the audio visualiser'''
  def __init__(self, parent):
    '''Initialise GUI'''
    tk.Frame.__init__(self, parent)
    self.parent = parent
    self.updaterate = 48 # cap framerate to 48 fps
    self.filenames = []
    self.playlist_filename = ""
    self.inputs_disabled = False
    self.init_assets() # load assets
    self.init_widgets() # create widgets
    self.init_functions() # initialise custom functions
    self.style("default") # the style function fits basic functionality e.g. playback is paused
    self.set_theme("Plain")

    self.updating = False
    self.start_updating()

  def init_assets(self):
    '''Load assets such as images'''
    ## MAKE DICT
    self.assets = dict()

    ## IMAGES
    for image_name in ["open", "snaptostart", "stop", "play", "pause",
                       "openplaylist", "saveplaylist", "prevtrack",
                       "nexttrack", "loop_off", "loop_on", "autoplay_off", "autoplay_on"]:
      img = Image.open(abs_path(r"assets/images/%s.bmp"%image_name))
      self.assets["image_%s"%image_name] = ImageTk.PhotoImage(img)
  
  def init_widgets(self):
    '''Initialise widgets for the GUI e.g. bargraph, scrubber'''
    ## MAKE DICT
    self.widgets = dict()
    
    ## MAKE WIDGETS
    # dimensions
    # OH BOY TIME TO START SCREAMING FOR NO REASON
    WIDTH = 500
    BUTTON_WIDTH = 30
    TOOLBAR_HEIGHT = 20
    TOOLBAR_N_BUTTONS_L = 3
    TOOLBAR_N_BUTTONS_R = 3
    MARQUEE_WIDTH = WIDTH - BUTTON_WIDTH*(TOOLBAR_N_BUTTONS_L + TOOLBAR_N_BUTTONS_R)
    BARGRAPH_HEIGHT = 200
    CONTROLBAR_HEIGHT = 30
    HEIGHT = TOOLBAR_HEIGHT + BARGRAPH_HEIGHT + CONTROLBAR_HEIGHT
    CONTROLBAR_N_BUTTONS = 3
    PROGRESS_LABEL_WIDTH = 90
    SCRUBBER_WIDTH = WIDTH - (CONTROLBAR_N_BUTTONS*BUTTON_WIDTH + PROGRESS_LABEL_WIDTH)
    assert MARQUEE_WIDTH >= 0 # sanity check
    assert SCRUBBER_WIDTH >= 0 # sanity check

    # set self dimensions
    self.config(width=WIDTH, height=HEIGHT)
    self.new_geometry = True
    self.geometry_t0 = time.time()

    # toolbar
    tbf = self.widgets["toolbar"] = DummyFrame(self, (WIDTH, TOOLBAR_HEIGHT), tk.TOP)
    tb_bf_l = DummyFrame(tbf, (TOOLBAR_N_BUTTONS_L*BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT)
    self.widgets["openplaylist_button"] = tk.Button(DummyFrame(tb_bf_l, (BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT), command=self.on_openplaylist_button, relief=tk.FLAT)
    self.widgets["saveplaylist_button"] = tk.Button(DummyFrame(tb_bf_l, (BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT), command=self.on_saveplaylist_button, relief=tk.FLAT)
    self.widgets["prevtrack_button"] = tk.Button(DummyFrame(tb_bf_l, (BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT), command=self.on_prevtrack_button, relief=tk.FLAT)
    self.widgets["openplaylist_button"].pack(fill=tk.BOTH)
    self.widgets["saveplaylist_button"].pack(fill=tk.BOTH)
    self.widgets["prevtrack_button"].pack(fill=tk.BOTH)
    # ::::::
    self.widgets["marquee"] = tk.Canvas(DummyFrame(tbf, (0, TOOLBAR_HEIGHT), tk.LEFT, expanding=True), width=0, height=TOOLBAR_HEIGHT, bd=0, highlightthickness=0)
    self.widgets["marquee"].pack(fill=tk.X, expand=True)
    # ::::::
    tb_bf_r = DummyFrame(tbf, (TOOLBAR_N_BUTTONS_L*BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT)
    self.widgets["nexttrack_button"] = tk.Button(DummyFrame(tb_bf_r, (BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT), command=self.on_nexttrack_button, relief=tk.FLAT)
    self.widgets["toggloop_button"] = tk.Button(DummyFrame(tb_bf_r, (BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT), command=self.on_toggloop_button, relief=tk.FLAT)
    self.widgets["toggautoplay_button"] = tk.Button(DummyFrame(tb_bf_r, (BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT), command=self.on_toggautoplay_button, relief=tk.FLAT)
    self.widgets["nexttrack_button"].pack(fill=tk.BOTH)
    self.widgets["toggloop_button"].pack(fill=tk.BOTH)
    self.widgets["toggautoplay_button"].pack(fill=tk.BOTH)
    
    # bargraph Canvas
    self.widgets["bargraph"] = tk.Canvas(DummyFrame(self, (WIDTH, 0), tk.TOP, expanding=True), width=WIDTH, height=0, bd=0, highlightthickness=0)
    self.widgets["bargraph"].pack(fill=tk.BOTH, expand=True)

    # controlbar Frame
    cbf = self.widgets["controlbar"] = DummyFrame(self, (WIDTH, CONTROLBAR_HEIGHT), tk.TOP)
    cb_bf = DummyFrame(cbf, (CONTROLBAR_N_BUTTONS*BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT)
    self.widgets["open_button"] = tk.Button(DummyFrame(cb_bf, (BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT), command=self.on_open_button, relief=tk.FLAT)
    self.widgets["stop_button"] = tk.Button(DummyFrame(cb_bf, (BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT), command=self.on_stop_button, relief=tk.FLAT)
    self.widgets["togg_button"] = tk.Button(DummyFrame(cb_bf, (BUTTON_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT), command=self.on_togg_button, relief=tk.FLAT)
    self.widgets["open_button"].pack(fill=tk.BOTH)
    self.widgets["stop_button"].pack(fill=tk.BOTH)
    self.widgets["togg_button"].pack(fill=tk.BOTH)
    # ::::::
    self.widgets["scrubber"] = tk.Canvas(DummyFrame(cbf, (0, CONTROLBAR_HEIGHT), tk.LEFT, expanding=True), width=0, height=CONTROLBAR_HEIGHT, bd=0, highlightthickness=0)
    self.widgets["scrubber"].pack(fill=tk.X, expand=True)
    # ::::::
    plf = self.widgets["progress_label_frame"] = DummyFrame(cbf, (PROGRESS_LABEL_WIDTH, CONTROLBAR_HEIGHT), tk.LEFT)
    self.widgets["progress_label"] = tk.Label(plf, background="#000000",
                                                   foreground="#80ff80",
                                                   font="Consolas 8 bold",
                                                   text="--:--/--:--"
                                              )
    self.widgets["progress_label"].pack(fill=tk.BOTH, expand=True)

    ## INITIALISE CANVASES
    marquee_dims = (MARQUEE_WIDTH, TOOLBAR_HEIGHT)
    bargraph_dims = (WIDTH, BARGRAPH_HEIGHT)
    scrubber_dims = (SCRUBBER_WIDTH, CONTROLBAR_HEIGHT)

    self.widgets["marquee"].config(background="#000000")
    marquee_left = (0.0, marquee_dims[1]/2)
    self.widgets["marquee"].text = self.widgets["marquee"].create_text(marquee_left, anchor=tk.W,
                                                                                     fill="#e0e0ff",
                                                                                     font="Verdana 8 italic bold",
                                                                                     text="Select song...",
                                                                                     tags="text")
    self.marquee_t0 = time.time()
    self.marquee_x = 0
    self.marquee_text = "" # placeholder
    self.marquee_colour = "#ffffff" # placeholder
    self.marquee_flashing = False
    self._marquee_job = None
    self.start_marquee()
    self.widgets["marquee"].bind("<Enter>", lambda e: self.start_marquee())

    self.bargraph_floats = [0.0]
    self.bargraph_cache = ("None", [])
    self.widgets["bargraph"].bar_ycoords = []
    self.widgets["bargraph"].bind("<Double-Button-1>", self.on_togg_button)

    self.scrubber_progress = 0.0
    self.scrubber_load_bar_progress = 0.0
    self.scrubber_held = False
    self.widgets["scrubber"].config(background="#101010") # dark grey
    self.widgets["scrubber"].load_bar = self.widgets["scrubber"].create_rectangle(0, -1, 0, scrubber_dims[1],
                                                                                  fill="#303030",
                                                                                  tags="load_bar")
    self.scrubloadbar_x = 0
    self.widgets["scrubber"].cursor = self.widgets["scrubber"].create_line(0, 0, 0, scrubber_dims[1], tags="cursor")
    self.widgets["scrubber"].itemconfig("cursor", fill="#20ff20", # green
                                                  width=2.0)
    
    self.widgets["scrubber"].bind("<ButtonPress-1>", self.on_scrubber_press)
    self.widgets["scrubber"].bind("<B1-Motion>", self.on_scrubber_hold)
    self.widgets["scrubber"].bind("<ButtonRelease-1>", self.on_scrubber_release)

    ## BINDINGS
    desc_dict = {"openplaylist_button": "Open playlist",
                 "saveplaylist_button": "Save playlist",
                 "prevtrack_button": "Previous track",
                 "nexttrack_button": "Next track",
                 "toggloop_button": "Toggle looping",
                 "toggautoplay_button": "Toggle autoplay",
                 "open_button": "Open track(s)",
                 "stop_button": "Stop playback",
                 "togg_button": "Toggle playback",
                 "progress_label": "Playback timestamp"
                 }

    for wn in desc_dict:
      func = ignoreargs(partial(self.flash_marquee_begin, desc_dict[wn], "info"), 1)
      self.widgets[wn].bind("<Enter>", func)
      self.widgets[wn].bind("<Leave>", lambda e: self.flash_marquee_end())
      self.widgets[wn].bind("<ButtonPress-1>", lambda e: self.flash_marquee_end())
    
    self.bind("<Configure>", self.on_configure)
    
    self.parent.bind("<space>", self.on_togg_button)
    self.parent.bind("<Control-Alt-o>", self.on_openplaylist_button)
    self.parent.bind("<Control-o>", self.on_open_button)
    self.parent.bind("<Control-s>", self.on_saveplaylist_button)
    self.parent.bind("<Left>", self.on_leftarrow_key)
    self.parent.bind("<KeyRelease-Left>", self.on_leftarrow_release)
    self.leftarrow_key_held = False
    self.parent.bind("<Right>", self.on_rightarrow_key)
    self.parent.bind("<KeyRelease-Right>", self.on_rightarrow_release)
    self.rightarrow_key_held = False
    self.parent.bind("<Alt-Left>", self.on_prevtrack_button)
    self.parent.bind("<Alt-Right>", self.on_nexttrack_button)
    self.parent.bind("r", self.on_resolution_button)
    self.parent.bind("t", self.on_theme_button)
    self.parent.bind("l", self.on_togglog_button)
    self.parent.bind("<Unmap>", self.on_unmap)
    self.parent.bind("<Map>", self.on_map)

    self.parent.protocol("WM_DELETE_WINDOW", self.on_quit)

  def get_marquee_dims(self):
    return (self.widgets["marquee"].winfo_width(), self.widgets["marquee"].winfo_height())

  def get_bargraph_dims(self):
    return (self.widgets["bargraph"].winfo_width(), self.widgets["bargraph"].winfo_height())

  def get_scrubber_dims(self):
    return (self.widgets["scrubber"].winfo_width(), self.widgets["scrubber"].winfo_height())

  def init_functions(self):
    '''Initialise custom functions'''
    self.functions = dict()
    for func_name in ["update",
                      "new_files",
                      "new_playlist",
                      "save_playlist",
                      "button_prevtrack",
                      "button_nexttrack",
                      "button_toggloop",
                      "button_toggautoplay",
                      "button_stop",
                      "button_togg",
                      "scrubber_press",
                      "scrubber_hold",
                      "scrubber_release",
                      "key_leftarrow",
                      "key_rightarrow",
                      "press_leftarrow",
                      "press_rightarrow",
                      "release_leftarrow",
                      "release_rightarrow",
                      "button_resolution",
                      "button_theme",
                      "button_togglog",
                      "quit"
                      ]: # [:
      self.functions[func_name] = lambda: None # all are allowed to be overridden

  def fconfig(self, func_name, func):
    '''Convenience function: configure custom function'''
    if func_name not in self.functions:
      raise KeyError("%s is not a custom function. Valid custom functions are: %s"%(func_name, list(self.functions)))
    self.functions[func_name] = func

  def get_filenames(self):
    '''Convenience function: get filename(s) of selected audio file(s)'''
    return self.filenames

  def get_playlist_filename(self):
    '''Convenience function: get filename of playlist file'''
    return self.playlist_filename

  def set_marquee(self, text, style="normal"):
    '''Set and update marquee'''
    self.set_marquee_text(text, style)
    if not self.marquee_flashing:
      self.update_marquee_text()

  def set_marquee_text(self, text, style):
    '''Set text and text colour on scrubber'''
    colour_dict = {"normal": "#e0e0ff",
                   "error": "#ffc0c0",
                   "info": "#b0ffb0"
                   }
    t, c = self.marquee_text, self.marquee_colour
    self.marquee_text = text
    self.marquee_colour = colour_dict[style]

  def update_marquee_text(self):
    self.widgets["marquee"].itemconfig("text", text=self.marquee_text, fill=self.marquee_colour)
    self.start_marquee()

  def flash_marquee(self, text, style="normal"):
    if self._marquee_job is not None:
      self.after_cancel(self._marquee_job)
    self._marquee_job = self.after(2000, self.flash_marquee_end)
    self.flash_marquee_begin(text, style=style)

  def flash_marquee_begin(self, text, style="normal"):
    self.marquee_flashing = True
    colour_dict = {"normal": "#e0e0ff",
                   "error": "#ffc0c0",
                   "info": "#a0ffa0"
                   }
    t, c = self.marquee_text, self.marquee_colour
    self.marquee_text = text
    self.marquee_colour = colour_dict[style]
    self.update_marquee_text()
    self.marquee_text = t
    self.marquee_colour = c

  def flash_marquee_end(self):
    self.marquee_flashing = False
    self.update_marquee_text()

  def refresh_dimensions(self):
    self.new_geometry = True

  def get_valid_themes(self):
    return ["Plain", "Rainbow", "Neon", "Polygonal", "Eclipse"]#, "Morningstar"]

  def set_bargraph(self, floatlist):
    '''Set bargraph to display list of floats that range from 0.0 to 1.0'''
    if len(floatlist) > 0:
      self.bargraph_floats = floatlist

  def update_bargraph(self):
    bg = self.widgets["bargraph"]
    right, bottom = self.get_bargraph_dims()
    n_bars = len(self.bargraph_floats)
    bar_space = self.get_bargraph_dims()[0]/n_bars
    
    if self.theme == "Plain":
      self.bargraph_cache = ("Plain", [])
      bg.delete("all")
      coords = []
      for i, a in enumerate(self.bargraph_floats):
        y = (0.497*bottom) - (0.4*bottom)*a
        coords.append((i*bar_space, y))
        coords.append(((i+1)*bar_space, y))
      for i, a in list(enumerate(self.bargraph_floats))[::-1]:
        y = (0.503*bottom) + (0.4*bottom)*a
        coords.append(((i+1)*bar_space, y))
        coords.append((i*bar_space, y))

      bg.create_polygon(coords, fill="#ffffff", width=0.0)
            
        
    elif self.theme == "Rainbow":
      self.bargraph_cache = ("Rainbow", [])
      bg.delete("all")
      hue_shift = -time.time()/5
      for i, a in enumerate(self.bargraph_floats):
        y = (0.99*bottom) - (0.98*bottom)*a
        hue = i/n_bars + hue_shift
        bg.create_rectangle(i*bar_space,
                            y,
                            (i+1)*bar_space,
                            bottom,
                            width=0.0,
                            fill=hue_to_colour(hue))

    elif self.theme == "Neon":
      self.bargraph_cache = ("Neon", [])
      bg.delete("all")
      w = 0.5*bar_space
      for i, a in enumerate(self.bargraph_floats):
        x = (i + 0.5)*bar_space
        y_top = (0.5*bottom) - (0.4*bottom)*a
        y_bottom = (0.5*bottom) + (0.4*bottom)*a
        bar = bg.create_line(x,
                             y_top,
                             x,
                             y_bottom,
                             width=w,
                             capstyle=tk.ROUND,
                             fill="#ff0000")
    elif self.theme == "Polygonal":
      self.bargraph_cache = ("Polygonal", [])
      bg.delete("all")
      coords = [(0, bottom/2)]
      for i, a in enumerate(self.bargraph_floats):
        coords.append(((i + 0.5)*bar_space, (0.497*bottom) - (0.4*bottom)*a))
      coords.append((self.get_bargraph_dims()[0], bottom/2))
      for i, a in list(enumerate(self.bargraph_floats))[::-1]:
        coords.append(((i + 0.5)*bar_space, (0.503*bottom) + (0.4*bottom)*a))
      bg.create_polygon(coords, fill="#000000", width=0.0)

    elif self.theme == "Eclipse":
      self.bargraph_cache = ("Eclipse", [])
      bg.delete("all")
      mid_x, mid_y = right/2, bottom/2
      inferior = min(mid_x, mid_y)
      mid_r = 0.4*inferior
      outer_r = 0.4*inferior
      inner_r = 0.05*inferior
      thickness = 0.01*inferior
##      inner_coords = []
##      outer_coords = []
      coords = []
      da = self.bargraph_floats[0] - self.bargraph_floats[-1]
      smear_len = n_bars//7
      smear = [self.bargraph_floats[-1] + da*ease_sine(i/(smear_len)) for i in range(smear_len)]
      smeared_floats = list(self.bargraph_floats) + smear
      n_bars += len(smear)
      for i, a in enumerate(smeared_floats + [smeared_floats[0]]):
        r = mid_r + thickness + a*outer_r
        theta = -(i/n_bars)*math.tau + math.tau*(11/16)
        x = r*math.cos(theta) + mid_x
        y = -(r*math.sin(theta)) + mid_y
        coords.append((x, y))
      for i, a in list(enumerate(smeared_floats + [smeared_floats[0]]))[::-1]:
        r = mid_r - a*inner_r
        theta = -(i/n_bars)*math.tau + math.tau*(11/16)
        x = r*math.cos(theta) + mid_x
        y = -(r*math.sin(theta)) + mid_y
        coords.append((x, y))
      bg.create_polygon(coords, fill="#e4e4ff")
##      for i, a in enumerate(smeared_floats):
##        r = mid_r + thickness + a*outer_r
##        theta = -(i/n_bars)*math.tau + math.tau*(11/16)
##        x = r*math.cos(theta) + mid_x
##        y = -(r*math.sin(theta)) + mid_y
##        outer_coords.append((x, y))
##      bg.create_polygon(outer_coords, fill="#d0e0ff")
##      for i, a in enumerate(smeared_floats):
##        r = mid_r - a*inner_r
##        theta = -(i/n_bars)*math.tau + math.tau*(11/16)
##        x = r*math.cos(theta) + mid_x
##        y = -(r*math.sin(theta)) + mid_y
##        inner_coords.append((x, y))
##      bg.create_polygon(inner_coords, fill="#000010")

    elif self.theme == "Morningstar":
      self.bargraph_cache = ("Morningstar", [])
      bg.delete("all")
      mid_x, mid_y = right/2, bottom/2
      inferior = min(mid_x, mid_y)
      in_r = 0.4*inferior
      thickness = 0.01*inferior
      outer_r = 0.4*inferior
      smear = list(np.linspace(self.bargraph_floats[-1], self.bargraph_floats[0], n_bars//3))[1:-1]
      smeared_floats = list(self.bargraph_floats) + smear
      n_bars += len(smear)
      w = (math.tau*in_r/n_bars)*(0.6)
      for i, a in enumerate(smeared_floats):
        r = in_r + thickness + a*outer_r
        theta = -(i/n_bars)*math.tau + math.tau*(5/8)
        is_hor = abs(math.sin(theta)) > (2**(-1/2))
        x0 = in_r*math.cos(theta) + mid_x
        y0 = -(in_r*math.sin(theta)) + mid_y
        x1 = x0 if is_hor else r*math.cos(theta) + mid_x
        y1 = y0 if not is_hor else -(r*math.sin(theta)) + mid_y
        bg.create_line(x0, y0, x1, y1,
                       width=w,
                       capstyle=tk.ROUND,
                       fill="#ffff00")
      

  def set_scrubber(self, progress):
    '''Set scrubber to display float that ranges from 0.0 to 1.0'''
    self.scrubber_progress = progress

  def set_scrubber_load_bar(self, progress):
    '''Set load bar on scrubber to float that ranges from 0.0 to 1.0'''
    self.scrubber_load_bar_progress = progress


  def update_scrubber(self):
    self.widgets["scrubber"].delete("all")
    
    # update load bar
    new_load_bar_x = int(self.scrubber_load_bar_progress*self.get_scrubber_dims()[0])
    self.widgets["scrubber"].load_bar = self.widgets["scrubber"].create_rectangle(-1, -1, new_load_bar_x, self.get_scrubber_dims()[1],
                                                                                  fill="#303030",
                                                                                  tags="load_bar")
    # update cursor
    new_cursor_x = int(self.scrubber_progress*self.get_scrubber_dims()[0])
    self.widgets["scrubber"].cursor = self.widgets["scrubber"].create_line(new_cursor_x,
                                                                           0,
                                                                           new_cursor_x,
                                                                           self.get_scrubber_dims()[1],
                                                                           fill="#20ff20",
                                                                           tags="cursor")
    self.widgets["scrubber"].itemconfig("cursor", width=4.0 if self.scrubber_held else 2.0) # There is one obviously lazy way to do it.

  def get_scrubber(self):
    '''Get scrubber progress as a float from 0.0 to 1.0'''
    return self.scrubber_progress

  def set_progress_label(self, text):
    '''Set progress label to display text'''
    self.widgets["progress_label"].config(text=text)

  def on_openplaylist_button(self, _=None):
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    pl_fn = filedialog.askopenfilename(title="Select Playlist",
                                       filetypes=(("Playlist Files (*.playlist)", r".playlist"),
                                                  ("All Files (*.*)", r"*.*")
                                                  )
                                       )
    if pl_fn == "":
      return
    self.playlist_filename = pl_fn
    self.functions["new_playlist"]()

  def on_saveplaylist_button(self, _=None):
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    file_data = "\n".join(self.filenames)
    pl_fn = filedialog.asksaveasfilename(title="Save Playlist",
                                         filetypes=(("Playlist Files (*.playlist)", r"*.playlist"),
                                                    ("All Files (*.*)", r"*.*")
                                                    ),
                                         defaultextension=".playlist"
                                         )
    if pl_fn == "":
      return
    with open(pl_fn, "wb") as f:
      f.write(bytes(file_data, "utf-8"))
      f.close()
    self.functions["save_playlist"]

  def on_prevtrack_button(self, _=None):
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    self.functions["button_prevtrack"]()

  def on_nexttrack_button(self, _=None):
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    self.functions["button_nexttrack"]()

  def on_toggloop_button(self, _=None):
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    self.functions["button_toggloop"]()

  def on_toggautoplay_button(self, _=None):
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    self.functions["button_toggautoplay"]()

  def on_open_button(self, _=None):
    '''Event trigger: press leftmost button'''
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    # select filename
    ext_filter = r"*.pcm;*.wav;*.ogg;\
                   *.aac;*.aiff;*.aifc;\
                   *.aif;*flac;*.mp3;*.wma"
    fns = filedialog.askopenfilenames(title="Select Audio Files",
                                      filetypes=(("Audio Files (%s)"%ext_filter, ext_filter),
                                                 ("All Files (*.*)", r"*.*")
                                                 )
                                      )
    fns = list(fns) # darn tuples...
    if fns != []:
      self.filenames = fns
      self.functions["new_files"]()

  def on_stop_button(self):
    '''Event trigger: press middle button'''
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    self.functions["button_stop"]()

  def on_togg_button(self, _=None):
    '''Event trigger: press rightmost button'''
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    self.functions["button_togg"]()

  def on_scrubber_press(self, event):
    '''Event trigger: mousepress scrubber'''
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    mouse_x = self.widgets["scrubber"].canvasx(event.x)
    mouse_progress = constrain_float(mouse_x/self.get_scrubber_dims()[0])
    self.set_scrubber(mouse_progress)
    self.scrubber_held = True
    self.functions["scrubber_press"]()

  def on_scrubber_hold(self, event):
    '''Event trigger: mouse movement scrubber'''
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    mouse_x = self.widgets["scrubber"].canvasx(event.x)
    mouse_progress = constrain_float(mouse_x/self.get_scrubber_dims()[0])
    self.set_scrubber(mouse_progress)
    self.functions["scrubber_hold"]()

  def on_scrubber_release(self, event):
    '''Event trigger: mouse release scrubber'''
    if self.inputs_disabled:
      return
    if self.leftarrow_key_held or self.rightarrow_key_held:
      return
    self.scrubber_held = False
    self.functions["scrubber_release"]()

  def on_leftarrow_key(self, event):
    '''Event trigger: left arrow pressed'''
    if self.inputs_disabled:
      return
    if not self.leftarrow_key_held:
      self.leftarrow_key_held = True
      self.functions["press_leftarrow"]()
    self.functions["key_leftarrow"]()

  def on_rightarrow_key(self, event):
    '''Event trigger: right arrow pressed'''
    if self.inputs_disabled:
      return
    if not self.rightarrow_key_held:
      self.rightarrow_key_held = True
      self.functions["press_rightarrow"]()
    self.functions["key_rightarrow"]()

  def on_leftarrow_release(self, event):
    if self.inputs_disabled:
      return
    self.leftarrow_key_held = False
    self.functions["release_leftarrow"]()

  def on_rightarrow_release(self, event):
    if self.inputs_disabled:
      return
    self.rightarrow_key_held = False
    self.functions["release_rightarrow"]()

  def on_resolution_button(self, event):
    '''Event trigger: key [r] pressed'''
    if self.inputs_disabled:
      return
    self.functions["button_resolution"]()

  def on_theme_button(self, event):
    '''Event trigger: key [t] pressed'''
    if self.inputs_disabled:
      return
    self.functions["button_theme"]()

  def on_togglog_button(self, event):
    if self.inputs_disabled:
      return
    self.functions["button_togglog"]()

  def on_configure(self, event):
    self.start_marquee()
##    self.after(30, self.refresh_dimensions)

  def on_resizerequest(self, event):
    self.on_configure()

  def on_unmap(self, event):
    self.stop_updating()
##    self.after(30, self.refresh_dimensions)

  def on_map(self, event):
    self.start_updating()
##    self.after(30, self.refresh_dimensions)

  def on_quit(self, _=None):
    '''Event trigger: close window'''
    self.functions["quit"]()
    self.parent.destroy()

  def style(self, trigger):
    '''Subtly style the GUI based on a trigger word''' # YOU JUST TRIGGERED ME REEEEE
    valid = ["default",
             "pending_file","loading","paused",   "playing",
             "loop_off",                          "loop_on",
             "autoplay_off",                      "autoplay_on"
             ]
    if trigger not in valid:
      raise KeyError("Invalid trigger: %s"%trigger)
    if trigger == "default":
      self.widgets["open_button"].config(image=self.assets["image_open"])
      self.widgets["stop_button"].config(image=self.assets["image_snaptostart"])
      self.widgets["togg_button"].config(image=self.assets["image_play"])
      self.widgets["openplaylist_button"].config(image=self.assets["image_openplaylist"])
      self.widgets["saveplaylist_button"].config(image=self.assets["image_saveplaylist"])
      self.widgets["prevtrack_button"].config(image=self.assets["image_prevtrack"])
      self.widgets["nexttrack_button"].config(image=self.assets["image_nexttrack"])
      self.widgets["toggloop_button"].config(image=self.assets["image_loop_off"])
      self.widgets["toggautoplay_button"].config(image=self.assets["image_autoplay_on"])
    
    elif trigger in ["pending_file", "loading", "paused"]:
      self.widgets["stop_button"].config(image=self.assets["image_snaptostart"])
      self.widgets["togg_button"].config(image=self.assets["image_play"])
    elif trigger == "playing":
      self.widgets["stop_button"].config(image=self.assets["image_stop"])
      self.widgets["togg_button"].config(image=self.assets["image_pause"])

    elif trigger == "loop_off":
      self.widgets["toggloop_button"].config(image=self.assets["image_loop_off"])
    elif trigger == "loop_on":
      self.widgets["toggloop_button"].config(image=self.assets["image_loop_on"])

    elif trigger == "autoplay_off":
      self.widgets["toggautoplay_button"].config(image=self.assets["image_autoplay_off"])
    elif trigger == "autoplay_on":
      self.widgets["toggautoplay_button"].config(image=self.assets["image_autoplay_on"])

  def set_theme(self, theme_name):
    assert theme_name in self.get_valid_themes()
    self.theme = theme_name
    c_dict = {"Plain": "#000040",
              "Rainbow": "#000000",
              "Neon": "#202020",
              "Polygonal": "#d0d0d0",
              "Eclipse": "#000010",
              "Morningstar": "#ff6000"
              }
    self.widgets["bargraph"].config(background=c_dict[theme_name])

  def start_marquee(self):
    self.marquee_t0 = time.time()
    self.widgets["marquee"].delete("all")
    marquee_left = (5.0, self.get_marquee_dims()[1]/2)
    self.widgets["marquee"].create_text(marquee_left,
                                        anchor=tk.W,
                                        font="Verdana 8 italic bold",
                                        text=self.marquee_text,
                                        fill=self.marquee_colour,
                                        tags="text")
    self.marquee_x = 5

  def update_marquee(self):
    if self.widgets["marquee"].bbox("text") is None:
      return
    speed = 25
    text_width = self.widgets["marquee"].bbox("text")[2] - self.widgets["marquee"].bbox("text")[0]
    left = self.marquee_x
    right = left + text_width
    scroll_width = (right - left) - (self.get_marquee_dims()[0] - 10)
    if scroll_width < 0: # text is smaller than the marquee box
      self.widgets["marquee"].move("text", -left + 5, 0)
      return
    cycle_length = 3 + scroll_width/speed + 3
    t = (time.time() - self.marquee_t0)%cycle_length
    if t < 3:
      self.marquee_x = 5
      self.widgets["marquee"].move("text", -left + 5, 0)
      return
    elif (cycle_length - t) < 3:
      dx = self.get_marquee_dims()[0] - right - 5
      self.marquee_x += dx
      self.widgets["marquee"].move("text", dx, 0)
      return
    else:
      dx = -(t - 3)*speed + 5 - left
      self.marquee_x += dx
      self.widgets["marquee"].move("text", dx, 0)
      return

  def start_updating(self):
    if self.updating: #already updating
      return
    self.updating = True
    self._updates_iter()

  def stop_updating(self):
    self.updating = False

  def _updates_iter(self):
    '''Do one iteration of update routine--DO NOT CALL MANUALLY'''
    if self.updating:
      self.after(int(1000/self.updaterate), self._updates_iter)
    self.functions["update"]()
    self.update_marquee()
    self.update_bargraph()
    self.update_scrubber()
    self.update_idletasks() # man that's a lot of updating...
##    self.after(int(1000/self.updaterate), self._updates_iter)

  def disable_inputs(self):
    '''Disable all input methods from functioning (buttons and scrubber)'''
    self.inputs_disabled = True

  def enable_inputs(self):
    '''Enable all input methods to function (buttons and scrubber)'''
    self.inputs_disabled = False

  def __str__(self):
    '''String representation of the GUI'''
    return "An app build for visualising audio (tkinter.Frame object)"

def test():
  '''test functionality of main class'''
  print("Testing functionality of gui.py...")
  root = tk.Tk()
  app = MainApp(root)
  app.pack(fill=tk.BOTH, expand=True)
  root.geometry("500x300")
  root.mainloop()

if __name__ == "__main__": # run when not imported
  test()
