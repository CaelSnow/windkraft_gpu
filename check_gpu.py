#!/usr/bin/env python3
"""
GPU-Check-Skript - Zeigt ob wirklich GPU oder Software-Rendering verwendet wird.
Unterstützt EGL für headless NVIDIA Server.
"""

import os
import sys

def check_gpu():
    print("=" * 60)
    print("GPU-DIAGNOSE")
    print("=" * 60)
    
    # 1. Umgebungsvariablen prüfen
    print("\n[1] Relevante Umgebungsvariablen:")
    env_vars = ['DISPLAY', 'SDL_VIDEODRIVER', 'PYOPENGL_PLATFORM',
                'MESA_GL_VERSION_OVERRIDE', 'LIBGL_ALWAYS_SOFTWARE', 
                '__GLX_VENDOR_LIBRARY_NAME', 'EGL_PLATFORM']
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
    
    # 3. PyOpenGL mit EGL
    print("\n[3] OpenGL-Kontext erstellen:")
    
    pyopengl_platform = os.environ.get('PYOPENGL_PLATFORM', '')
    sdl_driver = os.environ.get('SDL_VIDEODRIVER', '')
    
    print(f"    PYOPENGL_PLATFORM: {pyopengl_platform}")
    print(f"    SDL_VIDEODRIVER: {sdl_driver}")
    
    try:
        # Pygame für OpenGL-Kontext
        import pygame
        from pygame.locals import DOUBLEBUF, OPENGL
        
        pygame.init()
        
        # Offscreen-Modus: Kein RESIZABLE
        flags = DOUBLEBUF | OPENGL
        screen = pygame.display.set_mode((100, 100), flags)
        
        from OpenGL.GL import glGetString, GL_RENDERER, GL_VENDOR, GL_VERSION
        
        renderer = glGetString(GL_RENDERER)
        vendor = glGetString(GL_VENDOR)
        version = glGetString(GL_VERSION)
        
        # Bytes zu String
        renderer = renderer.decode('utf-8') if renderer else "Unknown"
        vendor = vendor.decode('utf-8') if vendor else "Unknown"
        version = version.decode('utf-8') if version else "Unknown"
        
        print(f"\n    GL_RENDERER: {renderer}")
        print(f"    GL_VENDOR:   {vendor}")
        print(f"    GL_VERSION:  {version}")
        
        # Analyse
        print("\n[4] ANALYSE:")
        renderer_lower = renderer.lower()
        vendor_lower = vendor.lower()
        
        if 'llvmpipe' in renderer_lower:
            print("    ⚠️  SOFTWARE-RENDERING (llvmpipe)!")
            print("    → GPU wird NICHT genutzt!")
            print("    → Mesa Software Rasterizer ist aktiv")
            print("\n    Für NVIDIA GPU auf headless Server:")
            print("    export SDL_VIDEODRIVER=offscreen")
            print("    export PYOPENGL_PLATFORM=egl")
            print("    python check_gpu.py")
            return False
            
        elif 'nvidia' in vendor_lower or 'nvidia' in renderer_lower:
            print("    ✓ NVIDIA GPU wird genutzt!")
            print("    → Hardware-Rendering aktiv")
            if 't4' in renderer_lower or 'tesla' in renderer_lower:
                print("    → Tesla T4 erkannt (Datacenter GPU)")
            return True
            
        elif 'mesa' in renderer_lower or 'mesa' in vendor_lower:
            print("    ⚠️  Mesa-Renderer (möglicherweise Software)")
            return False
            
        else:
            print(f"    ? Renderer: {renderer}")
            return True
        
    except Exception as e:
        print(f"    ✗ OpenGL-Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            pygame.quit()
        except:
            pass
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    success = check_gpu()
    sys.exit(0 if success else 1)
