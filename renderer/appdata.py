#!/usr/bin/python
from all_modules import *

try:
  DATAPATH = os.path.join(os.getenv("APPDATA"), APPDATA_FOLDERNAME)
  try:
    os.makedirs(DATAPATH)
  except:
    pass
except:
  DATAPATH = r"./data"

def datapath(relpath):
  return os.path.join(DATAPATH, relpath)

def dataclone(fn, datafn):
  shutil.copyfile(fn, datapath(datafn))

def datarm(datafn):
  os.remove(datapath(datafn))

def dataopen(datafn, *args, **kwargs):
  return open(datapath(datafn), *args, **kwargs)

def datainit():
  for relpath in ["save", "save/assets", "save/assets/meshes",
                  "save/assets/textures"]:
    try:
      os.makedirs(datapath(relpath))
    except:
      pass
