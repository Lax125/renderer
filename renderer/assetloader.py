#!/usr/bin/python

'''
sceneelement.py
original source: https://github.com/edward344/PyOpenGL-sample/blob/master/graphics.py
changes:
    - texture coordinates specific to each face are taken into account
    - made more pythonic with split and by removing unnecessary ifs
    - render_scene and render_texture is merged into one function
    - Immediate mode -> VBO

thanks edward344!
'''

import pygame.image as im
from OpenGL.GL import *
from math import sin, cos, tau
import ctypes
import numpy as np
from itertools import chain

def id_gen(start=1):
    next_id = start
    while True:
        yield next_id
        next_id += 1

def gentexcoord(f):
    X = (sin(f*tau)+1)/2
    Y = (cos(f*tau)+1)/2
    return (X, Y)

def load_texture(filename):
    """This function will return the id for the texture"""
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

class Asset:
    def __init__(self, filename, name="asset0"):
        self._clear()
        self.filename = filename
        self.name = name
        self._load()

    def _clear(self):
        pass

    def _load(self):
        pass

    def delete(self):
        pass

class Tex(Asset):
    def __init__(self, filename, name="texture0"):
        self._clear()
        self.filename = filename
        self.name = name
        self._load()

    def _clear(self):
        self.deleted = False
        self.ID = None

    def _load(self):
        self.ID = load_texture(self.filename)

    def delete(self):
        self.deleted = True
        glDeleteTextures([self.ID])
        self.ID = 0 # OpenGL's default texture, white
        self.filename = None
        self.name = None

class Obj(Asset):
    IDs = id_gen(1)
    def __init__(self, filename, name="object0"):
        self.ID = next(Obj.IDs)
        self._clear()
        self.filename = filename
        self.name = name
        try:
            self._load()
        except TypeError as e:
            raise TypeError("Bad obj file. More info:\n"+str(e))

    def _clear(self):
        # cullbackface
        #   OFF: show both front and back of each polygon
        #   ON:  show only front face of each polygon
        self.deleted = False
        self.cullbackface = True # modify this as you please
        
        self.vertices = [(0.0, 0.0, 0.0)] # 1-indexing
        self.texcoords = [(0.0, 0.0)] # 1-indexing, accounts for no-texcoord polygons
        self.normals = [(0.0, 0.0, 1.0)] # 1-indexing, accounts for no-normal polygons
        self.edges = set()
        self.tri_faces = []
        self.quad_faces = []
        self.poly_faces = []

        self.vbo_bufferlen = 0
        self.vbo_vertices = []
        self.vbo_texcoords = []
        self.vbo_normals = []
        self.vbo_tri_indices = []
        self.vbo_buffers = []

    def _load(self):
        filename = self.filename
        f = open(filename)
        for line in f:
            words = line.split()
            if not words:
                continue
            command = words[0]
            if command == "v":
                vertex = tuple(float(word) for word in words[1:4])
                self.vertices.append(vertex)

            elif command == "vt":
                texcoord = tuple(float(word) for word in words[1:3])
                self.texcoords.append(texcoord)

            elif command == "vn":
                normal = tuple(float(word) for word in words[1:4])
                self.normals.append(normal)
                
            elif command == "f":
                face = []

                # face := [(v0, vt0, vn0), (v1, vt1, vn1), (v2, vt2, vn2), ...]
                for word in words[1:]:
                    word = word.replace("//", "/0/")
                    nums = [int(strint) for strint in word.split("/")]
                    nums += [0]*(3-len(nums))
                    face.append(tuple(nums)) # v, vt, vn
                
                for i in range(-1, len(face)-1): # Add new (A, B) pairs into self.edges
                    edge = (face[i][0], face[i+1][0])
                    if edge in self.edges or edge[::-1] in self.edges:
                        continue
                    self.edges.add(edge)

                N_v = len(face)
                
                if N_v == 3:
                    self.tri_faces.append(face)
                elif N_v == 4:
                    self.quad_faces.append(face)
                else:
                    self.poly_faces.append(face)
                    
        f.close()
        self._gen_normals()
        self._gen_vbo_arrays()
        self._gen_vbo_buffers()

    def _gen_normals(self):
        for face in chain(self.tri_faces, self.quad_faces, self.poly_faces):
            if face[0][2] != 0:
                continue
            A = self.vertices[face[0][0]]
            B = self.vertices[face[1][0]]
            C = self.vertices[face[2][0]]
            AB = tuple(Bn-An for An, Bn in zip(A, B))
            AC = tuple(Cn-An for An, Cn in zip(A, C))
            x, y, z = normal = np.cross(AC, AB)
