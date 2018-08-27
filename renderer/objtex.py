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

def delete_texture(textureid):
    glDeleteTextures(1, [textureid])

class Obj:
    def __init__(self, filename):
        self.vertices = []
        self.texcoords = []
        self.normals = []
        self.edges = set()
        self.tri_faces = []
        self.quad_faces = []
        self.poly_faces = []

        self.filename = filename
        try:
            self._load()
        except TypeError as e:
            print("Bad obj file. More info:\n"+str(e))

    def _load(self):
        filename = self.filename
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
                for i in range(-1, len(face)-1):
                    edge = (face[i][0], face[i+1][0])
                    if edge in self.edges or edge[::-1] in self.edges:
                        continue
                    self.edges.add(edge)
                
                if len(face) == 3:
                    self.tri_faces.append(tuple(face))
                elif len(face) == 4:
                    self.quad_faces.append(tuple(face))
                else:
                    self.poly_faces.append(tuple(face))
                    
                    
        f.close()

    def __repr__(self):
        return "Obj(%s)"%self.filename

    def _render_face(self, face):
        normalid = face[0][2]
        if normalid:
            normal = self.normals[normalid-1] 
            glNormal3f(*normal)
        for i, v in enumerate(face):
            texcoordid = v[1]
            if texcoordid:
                glTexCoord2fv(self.texcoords[texcoordid-1])
            else:
                glTexCoord2fv(gentexcoord(i/len(face)))
            glVertex3f(*self.vertices[v[0]-1])

    def _render_edge(self, edge):
        pA, pB = self.vertices[edge[0]-1], self.vertices[edge[1]-1]
        glVertex3f(*pA)
        glVertex3f(*pB)
            
    def render(self, textureID):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, textureID)
        
        # TRIANGLES
        glBegin(GL_TRIANGLES)
        for face in (self.tri_faces):
            self._render_face(face)
        glEnd()

        # QUADRILATERALS
        glBegin(GL_QUADS)
        for face in (self.quad_faces):
            self._render_face(face)
        glEnd()

        # N>4 POLYGONS
        for face in (self.poly_faces):
            glBegin(GL_POLYGON)
            self._render_face(face)
            glEnd()

        glDisable(GL_TEXTURE_2D)

    def render_wireframe(self): # for fast rendering
        glBegin(GL_LINES)
        for edge in self.edges:
            self._render_edge(edge)
        glEnd()
        
