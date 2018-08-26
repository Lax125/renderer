#!/usr/bin/python

'''
obj.py
original source: https://github.com/edward344/PyOpenGL-sample/blob/master/graphics.py
changes:
    - texture coordinates specific to each face are taken into account
    - made more pythonic with split and by removing unnecessary ifs
    - default texture, render_scene and render_texture is merged into one function

thanks edward344!
'''

import pygame.image as im
from OpenGL.GL import *
from math import sin, cos, tau

def gentexcoord(f):
    X = (sin(f*tau)+1)/2
    Y = (cos(f*tau)+1)/2
    return (X, Y)

def load_texture(filename):
    """ This fuctions will return the id for the texture"""
    textureSurface = im.load(filename)
    textureData = im.tostring(textureSurface,"RGBA",1)
    width = textureSurface.get_width()
    height = textureSurface.get_height()
    ID = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D,ID)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,width,height,0,GL_RGBA,GL_UNSIGNED_BYTE,textureData)
    return ID

DEFAULT_TEXTUREID = load_texture("./assets/textures/_default.png")

class Obj:
    def __init__(self, filename):
        self.vertices = []
        self.texcoords = []
        self.normals = []
        self.triangle_faces = []
        self.quad_faces = []
        self.polygon_faces = []
        try:
            self._load(filename)
        except TypeError as e:
            print("Bad obj file. More info:\n"+str(e))

    def _load(self, filename):
        f = open(filename)
        n = 1
        for line in f:
            words = line.split()
            command = words[0]
            if command == "v":
                vertex = tuple(float(word) for word in words[1:4])
                self.vertices.append(vertex)
                
            elif command == "vn":
                normal = tuple(float(word) for word in words[1:4])
                self.normals.append(normal)

            elif command == "vt":
                texcoord = tuple(float(word) for word in words[1:3])
                self.texcoords.append(texcoord)
                
            elif command == "f":
                face = []
                for word in words[1:]:
                    word = word.replace("//", "/0/")
                    nums = [int(strint) for strint in word.split("/")]
                    nums += [0]*(3-len(nums))
                    face.append(tuple(nums)) # v, vt, vn
                if len(face) == 3:
                    self.tri_faces.append(tuple(face))
                elif len(face) == 4:
                    self.quad_faces.append(tuple(face))
                else:
                    self.poly_faces.append(tuple(face))
                    
                    
        f.close()

    def _render_face(self, face):
        normalid = face[0][2]
        if normalid:
            normal = self.normals[normalid-1] 
            glNormal3fv(normal)
        for i, v in enumerate(face):
            texcoordid = v[1]
            if texcoordid:
                glTexCoord2fv(self.texcoords[texcoordid])
            else:
                glTexCoord2fv(gentexcoord(i/len(face)))
            glVertex3fv(self.vertices[v[0]-1])
            
    def render(self, textureID=DEFAULT_TEXTUREID):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, textureID)
        
        # TRIANGLES
        glBegin(GL_TRIANGLES)
        for face in (self.triangle_faces):
            self._render_face(face)
        glEnd()

        # QUADRILATERALS
        glBegin(GL_QUADS)
        for face in (self.quad_faces):
            self._render_face(face)
        glEnd()

        # N>4 POLYGONS
        for face in (self.polygon_faces):
            glBegin(GL_POLYGON)
            self._render_face(face)
            glEnd()

        glDisable(GL_TEXTURE_2D)
