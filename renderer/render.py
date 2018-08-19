#usr/bin/python

from PIL import Image, ImageDraw, ImageOps
from engine import *

def combine_layers(images):
  '''Pastes images on top of eachother'''
  result = images[0].copy()
  for image in images[1:]:
    result.paste(image, (0, 0), image)
  return result

class Renderer:
  def __init__(self,
               camera=Camera(pos=Point((0, 0, -1.5))),
               scene=Scene([Model.loadfrom_off("teapot.off", pos=Point((-0.5, -0.5, 0)), rx=-0.7*pi, scale=1.2, colour="#ff00ffff"),
                            Model.loadfrom_off("teapot.off", pos=Point((-1.5, 0.0, 0.5)), rx=-0.7*pi, scale=1.0, colour="#ffff00ff"),
                            Model.loadfrom_off("teapot.off", pos=Point((-0.7, -0.5, 0.0)), rx=-0.7*pi, scale=1.0, colour="#00ffffff")
                            ], bg="#ffffff"),
               imagedims=(800, 800)
               ):
    self._camera = camera
    self._scene = None
    self.set_scene(scene)
    self._imfull = None
    self._imquick = None
    self._resfull = (800, 800)
    self._resquick = (200, 200)
    self._res = self._resfull
    self._xaov = 0.6*pi
    self._imagedims = imagedims
    self._refresh_all()

  def set_scene(self, scene):
    self._scene = scene
    self._camera.set_scene(scene)

  def _refresh_all(self):
    self._camera.set_resolution(*self._res)
    self._camera.set_xaov(self._xaov)
    self._camera._update_all()

  def set_resquick(self, XY):
    self._resquick = XY

  def set_mode(self, MODE):
    if MODE == "FULL":
      self._res = self._resfull
    elif MODE == "QUICK":
      self._res = self._resquick
    else:
      raise KeyError("%s is not a valid mode."%MODE)

    self._refresh_all()

  def set_imagedims(self, imageXY):
    self._imagedims = imageXY

  def get_imagedims(self):
    return self._imagedims

  def get_im_size(self):
    return self._res

  def get_background(self):
    return Image.new("RGB", self.get_im_size(), self._scene.get_bg())

  def get_triframe(self):
    X, Y = self.get_im_size()
    im = Image.new("RGBA", (X, Y))
    mask = Image.new("1", (X, Y))
    drawim = ImageOps.invert(self.get_background())
    draw = ImageDraw.Draw(drawim, "RGBA")
    maskdraw = ImageDraw.Draw(mask)
    depths = np.ndarray(self.get_im_size()[::-1], float)
    depths.fill(self._camera.get_maxdepth())
    for tri in sorted(list(self._camera.get_visible_tris()), key=lambda tri: -max(self._camera.get_depth(p) for p in tri)):
      XYA, XYB, XYC = self.project_tri(tri)
      if XYA is None:
        continue
      draw.polygon([XYA, XYB, XYC], tri.get_colour())
      maskdraw.polygon([XYA, XYB, XYC], 1)
    im.paste(ImageOps.invert(drawim), (0, 0), mask)
    return im.convert("RGBA")

  def get_wireframe(self):
    im = Image.new("RGBA", self.get_im_size(), "#00000000")
    draw = ImageDraw.Draw(im)
    for dl in self._camera.get_wireframe_drawlines():
      draw.line(dl, fill="#000000ff")
    return im

  def get_bboxframe(self):
    im = Image.new("RGBA", self.get_im_size(), "#00000000")
    draw = ImageDraw.Draw(im)
    for dl in self._camera.get_bboxframe_drawlines():
      draw.line(dl, fill="#aa00aaff")
    return im

  def render_full(self):
    self.set_mode("FULL")
    self._imfull = combine_layers([self.get_background(),
                                   self.get_triframe(),
                                   self.get_wireframe(),
                                   self.get_bboxframe()
                                   ])

  def get_imfull(self):
    return self._imfull.resize(self._imagedims, Image.ANTIALIAS)

  def get_fullrender(self):
    self.render_full()
    return self.get_imfull()

  def render_quick(self):
    self.set_mode("QUICK")
    self._imquick = combine_layers([self.get_background(),
                                    self.get_wireframe(),
                                    self.get_bboxframe()
                                    ])

  def get_imquick(self):
    return self._imquick.resize(self._imagedims, Image.ANTIALIAS)

  def get_quickrender(self):
    self.render_quick()
    return self.get_imquick()

  def project_tri(self, tri):
    assert type(tri) is Tri
    XYA, XYB, XYC = (self._camera.project_point(p) for p in tri)
    n_validpoints = sum(XY != (None, None) for XY in (XYA, XYB, XYC))
    if n_validpoints == 3:
      return ((self._camera._xspan + XY[0], self._camera._yspan - XY[1]) for XY in (XYA, XYB, XYC))
    return (None, None, None)

  def get_mask_tri(self, tri):
    mask = Image.new("1", self.get_im_size())
    draw = ImageDraw.Draw(mask)
    XYA, XYB, XYC = self.project_tri(tri)
    if XYA is None:
      return mask
    draw.polygon([XYA, XYB, XYC], 1)
    return mask
