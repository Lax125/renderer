#usr/bin/python

from render import *

def test():
  r = Renderer()
  r._camera.set_resolution(1000, 1000)
  r._camera.set_xaov(0.6*pi)
  im = r.get_quickrender()
  im.show()
  im.save("tmp.bmp")

if __name__ == "__main__":
  test()
