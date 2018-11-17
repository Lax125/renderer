#!/usr/bin/env python
'''
userenv.py

Describes user environment class that contains:
  - Loaded texture objects
  - Loaded model objects
  - The scene to render
'''
from all_modules import *
from engine import Scene, Camera

class UserEnv:
  '''A user environment describes everything about the state of the application to be saved.'''
  def __init__(self, assets=set(), scene=Scene(), camera=Camera()):
    self.assets = assets
    self.scene = scene
    self.camera = camera

  def __str__(self):
    return '''[[User Environment]]
  Assets: {}
  Renderables: {}'''.format(len(self.assets), len(self.scene.rends))

