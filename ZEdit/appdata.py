#!/usr/bin/env python
'''
appdata.py
defines interaction between
the code and the roaming appdata
folder reserved for it.
'''
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
  '''Get absolute path (DATAPATH/relpath) from relative appdata path (relpath)'''
  return os.path.join(DATAPATH, relpath)

def dataclone(fn, datafn):
  '''Clone file (fn) into a path in the appdata folder (DATAPATH/datafn)'''
  shutil.copyfile(fn, datapath(datafn))

def datarm(datafn):
  '''Delete file in appdata folder (DATAPATH/datafn)'''
  os.remove(datapath(datafn))

def dataopen(datafn, *args, **kwargs):
  '''Get FileIO object from (DATAPATH/datafn)'''
  return open(datapath(datafn), *args, **kwargs)

def datainit():
  '''Initialise folder structure in appdata'''
  for relpath in ["save", "save/assets", "save/assets/meshes",
                  "save/assets/textures"]:
    try:
      os.makedirs(datapath(relpath))
    except:
      pass
