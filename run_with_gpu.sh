#!/bin/bash
# =============================================================================
# GPU-Rendering auf Headless Server - EGL Version
# =============================================================================
#
# GLX funktioniert nicht mit NVIDIA + Xvfb (BadAlloc Error)
# Lösung: EGL für echtes headless GPU-Rendering
#
# Verwendung:
#   chmod +x run_with_gpu.sh
#   ./run_with_gpu.sh python main.py --record
#
# =============================================================================

echo "=========================================="
echo "NVIDIA Tesla T4 - Headless GPU Rendering"
echo "=========================================="

# Kein Audio auf Server
export SDL_AUDIODRIVER=dummy

# SDL/Pygame: Offscreen Rendering
export SDL_VIDEODRIVER=offscreen

# PyOpenGL: EGL Backend für headless NVIDIA
export PYOPENGL_PLATFORM=egl

echo "EGL Headless Rendering aktiviert"
echo "SDL_VIDEODRIVER=$SDL_VIDEODRIVER"
echo "PYOPENGL_PLATFORM=$PYOPENGL_PLATFORM"
echo ""

"$@"
