#!/bin/bash
# =============================================================================
# GPU-Rendering auf Headless Server (Tesla T4, V100, A100, etc.)
# =============================================================================
#
# Problem: Ohne X11 Display fällt OpenGL auf Mesa/llvmpipe (Software) zurück
# Lösung:  Virtuelles Framebuffer (Xvfb) + NVIDIA als GLX-Vendor
#
# Verwendung:
#   chmod +x run_with_gpu.sh
#   ./run_with_gpu.sh python main.py --record
#
# =============================================================================

# NVIDIA als OpenGL-Vendor erzwingen
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __NV_PRIME_RENDER_OFFLOAD=1
export __VK_LAYER_NV_optimus=NVIDIA_only

# EGL für headless rendering
export EGL_PLATFORM=device

# Mesa Software-Rendering deaktivieren
export LIBGL_ALWAYS_SOFTWARE=0

# SDL/Pygame Einstellungen für bessere Kompatibilität
export SDL_AUDIODRIVER=dummy
export SDL_VIDEODRIVER=x11

# Xvfb (virtuelles Display) starten und Befehl ausführen
echo "=========================================="
echo "GPU-Rendering mit Tesla T4"
echo "=========================================="
echo "Starte virtuelles Display mit Xvfb..."

# Prüfe ob Xvfb installiert ist
if ! command -v xvfb-run &> /dev/null; then
    echo "FEHLER: xvfb-run nicht gefunden!"
    echo "Installiere mit: sudo apt-get install xvfb"
    exit 1
fi

# Führe Befehl mit virtuellem Display aus
# -a = automatisch freien Display-Port finden
# -s = Screen-Optionen
xvfb-run -a -s "-screen 0 1920x1080x24 +extension GLX" "$@"