##            magnitude = (x**2 + y**2 + z**2)**0.5
##            print("NORMAL")
##            print(AB, AC)
##            print(tuple(normal))
            self.normals.append(tuple(normal))
            normal_index = len(self.normals)-1
            for i, (v, vt, vn) in enumerate(face):
                face[i] = (v, vt, normal_index)
            

    def _gen_vbo_arrays(self):
        # TRIS
        for face in chain(self.tri_faces, self.quad_faces, self.poly_faces):
            di = self.vbo_bufferlen
            N_v = len(face)
            for v, vt, vn in face:
                self.vbo_vertices.extend(self.vertices[v])
                self.vbo_texcoords.extend(self.texcoords[vt])
                self.vbo_normals.extend(self.normals[vn])
            Ai = di
            for Bi, Ci in zip(range(di+1,di+N_v-1), range(di+2,di+N_v)):
                self.vbo_tri_indices.extend((Ai, Bi, Ci))
            self.vbo_bufferlen += N_v

    def _gen_vbo_buffers(self):
        # vertices, texcoords, normals, indices for tris
        buffers = glGenBuffers(4)

        # vertices [x, y, z, x, y, z, ...]
        glBindBuffer(GL_ARRAY_BUFFER, buffers[0])
        glBufferData(GL_ARRAY_BUFFER,
                     len(self.vbo_vertices)*4,
                     (ctypes.c_float*len(self.vbo_vertices))(*self.vbo_vertices),
                     GL_STATIC_DRAW)

        # texcoords [X, Y, X, Y, X, Y, ...]
        glBindBuffer(GL_ARRAY_BUFFER, buffers[1])
        glBufferData(GL_ARRAY_BUFFER,
                     len(self.vbo_texcoords)*4,
                     (ctypes.c_float*len(self.vbo_texcoords))(*self.vbo_texcoords),
                     GL_STATIC_DRAW)

        # normals [dx, dy, dz, dx, dy, dz, ...]
        glBindBuffer(GL_ARRAY_BUFFER, buffers[2])
        glBufferData(GL_ARRAY_BUFFER,
                     len(self.vbo_normals)*4,
                     (ctypes.c_float*len(self.vbo_normals))(*self.vbo_normals),
                     GL_STATIC_DRAW)

        # vertex indices for tris [Ai, Bi, Ci, Ai, Bi, Ci, ...]
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, buffers[3])
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                     len(self.vbo_tri_indices)*4,
                     (ctypes.c_uint*len(self.vbo_tri_indices))(*self.vbo_tri_indices),
                     GL_STATIC_DRAW)

        self.vbo_buffers = buffers

    def __repr__(self):
        return "Obj(%s)"%self._filename
    

    def _render_face(self, face):
        '''DEPRECATED: render single face'''
        normalid = face[0][2]
        if normalid:
            normal = self.normals[normalid] 
            glNormal3fv(normal)
        for i, v in enumerate(face):
            glTexCoord2fv(self.texcoords[v[1]])
            glVertex3fv(self.vertices[v[0]])

    def _render_edge(self, edge):
        pA, pB = self.vertices[edge[0]], self.vertices[edge[1]]
        glVertex3fv(pA)
        glVertex3fv(pB)
            
    def render(self, tex): # GPU-powered rendering!
        '''Render obj into buffers with texture from textureID.'''
        if self.cullbackface:
            glEnable(GL_CULL_FACE)
        glBindTexture(GL_TEXTURE_2D, tex.ID)

##        #====IMMEDIATE (SLOW, DEPRECATED)====
##        # TRIANGLES
##        glBegin(GL_TRIANGLES)
##        for face in (self.tri_faces):
##            self._render_face(face)
##        glEnd()
##
##        # QUADRILATERALS
##        glBegin(GL_QUADS)
##        for face in (self.quad_faces):
##            self._render_face(face)
##        glEnd()
##
##        # N>4 POLYGONS
##        for face in (self.poly_faces):
##            glBegin(GL_POLYGON)
##            self._render_face(face)
##            glEnd()

        #====VBO (STANDARD, GPU PIPELINE)====
        V, TC, N, TRI_I = self.vbo_buffers
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        
        glBindBuffer(GL_ARRAY_BUFFER, V)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, TC)
        glTexCoordPointer(2, GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, N)
        glNormalPointer(GL_FLOAT, 0, None)

        # WE SHOULD TAKE RENDERING JOBS
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, TRI_I)
        # AND PUSH IT TO THE GPU PIPELINE
        glDrawElements(GL_TRIANGLES, len(self.vbo_tri_indices), GL_UNSIGNED_INT, None)
        
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

        glDisable(GL_CULL_FACE)

    def delete(self):
        self._clear()
        self.ID = 0
        self.filename = r"./assets/objects/cube.obj"
        self.name = None
        self._load()
        self.deleted = True
