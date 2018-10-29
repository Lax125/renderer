#!/usr/bin/python
'''
remote.py

All user-friendly functions to modify a UserEnv go here.

'''
from all_modules import *

from rotpoint import Rot, Point
from asset import Asset, Mesh, Tex
from engine import Renderable, Model, Lamp, Directory, Link, Camera, Scene
from appdata import *
import saver

datainit()

class Remote:
  '''A remote to control a user environment with methods.'''
  def __init__(self, userenv):
    self.userenv = userenv # should be clear for saving

  def new(self):
    '''New project'''
    self.clearUserEnv()

  def load(self, fn):
    '''Load project'''
    saver.load(fn)

  def save(self, fn):
    '''Save project'''
    saver.save(fn)

##  def loadMesh(self, fn, *args, **kwargs):
##    '''Load a mesh into a Mesh object and an appdata file'''
##    new_mesh = Mesh(fn, *args, **kwargs)
##    return new_mesh
##
##  def loadTexture(self, fn, *args, **kwargs):
##    '''Load a texture into a Tex object and an appdata file'''
##    new_tex = Tex(fn, *args, **kwargs)
##    im = Image.open(fn).resize((1024, 1024))
##    im.save()
##    return new_tex

  def addAsset(self, asset):
    '''Add a Texture object (Mesh, Tex) into the userenv'''
    has_asset = asset in self.userenv.assets
    self.userenv.assets.add(asset)
    return has_asset

  def delAsset(self, asset):
    '''Delete an asset from both its appdata location and userenv and unload it'''
    if type(asset) is Mesh:
      fn = "save/assets/meshes/%d.obj"%asset.ID
    elif type(asset) is Tex:
      fn = "save/assets/textures/%d.png"%asset.ID
    try:
      datarm(fn)
    except:
      pass
    asset.delete()
    self.userenv.assets.discard(asset)

  def addRend(self, rend, directory=None):
    '''Adds rend into userenv's scene'''
    if directory is None:
      has_rend = rend in self.userenv.scene.rends
      self.userenv.scene.add(rend)
    else:
      has_rend = rend in directory.rends
      directory.add(rend)
    return has_rend

  def delRend(self, rend):
    '''Deletes rend from userenv's scene'''
    rend.setParent(None)
    self.userenv.scene.discard(rend)

  def add(self, obj, directory=None):
    if isinstance(obj, Asset):
      return self.addAsset(obj)
    elif isinstance(obj, Renderable):
      return self.addRend(obj, directory)

  def delete(self, obj):
    if isinstance(obj, Asset):
      self.delAsset(obj)
    elif isinstance(obj, Renderable):
      self.delRend(obj)

  def configModel(self, model, mesh=None, tex=None, pos=None, rot=None, scale=None, name=None):
    '''Configures Model object's assets, position, rotation, scale, and name'''
    assert model in self.userenv.models
    model.mesh = mesh if mesh is not None else model.mesh
    model.tex = tex if tex is not None else model.tex
    model.pos = pos if pos is not None else model.pos
    model.rot = rot if rot is not None else model.rot
    model.scale = scale if scale is not None else model.scale
    model.name = name if name is not None else model.name

  def configCamera(self, pos=None, rot=None, fovy=None, zoom=None):
    '''Configure's camera's position, rotation, and field of view'''
    cam = self.userenv.camera # sorry my fingers are tired
    cam.pos = pos if pos is not None else cam.pos
    cam.rot = rot if rot is not None else cam.rot
    cam.fovy = fovy if fovy is not None else cam.fovy
    cam.zoom = zoom if zoom is not None else cam.zoom

  def changeCameraRot(self, drx, dry, drz):
    '''Adds delta rotation to camera's rotation'''
    self.userenv.camera.rot += (drx, dry, drz)

  def dragPan(self, dX, dY):
    self.userenv.camera.rot = Rot(dY/300, -dX/300, 0)*self.userenv.camera.rot

  def changeRendRot(self, rend, drx, dry, drz):
    rend.rot += (drx, dry, drz)

  def lookAt(self, obj):
    '''Makes camera look at object with 0 roll'''
    if isinstance(obj, Renderable):
      dpos = obj.getTruePos() - self.userenv.camera.pos
    elif isinstance(obj, Point):
      dpos = obj - self.userenv.camera.pos
    self.userenv.camera.rot = Rot.from_delta3(dpos)

  def moveCameraTo(self, obj):
    if isinstance(obj, Renderable):
      newpos, newrot = obj.getTruePos(), obj.getTrueRot()
    else:
      newpos, newRot = obj
    self.userenv.camera.pos, self.userenv.camera.rot = newpos, newrot

  def rectifyCamera(self):
    '''Stands camera upright'''
    rx, ry, rz = self.userenv.camera.rot
    self.userenv.camera.rot = Rot(rx, ry, 0)

  def setFocus(self, rend):
    '''Sets focus on a renderable'''
    self.lookAt(rend)
    self.userenv.focus = rend

  def moveCamera(self, dx, dy, dz):
    '''Moves camera by deltas'''
    self.userenv.camera.pos += (dx, dy, dz)

  def moveRend(self, rend, dx, dy, dz):
    rend.pos += (rend.getDirBasePos((dx, dy, dz))-rend.getDirBasePos((0, 0, 0)))

  def moveRendTo(self, rend, x, y, z):
    rend.pos = rend.getDirBasePos((x, y, z))

  def resizeViewport(self, X, Y):
    '''Resizes the OpenGL viewport to (X, Y)'''
    glViewport(0,0, X,Y)

  def renderScene(self, aspect=1.33):
    '''Renders the scene into the OpenGL view buffer'''
    self.userenv.scene.render(self.userenv.camera, aspect=aspect)

##  def renderOverlay(self, aspect=1.33):
##    self.userenv.scene.renderOverlay(self.userenv.camera, aspect=aspect)

  def clearUserEnv(self):
    '''Clears user environment to a clean slate'''
    UE = self.userenv
    for asset in list(UE.assets):
      self.delAsset(asset)
    UE.focus = None
    UE.camera = Camera()
    UE.scene = Scene()
    UE.assets.clear()
    try:
      shutil.rmtree(datapath("save/assets/meshes"))
      shutil.rmtree(datapath("save/assets/textures"))
      os.mkdir(datapath("save/assets/meshes"))
      os.mkdir(datapath("save/assets/textures"))
    except:
      pass

  
