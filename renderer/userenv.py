#!/usr/bin/python
'''
userenv.py

Describes user environment class that contains:
  - IDs of loaded textures
  - Loaded model objects
  - The scene to render
"EVERYONE IS HERE."
*SMASH BROS ULTIMATE THEME STARTS PLAYING*
'''

from engine import Scene, Camera

class UserEnv:
  '''A user environment describes everything about the state of the application to be saved.'''
  def __init__(self, assets=set(), scene=Scene(), camera=Camera(), focus=None):
    self.assets = assets
    self.scene = scene
    self.camera = camera
    self.focus = focus

  def __str__(self):
    return '''[[User Environment]]
  Assets: {}
  Renderables: {}'''.format(len(self.assets), len(self.scene.rends))

