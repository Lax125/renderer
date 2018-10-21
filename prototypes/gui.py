#!/usr/bin/python

# gui.py: defines functionality of the GUI cause SoC told me to.
# SoC means Separation of Concerns. If I were designing a robot
# this would be the eyes, ears, limbs, hinges, and motors--i.e. the I and the O.

import sys, os

import tkinter as tk # GUI framework
from tkinter import filedialog # open file through GUI
from glglue import togl
from PIL import Image, ImageTk # handle bitmap files

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

class Popup(tk.Toplevel):
  def __init__(self):
    super().__init__()
    self.grab_set()
    protocol("WM_DELETE_WINDOW", self.quit)

  # Window should be packed with frame

  def quit(self):
    self.grab_release()
    self.destroy()

class DummyFrame(tk.Frame):
  '''A frame automatically packed in another frame/window. Used to segment the GUI.'''
  def __init__(self, parent, dimensions, packside, expanding=False, fillaxis=tk.BOTH):
    '''Initialise DummyFrame'''
    w, h = dimensions
    tk.Frame.__init__(self, parent, width=w, height=h)
    self.pack_propagate(expanding)
    self.pack(side=packside, fill=fillaxis, expand=expanding)

class GLFrame(tk.Frame):
  '''A Frame that contains OpenGL context'''

  def __init__(self):
    pass

class MainApp(tk.Frame):
  '''A TkInter Frame with GUI for the audio visualiser'''
  def __init__(self, parent, remote):
    '''Initialise GUI'''
    tk.Frame.__init__(self, parent)
    self.parent = parent
    self.remote = remote
    self.updaterate = 60
    self.project_filename = None
    self.playlist_filename = ""
    self.inputs_disabled = False
    self.init_assets() # load assets
    self.init_widgets() # create widgets
    self.init_functions() # initialise custom functions

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
      img = Image.open(r"assets/images/%s.bmp"%image_name)
      self.assets["image_%s"%image_name] = ImageTk.PhotoImage(img)
  
  def init_widgets(self):
    '''Initialise widgets for the GUI'''
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

    ## BINDINGS
    desc_dict = {"openproject_button": "Open project",
                 "saveproject_button": "Save project",
                 }

    for wn in desc_dict:
      func = ignoreargs(partial(self.flash_marquee_begin, desc_dict[wn], "info"), 1)
      self.widgets[wn].bind("<Enter>", func)
      self.widgets[wn].bind("<Leave>", lambda e: self.flash_marquee_end())
      self.widgets[wn].bind("<ButtonPress-1>", lambda e: self.flash_marquee_end())

    self.parent.protocol("WM_DELETE_WINDOW", self.on_quit)

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

  def on_openproject_button(self, _=None):
    if self.inputs_disabled:
      return
    p_fn = filedialog.askopenfilename(title="Open Project",
                                       filetypes=(("3-D Project Files (*.3dproj)", r".3dproj"),
                                                  ("All Files (*.*)", r"*.*")
                                                  )
                                       )
    if p_fn == "":
      return
    self.remote.load_project(p_fn)

  def on_saveproject_button(self, _=None):
    if self.inputs_disabled:
      return
    p_fn = filedialog.asksaveasfilename(title="Save Playlist",
                                         filetypes=(("Playlist Files (*.playlist)", r"*.playlist"),
                                                    ("All Files (*.*)", r"*.*")
                                                    ),
                                         defaultextension=".playlist"
                                         )
    if p_fn == "":
      return
    self.remote.save_project(p_fn)

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
