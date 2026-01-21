"""
VBO-basiertes Rendering für GPU-Beschleunigung
==============================================

Verwendet Vertex Buffer Objects (VBOs) statt glBegin/glEnd für
echte GPU-Nutzung. Wird nur bei HIGH/MEDIUM Rendering-Tier aktiviert.

Performance-Vergleich:
- glBegin/glEnd (Immediate Mode): CPU-bound, ~0% GPU-Nutzung
- VBOs: GPU-bound, ~20-60% GPU-Nutzung, 2-5x schneller

Vorlesungskonzept: Vertex Buffer Objects, GPU-Pipelining
"""

import numpy as np
from OpenGL.GL import *
from OpenGL.arrays import vbo
from typing import List, Tuple, Optional
import math


class BundeslandVBO:
    """
    VBO-basiertes Rendering für ein Bundesland.
    
    Speichert alle Vertex-Daten in GPU-Buffern für schnelles Rendering.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.initialized = False
        
        # VBO IDs
        self.top_vbo = None      # Oberseite
        self.sides_vbo = None    # Seitenwände
        self.bottom_vbo = None   # Unterseite
        self.edges_vbo = None    # Kanten
        
        # Vertex counts
        self.top_vertex_count = 0
        self.sides_vertex_count = 0
        self.bottom_vertex_count = 0
        self.edges_vertex_count = 0
        
        # Farben
        self.top_color = (0.8, 0.8, 0.8)
        self.side_color = (0.6, 0.6, 0.6)
        self.edge_color = (0.4, 0.4, 0.4)
    
    def build_from_bundesland(self, bl):
        """
        Erstellt VBOs aus einem Bundesland-Objekt.
        
        Args:
            bl: Bundesland-Objekt mit vertices_top, vertices_bottom, triangles, holes
        """
        if self.initialized:
            self.cleanup()
        
        self.top_color = bl.top_color
        self.side_color = bl.side_color
        self.edge_color = bl.edge_color
        
        # Berechne outer_count
        if hasattr(bl, 'holes') and bl.holes:
            hole_vertex_count = sum(len(h) for h in bl.holes)
            outer_count = len(bl.vertices_top) - hole_vertex_count
        else:
            outer_count = len(bl.vertices_top)
            bl.holes = []
        
        # === OBERSEITE (Dreiecke) ===
        top_vertices = []
        for a, b, c in bl.triangles:
            # Vertex: position (3) + normal (3) = 6 floats
            v1 = bl.vertices_top[a]
            v2 = bl.vertices_top[b]
            v3 = bl.vertices_top[c]
            normal = (0.0, 1.0, 0.0)  # Nach oben
            
            top_vertices.extend([v1[0], v1[1], v1[2], normal[0], normal[1], normal[2]])
            top_vertices.extend([v2[0], v2[1], v2[2], normal[0], normal[1], normal[2]])
            top_vertices.extend([v3[0], v3[1], v3[2], normal[0], normal[1], normal[2]])
        
        if top_vertices:
            top_array = np.array(top_vertices, dtype=np.float32)
            self.top_vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.top_vbo)
            glBufferData(GL_ARRAY_BUFFER, top_array.nbytes, top_array, GL_STATIC_DRAW)
            self.top_vertex_count = len(top_vertices) // 6
        
        # === SEITENWÄNDE (Quads als Dreiecke) ===
        sides_vertices = []
        
        # Äußerer Rand
        for i in range(outer_count):
            next_i = (i + 1) % outer_count
            
            t1 = bl.vertices_top[i]
            t2 = bl.vertices_top[next_i]
            b1 = bl.vertices_bottom[i]
            b2 = bl.vertices_bottom[next_i]
            
            # Normale berechnen
            dx = t2[0] - t1[0]
            dz = t2[2] - t1[2]
            length = math.sqrt(dx * dx + dz * dz)
            if length > 0.0001:
                nx = -dz / length
                nz = dx / length
            else:
                nx, nz = 0, 1
            normal = (nx, 0.0, nz)
            
            # Zwei Dreiecke pro Quad
            # Dreieck 1: t1, t2, b2
            sides_vertices.extend([t1[0], t1[1], t1[2], normal[0], normal[1], normal[2]])
            sides_vertices.extend([t2[0], t2[1], t2[2], normal[0], normal[1], normal[2]])
            sides_vertices.extend([b2[0], b2[1], b2[2], normal[0], normal[1], normal[2]])
            # Dreieck 2: t1, b2, b1
            sides_vertices.extend([t1[0], t1[1], t1[2], normal[0], normal[1], normal[2]])
            sides_vertices.extend([b2[0], b2[1], b2[2], normal[0], normal[1], normal[2]])
            sides_vertices.extend([b1[0], b1[1], b1[2], normal[0], normal[1], normal[2]])
        
        # Loch-Ränder (innere Seitenwände)
        if bl.holes:
            offset = outer_count
            for hole in bl.holes:
                hole_len = len(hole)
                for i in range(hole_len):
                    next_i = (i + 1) % hole_len
                    
                    idx1 = offset + i
                    idx2 = offset + next_i
                    
                    t1 = bl.vertices_top[idx1]
                    t2 = bl.vertices_top[idx2]
                    b1 = bl.vertices_bottom[idx1]
                    b2 = bl.vertices_bottom[idx2]
                    
                    # Invertierte Normale für innere Wand
                    dx = t2[0] - t1[0]
                    dz = t2[2] - t1[2]
                    length = math.sqrt(dx * dx + dz * dz)
                    if length > 0.0001:
                        nx = dz / length
                        nz = -dx / length
                    else:
                        nx, nz = 0, 1
                    normal = (nx, 0.0, nz)
                    
                    # Zwei Dreiecke pro Quad
                    sides_vertices.extend([t1[0], t1[1], t1[2], normal[0], normal[1], normal[2]])
                    sides_vertices.extend([t2[0], t2[1], t2[2], normal[0], normal[1], normal[2]])
                    sides_vertices.extend([b2[0], b2[1], b2[2], normal[0], normal[1], normal[2]])
                    sides_vertices.extend([t1[0], t1[1], t1[2], normal[0], normal[1], normal[2]])
                    sides_vertices.extend([b2[0], b2[1], b2[2], normal[0], normal[1], normal[2]])
                    sides_vertices.extend([b1[0], b1[1], b1[2], normal[0], normal[1], normal[2]])
                
                offset += hole_len
        
        if sides_vertices:
            sides_array = np.array(sides_vertices, dtype=np.float32)
            self.sides_vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.sides_vbo)
            glBufferData(GL_ARRAY_BUFFER, sides_array.nbytes, sides_array, GL_STATIC_DRAW)
            self.sides_vertex_count = len(sides_vertices) // 6
        
        # === UNTERSEITE (Dreiecke, umgekehrte Reihenfolge) ===
        bottom_vertices = []
        for a, b, c in bl.triangles:
            v1 = bl.vertices_bottom[c]
            v2 = bl.vertices_bottom[b]
            v3 = bl.vertices_bottom[a]
            normal = (0.0, -1.0, 0.0)  # Nach unten
            
            bottom_vertices.extend([v1[0], v1[1], v1[2], normal[0], normal[1], normal[2]])
            bottom_vertices.extend([v2[0], v2[1], v2[2], normal[0], normal[1], normal[2]])
            bottom_vertices.extend([v3[0], v3[1], v3[2], normal[0], normal[1], normal[2]])
        
        if bottom_vertices:
            bottom_array = np.array(bottom_vertices, dtype=np.float32)
            self.bottom_vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.bottom_vbo)
            glBufferData(GL_ARRAY_BUFFER, bottom_array.nbytes, bottom_array, GL_STATIC_DRAW)
            self.bottom_vertex_count = len(bottom_vertices) // 6
        
        # === KANTEN (Lines) ===
        edges_vertices = []
        
        # Äußerer Rand
        for i in range(outer_count):
            v = bl.vertices_top[i]
            edges_vertices.extend([v[0], v[1] + 0.001, v[2]])
        
        # Loch-Ränder
        if bl.holes:
            offset = outer_count
            for hole in bl.holes:
                for i in range(len(hole)):
                    v = bl.vertices_top[offset + i]
                    edges_vertices.extend([v[0], v[1] + 0.001, v[2]])
                offset += len(hole)
        
        if edges_vertices:
            edges_array = np.array(edges_vertices, dtype=np.float32)
            self.edges_vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.edges_vbo)
            glBufferData(GL_ARRAY_BUFFER, edges_array.nbytes, edges_array, GL_STATIC_DRAW)
            self.edges_vertex_count = len(edges_vertices) // 3
        
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.initialized = True
        
        # Speichere für Höhen-Updates
        self._outer_count = outer_count
        self._holes = bl.holes
        self._vertices_2d = [(v[0], v[2]) for v in bl.vertices_top]
        self._triangles = bl.triangles
    
    def update_height(self, new_height: float):
        """
        Aktualisiert die Höhe des Bundeslandes.
        
        Muss die VBOs neu aufbauen da sich Y-Koordinaten ändern.
        """
        if not self.initialized:
            return
        
        # Vereinfachte Version: Nur Y-Koordinaten in den VBOs aktualisieren
        # TODO: Für bessere Performance könnte man glBufferSubData verwenden
        pass  # Aktuell wird das Bundesland komplett neu gerendert
    
    def render(self):
        """Rendert das Bundesland mit VBOs."""
        if not self.initialized:
            return
        
        stride = 6 * 4  # 6 floats * 4 bytes
        
        # === OBERSEITE ===
        if self.top_vbo and self.top_vertex_count > 0:
            glColor3f(*self.top_color)
            glBindBuffer(GL_ARRAY_BUFFER, self.top_vbo)
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_NORMAL_ARRAY)
            glVertexPointer(3, GL_FLOAT, stride, None)
            glNormalPointer(GL_FLOAT, stride, ctypes.c_void_p(3 * 4))
            glDrawArrays(GL_TRIANGLES, 0, self.top_vertex_count)
        
        # === SEITENWÄNDE ===
        if self.sides_vbo and self.sides_vertex_count > 0:
            glColor3f(*self.side_color)
            glBindBuffer(GL_ARRAY_BUFFER, self.sides_vbo)
            glVertexPointer(3, GL_FLOAT, stride, None)
            glNormalPointer(GL_FLOAT, stride, ctypes.c_void_p(3 * 4))
            glDrawArrays(GL_TRIANGLES, 0, self.sides_vertex_count)
        
        # === UNTERSEITE ===
        if self.bottom_vbo and self.bottom_vertex_count > 0:
            glColor3f(*self.side_color)
            glBindBuffer(GL_ARRAY_BUFFER, self.bottom_vbo)
            glVertexPointer(3, GL_FLOAT, stride, None)
            glNormalPointer(GL_FLOAT, stride, ctypes.c_void_p(3 * 4))
            glDrawArrays(GL_TRIANGLES, 0, self.bottom_vertex_count)
        
        glDisableClientState(GL_NORMAL_ARRAY)
        
        # === KANTEN ===
        if self.edges_vbo and self.edges_vertex_count > 0:
            glDisable(GL_LIGHTING)
            glColor3f(*self.edge_color)
            glLineWidth(1.3)
            glBindBuffer(GL_ARRAY_BUFFER, self.edges_vbo)
            glVertexPointer(3, GL_FLOAT, 0, None)
            glDrawArrays(GL_LINE_LOOP, 0, self._outer_count)
            
            # Loch-Kanten
            if self._holes:
                offset = self._outer_count
                for hole in self._holes:
                    glDrawArrays(GL_LINE_LOOP, offset, len(hole))
                    offset += len(hole)
            
            glEnable(GL_LIGHTING)
        
        glDisableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def cleanup(self):
        """Löscht VBOs aus dem GPU-Speicher."""
        if self.top_vbo:
            glDeleteBuffers(1, [self.top_vbo])
        if self.sides_vbo:
            glDeleteBuffers(1, [self.sides_vbo])
        if self.bottom_vbo:
            glDeleteBuffers(1, [self.bottom_vbo])
        if self.edges_vbo:
            glDeleteBuffers(1, [self.edges_vbo])
        
        self.top_vbo = None
        self.sides_vbo = None
        self.bottom_vbo = None
        self.edges_vbo = None
        self.initialized = False


class VBORenderer:
    """
    Verwaltet VBO-Rendering für alle Bundesländer.
    
    Wird nur bei HIGH/MEDIUM Rendering-Tier verwendet.
    """
    
    def __init__(self):
        self.bundesland_vbos: dict[str, BundeslandVBO] = {}
        self.initialized = False
    
    def build_all(self, bundeslaender: list):
        """
        Erstellt VBOs für alle Bundesländer.
        
        Args:
            bundeslaender: Liste von Bundesland-Objekten
        """
        for bl in bundeslaender:
            bl_vbo = BundeslandVBO(bl.name)
            bl_vbo.build_from_bundesland(bl)
            self.bundesland_vbos[bl.name] = bl_vbo
        
        self.initialized = True
        print(f"    [VBO] {len(self.bundesland_vbos)} Bundesländer in GPU-Speicher geladen")
    
    def render_all(self):
        """Rendert alle Bundesländer mit VBOs."""
        for bl_vbo in self.bundesland_vbos.values():
            bl_vbo.render()
    
    def render_one(self, name: str):
        """Rendert ein einzelnes Bundesland."""
        if name in self.bundesland_vbos:
            self.bundesland_vbos[name].render()
    
    def cleanup(self):
        """Löscht alle VBOs."""
        for bl_vbo in self.bundesland_vbos.values():
            bl_vbo.cleanup()
        self.bundesland_vbos.clear()
        self.initialized = False


# Import für ctypes
import ctypes
