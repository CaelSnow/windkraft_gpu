#!/usr/bin/env python3
"""
GPU-Check-Skript - Zeigt ob wirklich GPU oder Software-Rendering verwendet wird.
"""

import os
import sys

def check_gpu():
    print("=" * 60)
    print("GPU-DIAGNOSE")
    print("=" * 60)
    
    # 1. Umgebungsvariablen prüfen
    print("\n[1] Relevante Umgebungsvariablen:")
    env_vars = ['DISPLAY', 'MESA_GL_VERSION_OVERRIDE', 'LIBGL_ALWAYS_SOFTWARE', 
                '__GLX_VENDOR_LIBRARY_NAME', 'VGL_DISPLAY', 'EGL_PLATFORM']
    for var in env_vars:
        val = os.environ.get(var, "(nicht gesetzt)")
        print(f"    {var}: {val}")
    
    # 2. NVIDIA SMI prüfen
    print("\n[2] nvidia-smi Ausgabe:")
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version,memory.total', 
                                '--format=csv,noheader'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"    ✓ NVIDIA GPU gefunden: {result.stdout.strip()}")
        else:
            print(f"    ✗ nvidia-smi fehlgeschlagen: {result.stderr}")
    except FileNotFoundError:
        print("    ✗ nvidia-smi nicht gefunden (kein NVIDIA-Treiber?)")
    except Exception as e:
        print(f"    ✗ Fehler: {e}")
    
    # 3. PyOpenGL Info
    print("\n[3] OpenGL-Kontext erstellen und prüfen:")
    try:
        import pygame
        from pygame.locals import DOUBLEBUF, OPENGL, HIDDEN
        
        pygame.init()
        # Versuche Hidden Window (für Server ohne Display)
        try:
            screen = pygame.display.set_mode((100, 100), DOUBLEBUF | OPENGL | HIDDEN)
        except:
            # Fallback: Normales Fenster
            screen = pygame.display.set_mode((100, 100), DOUBLEBUF | OPENGL)
        
        from OpenGL.GL import glGetString, GL_RENDERER, GL_VENDOR, GL_VERSION
        
        renderer = glGetString(GL_RENDERER).decode('utf-8')
        vendor = glGetString(GL_VENDOR).decode('utf-8')
        version = glGetString(GL_VERSION).decode('utf-8')
        
        print(f"    GL_RENDERER: {renderer}")
        print(f"    GL_VENDOR:   {vendor}")
        print(f"    GL_VERSION:  {version}")
        
        # Analyse
        print("\n[4] ANALYSE:")
        renderer_lower = renderer.lower()
        
        if 'llvmpipe' in renderer_lower:
            print("    ⚠️  SOFTWARE-RENDERING (llvmpipe)!")
            print("    → GPU wird NICHT genutzt!")
            print("    → Mesa Software Rasterizer ist aktiv")
            print("\n    Lösung für NVIDIA GPU Server:")
            print("    export __GLX_VENDOR_LIBRARY_NAME=nvidia")
            print("    export EGL_PLATFORM=device")
            print("    Oder: Nutze VirtualGL / xvfb-run")
            
        elif 'mesa' in renderer_lower and 'nvidia' not in vendor.lower():
            print("    ⚠️  MESA-RENDERER (möglicherweise Software)")
            print("    → Könnte Software oder Intel GPU sein")
            
        elif 'nvidia' in vendor.lower() or 'nvidia' in renderer_lower:
            print("    ✓ NVIDIA GPU wird genutzt!")
            print("    → Hardware-Rendering aktiv")
            # Prüfe welche GPU
            if 't4' in renderer_lower:
                print("    → Tesla T4 erkannt (Datacenter GPU)")
            elif 'v100' in renderer_lower:
                print("    → Tesla V100 erkannt (Datacenter GPU)")
            elif 'a100' in renderer_lower:
                print("    → A100 erkannt (Datacenter GPU)")
        else:
            print(f"    ? Unbekannter Renderer: {renderer}")
        
        pygame.quit()
        
    except Exception as e:
        print(f"    ✗ OpenGL-Fehler: {e}")
        print("\n    Mögliche Ursachen:")
        print("    - Kein X11/Display verfügbar")
        print("    - OpenGL-Bibliothek fehlt")
        print("    - Treiber nicht korrekt installiert")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_gpu()
