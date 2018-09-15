import sys, os
import zipfile
import shutil
import shlex # for splitting values in blueprint.dat files
from appdata import *
from rotpoint import Rot, Point
from engine import Model, Light
from assetloader import Mesh, Tex, id_gen
from collections import defaultdict as ddict

# The following function, quite appropriately named "get0",
# returns a value that is equivalent to the following things:
#   - x - x
#   - e^(pi*i) + 1
#   - The number of non-trivial (The number of non-trivial (The number of non-trivial (...))) found in the Riemann function
#   - False
#   - No
#   - Zilch
#   - Nada
#   - The number of friends I have
def get0():
  return 0

def lazyReadlines(f):
  l = f.readline()
  while l:
    yield l
    l = f.readline()

def castList(types, l):
  return [T(a) for T, a in zip(types, l)]

def zipdir(path, ziph):
  # ziph is zipfile handle
  for root, dirs, files in os.walk(path):
    for file in files:
      absname = os.path.join(root, file)
      arcname = absname[len(path)+1:]
      ziph.write(absname, arcname)

def unzipdir(ziph, path):
  ziph.extractall(path)

def strPosRot(obj):
  return " ".join([str(fl) for fl in [*obj.pos, *obj.rot]])

def deStrPosRot(s):
  nums = s.split()
  pos = Point(*nums[0:3])
  rot = Rot(*nums[3:6])
  return pos, rot

class Saver:
  def __init__(self, app):
    self.UE = app.UE
    self.R = app.R
    self.app = app
    self.defaultMesh = self.R.loadMesh("./assets/meshes/_default.obj")
    self.defaultTexture = self.R.loadTexture("./assets/textures/_default.png")

  def update(self): # construct a .obj-like file that specifies construction of a userenv
    with dataopen("save/blueprint.dat", "w") as f:
      f.write("# 3DBP\n")
      # Placement indicies conform to Wavefront's 1-indexing
      # because having two competing standards is confusing
      meshPlacements = id_gen(1) # yields 1, 2, 3, ...
      texturePlacements = id_gen(1) # yields 1, 2, 3, ...
      mDict = ddict(get0) # mesh ID -> placement index {1, 2, 3, ...}
      tDict = ddict(get0) # texture ID -> placement index {1, 2, 3, ...}
      for asset in self.UE.assets:
        if type(asset) is Mesh:
          f.write("m %s %d %d\n"%(repr(asset.name), asset.ID,
                                  asset.cullbackface))
          mDict[asset.ID] = next(meshPlacements)
        elif type(asset) is Tex:
          f.write("t %s %d\n"%(repr(asset.name), asset.ID))
          tDict[asset.ID] = next(texturePlacements)
      for rend in self.UE.scene:
        if type(rend) is Model:
          f.write("model %s %s %s %s %s %s\n"%(repr(rend.name), mDict[rend.mesh.ID], tDict[rend.tex.ID],
                                               strPosRot(rend), rend.scale, rend.shininess))
      f.write("cam %s %s %s\n"%(strPosRot(self.UE.camera),
                                self.UE.camera.fovy,
                                self.UE.camera.zoom))
      f.close()
      

  def save(self, fn):
    self.update()
    savepath = datapath("save")
    # zip that into fn
    zipf = zipfile.ZipFile(fn, "w", zipfile.ZIP_DEFLATED)
    zipdir(savepath, zipf)

  def load(self, fn): # doesn't clear userenv or app
    savepath = datapath("save")
    
    # clear save folder
    shutil.rmtree(savepath)
    os.mkdir(savepath)
    
    # copy zipped contents of fn into save folder
    zipf = zipfile.ZipFile(fn, "r")
    unzipdir(zipf, savepath)

    try:
      self.load_appdata()
    except:
      raise IOError()

  def load_appdata(self):
    meshes = [self.defaultMesh]
    textures = [self.defaultTexture]
    for line in lazyReadlines(dataopen("save/blueprint.dat", "r")):
      words = shlex.split(line)
      if not words:
        continue
      command, *args = words
      
      if command == "#":
        pass
      
      elif command == "m": # mesh
        name, ID, cullbackface = castList([str, int, int], args)
        if ID == 0:
          meshes.append(self.defaultMesh)
        else:
          new_mesh = self.R.loadMesh(datapath("save/assets/meshes/%d.obj"%ID), name=name)
          new_mesh.cullbackface = bool(cullbackface)
          self.app.addAsset(new_mesh)
          meshes.append(new_mesh)
          
      elif command == "t": # texture
        name, ID = castList([str, int], args)
        if ID == 0:
          textures.append(self.defaultTexture)
        else:
          new_tex = self.R.loadTexture(datapath("save/assets/textures/%d.png"%ID), name=name)
          self.app.addAsset(new_tex)
          textures.append(new_tex)

      elif command == "model":
        name, meshIndex, texIndex, x,y,z,rx,ry,rz, scale, shininess\
          = castList([str, int, int, *[float]*6, float, float], args)
        new_model = Model(meshes[meshIndex], textures[texIndex], pos=Point(x,y,z),
                          rot=Rot(rx,ry,rz), scale=scale, shininess=shininess)
        self.app.addRend(new_model)

      elif command == "cam":
        x,y,z,rx,ry,rz, fovy, zoom = castList([*[float]*6, float, float], args)
        self.R.configCamera(Point(x,y,z), Rot(rx, ry, rz), fovy, zoom)
    
