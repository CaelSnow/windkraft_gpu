"""
Hardware-Erkennung und Capability-Management
=============================================

Erkennt automatisch die verfügbare Hardware (CPU, GPU, RAM) und
wählt basierend darauf die optimalen Rendering-Methoden.

Features:
- GPU-Erkennung (NVIDIA, AMD, Intel, CPU-only)
- OpenGL-Version und Extensions prüfen
- Automatische Methodenwahl basierend auf Hardware
- Fallback-Strategien bei fehlender Hardware

Verwendung:
    from germany3d.hardware import HardwareCapabilities
    caps = HardwareCapabilities.detect()
    
    if caps.has_instancing:
        # Nutze GPU Instancing
    else:
        # Fallback zu Display Lists
"""

import os
import platform
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum, auto


class GPUVendor(Enum):
    """GPU-Hersteller."""
    NVIDIA = auto()
    AMD = auto()
    INTEL = auto()
    APPLE = auto()
    UNKNOWN = auto()
    NONE = auto()  # CPU-only


class RenderingTier(Enum):
    """
    Rendering-Qualitätsstufen basierend auf Hardware.
    
    HIGH:   NVIDIA RTX, AMD RX 6000+, Apple M1+
    MEDIUM: NVIDIA GTX 1000+, AMD RX 500+, Intel Iris
    LOW:    Ältere GPUs, Intel UHD
    MINIMAL: Integrated Graphics, CPU-only
    """
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    MINIMAL = auto()


@dataclass
class HardwareCapabilities:
    """
    Sammelt und verwaltet Hardware-Fähigkeiten.
    
    Wird einmal beim Start ermittelt und dann für Optimierungsentscheidungen
    verwendet.
    """
    # System
    os_name: str = ""
    os_version: str = ""
    
    # CPU
    cpu_name: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    
    # RAM
    ram_gb: float = 0.0
    
    # GPU
    gpu_vendor: GPUVendor = GPUVendor.UNKNOWN
    gpu_name: str = ""
    gpu_driver: str = ""
    gpu_vram_mb: int = 0
    
    # OpenGL
    opengl_version: str = ""
    opengl_major: int = 0
    opengl_minor: int = 0
    glsl_version: str = ""
    
    # Extensions
    extensions: List[str] = field(default_factory=list)
    
    # Fähigkeiten (abgeleitet)
    has_instancing: bool = False          # GL_ARB_draw_instanced
    has_geometry_shader: bool = False     # GL 3.2+
    has_compute_shader: bool = False      # GL 4.3+
    has_tessellation: bool = False        # GL 4.0+
    has_bindless_texture: bool = False    # GL_ARB_bindless_texture
    has_multi_draw_indirect: bool = False # GL 4.3+
    has_vbo: bool = False                 # GL 1.5+ (Vertex Buffer Objects)
    
    # Empfohlene Einstellungen
    rendering_tier: RenderingTier = RenderingTier.MINIMAL
    max_turbines_recommended: int = 1000
    use_shadows: bool = False
    use_lod: bool = True
    lod_mode: str = "standard"  # standard, aggressive, extreme
    use_frustum_culling: bool = True
    use_instanced_rendering: bool = False
    use_vbo_rendering: bool = False       # VBO statt glBegin/glEnd
    
    @classmethod
    def detect(cls) -> 'HardwareCapabilities':
        """
        Erkennt Hardware und erstellt Capabilities-Objekt.
        
        Returns:
            HardwareCapabilities mit allen erkannten Fähigkeiten
        """
        caps = cls()
        
        # System-Infos
        caps._detect_system()
        
        # GPU-Infos (mit OpenGL-Kontext)
        caps._detect_gpu()
        
        # OpenGL Extensions
        caps._detect_extensions()
        
        # Fähigkeiten ableiten
        caps._derive_capabilities()
        
        # Empfehlungen berechnen
        caps._calculate_recommendations()
        
        return caps
    
    def _detect_system(self):
        """Erkennt System-Informationen."""
        self.os_name = platform.system()
        self.os_version = platform.version()
        
        # CPU
        self.cpu_name = platform.processor() or self._get_cpu_name_wmic()
        self.cpu_threads = os.cpu_count() or 1
        self.cpu_cores = self._get_physical_cores()
        
        # RAM
        self.ram_gb = self._get_ram_gb()
    
    def _get_cpu_name_wmic(self) -> str:
        """Holt CPU-Namen via WMIC (Windows)."""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "cpu", "get", "name"],
                    capture_output=True, text=True, timeout=5
                )
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    return lines[1].strip()
        except:
            pass
        return "Unknown CPU"
    
    def _get_physical_cores(self) -> int:
        """Ermittelt physische CPU-Kerne."""
        try:
            import psutil
            return psutil.cpu_count(logical=False) or self.cpu_threads // 2
        except ImportError:
            return max(1, self.cpu_threads // 2)
    
    def _get_ram_gb(self) -> float:
        """Ermittelt verfügbaren RAM."""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            return 8.0  # Annahme: 8 GB
    
    def _check_nvidia_cuda(self) -> bool:
        """Prüft ob nvidia-smi eine GPU findet (CUDA verfügbar)."""
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0 and len(result.stdout.strip()) > 0
        except:
            return False
    
    def _detect_gpu(self):
        """Erkennt GPU über OpenGL (nutzt bestehenden Kontext wenn vorhanden)."""
        try:
            from OpenGL.GL import glGetString, glGetIntegerv
            from OpenGL.GL import GL_RENDERER, GL_VERSION, GL_VENDOR
            from OpenGL.GL import GL_SHADING_LANGUAGE_VERSION
            
            # Prüfe ob bereits ein OpenGL-Kontext existiert
            try:
                test = glGetString(GL_VERSION)
                context_exists = test is not None
            except:
                context_exists = False
            
            created_context = False
            if not context_exists:
                # Erstelle temporären Kontext nur wenn keiner existiert
                import pygame
                from pygame.locals import DOUBLEBUF, OPENGL, HIDDEN
                pygame.init()
                pygame.display.set_mode((1, 1), DOUBLEBUF | OPENGL | HIDDEN)
                created_context = True
            
            # GPU-Infos
            vendor_str = glGetString(GL_VENDOR)
            if vendor_str:
                vendor_str = vendor_str.decode('utf-8')
                self.gpu_vendor = self._parse_vendor(vendor_str)
            
            renderer = glGetString(GL_RENDERER)
            if renderer:
                self.gpu_name = renderer.decode('utf-8')
            
            version = glGetString(GL_VERSION)
            if version:
                self.gpu_driver = version.decode('utf-8')
                self._parse_opengl_version(version.decode('utf-8'))
            
            glsl = glGetString(GL_SHADING_LANGUAGE_VERSION)
            if glsl:
                self.glsl_version = glsl.decode('utf-8')
            
            # Schließe nur den selbst erstellten Kontext
            if created_context:
                import pygame
                pygame.quit()
            
        except Exception as e:
            print(f"[WARN] GPU-Erkennung fehlgeschlagen: {e}")
            self.gpu_vendor = GPUVendor.NONE
    
    def _parse_vendor(self, vendor_str: str) -> GPUVendor:
        """Parst GPU-Hersteller aus String."""
        vendor_lower = vendor_str.lower()
        
        if 'nvidia' in vendor_lower:
            return GPUVendor.NVIDIA
        elif 'amd' in vendor_lower or 'ati' in vendor_lower:
            return GPUVendor.AMD
        elif 'intel' in vendor_lower:
            return GPUVendor.INTEL
        elif 'apple' in vendor_lower:
            return GPUVendor.APPLE
        else:
            return GPUVendor.UNKNOWN
    
    def _parse_opengl_version(self, version_str: str):
        """Parst OpenGL-Version aus String."""
        self.opengl_version = version_str
        
        # Format: "4.6.0 - Build 27.20.100.8729" oder "4.6.0"
        try:
            parts = version_str.split()[0].split('.')
            self.opengl_major = int(parts[0])
            self.opengl_minor = int(parts[1]) if len(parts) > 1 else 0
        except:
            self.opengl_major = 2
            self.opengl_minor = 0
    
    def _detect_extensions(self):
        """Erkennt verfügbare OpenGL-Extensions (nutzt bestehenden Kontext)."""
        try:
            from OpenGL.GL import glGetString, glGetIntegerv
            from OpenGL.GL import GL_EXTENSIONS, GL_NUM_EXTENSIONS, GL_VERSION
            
            # Prüfe ob bereits ein OpenGL-Kontext existiert
            try:
                test = glGetString(GL_VERSION)
                context_exists = test is not None
            except:
                context_exists = False
            
            created_context = False
            if not context_exists:
                import pygame
                from pygame.locals import DOUBLEBUF, OPENGL, HIDDEN
                pygame.init()
                pygame.display.set_mode((1, 1), DOUBLEBUF | OPENGL | HIDDEN)
                created_context = True
            
            # Versuche moderne Methode (OpenGL 3.0+)
            try:
                from OpenGL.GL import glGetStringi
                num_ext = glGetIntegerv(GL_NUM_EXTENSIONS)
                self.extensions = [
                    glGetStringi(GL_EXTENSIONS, i).decode('utf-8')
                    for i in range(num_ext)
                ]
            except:
                # Fallback: Legacy-Methode
                ext_str = glGetString(GL_EXTENSIONS)
                if ext_str:
                    self.extensions = ext_str.decode('utf-8').split()
            
            if created_context:
                import pygame
                pygame.quit()
            
        except Exception as e:
            print(f"[WARN] Extension-Erkennung fehlgeschlagen: {e}")
            self.extensions = []
    
    def _derive_capabilities(self):
        """Leitet Fähigkeiten aus OpenGL-Version und Extensions ab."""
        # VBOs (GL 1.5+ oder ARB_vertex_buffer_object)
        self.has_vbo = (
            (self.opengl_major >= 2) or
            (self.opengl_major == 1 and self.opengl_minor >= 5) or
            'GL_ARB_vertex_buffer_object' in self.extensions
        )
        
        # Instancing (GL 3.1+ oder ARB_draw_instanced)
        self.has_instancing = (
            (self.opengl_major >= 3 and self.opengl_minor >= 1) or
            'GL_ARB_draw_instanced' in self.extensions or
            'GL_EXT_draw_instanced' in self.extensions
        )
        
        # Geometry Shader (GL 3.2+)
        self.has_geometry_shader = (
            (self.opengl_major >= 3 and self.opengl_minor >= 2) or
            self.opengl_major >= 4
        )
        
        # Tessellation (GL 4.0+)
        self.has_tessellation = self.opengl_major >= 4
        
        # Compute Shader (GL 4.3+)
        self.has_compute_shader = (
            self.opengl_major >= 4 and self.opengl_minor >= 3
        )
        
        # Multi-Draw Indirect (GL 4.3+)
        self.has_multi_draw_indirect = (
            (self.opengl_major >= 4 and self.opengl_minor >= 3) or
            'GL_ARB_multi_draw_indirect' in self.extensions
        )
        
        # Bindless Texture
        self.has_bindless_texture = (
            'GL_ARB_bindless_texture' in self.extensions or
            'GL_NV_bindless_texture' in self.extensions
        )
    
    def _calculate_recommendations(self):
        """Berechnet empfohlene Einstellungen basierend auf Hardware."""
        
        # Rendering Tier bestimmen
        if self.gpu_vendor == GPUVendor.NVIDIA:
            gpu_upper = self.gpu_name.upper()
            
            # HIGH Tier: RTX-Serie, GTX 16/20-Serie, Tesla/Datacenter GPUs (T4, V100, A100, etc.)
            if any(x in gpu_upper for x in ['RTX', 'GTX 16', 'GTX 20', 'GTX 30', 'GTX 40',
                                             'TESLA', 'T4', 'V100', 'A100', 'A10', 'A30', 'A40',
                                             'H100', 'L4', 'L40', 'QUADRO RTX', 'QUADRO P']):
                self.rendering_tier = RenderingTier.HIGH
            elif any(x in gpu_upper for x in ['GTX 10', 'GTX 9', 'QUADRO']):
                self.rendering_tier = RenderingTier.MEDIUM
            else:
                self.rendering_tier = RenderingTier.MEDIUM  # NVIDIA ist immer mindestens MEDIUM
                
        elif self.gpu_vendor == GPUVendor.AMD:
            gpu_upper = self.gpu_name.upper()
            if any(x in gpu_upper for x in ['RX 6', 'RX 7', 'MI100', 'MI200', 'MI300', 'INSTINCT']):
                self.rendering_tier = RenderingTier.HIGH
            elif any(x in gpu_upper for x in ['RX 5', 'VEGA', 'VII']):
                self.rendering_tier = RenderingTier.MEDIUM
            else:
                self.rendering_tier = RenderingTier.MEDIUM  # AMD ist auch mindestens MEDIUM
                
        elif self.gpu_vendor == GPUVendor.INTEL:
            if 'Iris' in self.gpu_name or 'Arc' in self.gpu_name:
                self.rendering_tier = RenderingTier.MEDIUM
            else:
                self.rendering_tier = RenderingTier.LOW
                
        elif self.gpu_vendor == GPUVendor.APPLE:
            self.rendering_tier = RenderingTier.MEDIUM
        else:
            self.rendering_tier = RenderingTier.MINIMAL
        
        # =====================================================================
        # WICHTIG: Prüfe ob NVIDIA GPU vorhanden aber llvmpipe aktiv
        # (typisch für Google Colab - GPU nur für CUDA, nicht OpenGL)
        # =====================================================================
        gpu_name_lower = self.gpu_name.lower()
        is_software_rendering = 'llvmpipe' in gpu_name_lower or 'swrast' in gpu_name_lower
        
        # Prüfe ob nvidia-smi eine GPU findet (CUDA verfügbar)
        has_nvidia_cuda = self._check_nvidia_cuda()
        
        if is_software_rendering and has_nvidia_cuda:
            print("\n  ⚠️  HINWEIS: NVIDIA GPU erkannt, aber OpenGL nutzt Software-Rendering!")
            print("      → Typisch für Google Colab / Headless Server")
            print("      → GPU wird für CUDA genutzt, nicht für OpenGL")
            print("      → VBOs werden trotzdem aktiviert (schneller als glBegin/glEnd)")
        
        # Einstellungen basierend auf Tier
        # ALLE FEATURES AKTIVIERT - Benutzer möchte volle Qualität
        # LOD und Quadtree sorgen für gute Performance
        
        if self.rendering_tier == RenderingTier.HIGH:
            self.max_turbines_recommended = 50000
            self.use_shadows = True
            self.lod_mode = "standard"
            self.use_instanced_rendering = self.has_instancing
            self.use_vbo_rendering = self.has_vbo  # VBO für GPU-Beschleunigung
            
        elif self.rendering_tier == RenderingTier.MEDIUM:
            self.max_turbines_recommended = 50000
            self.use_shadows = True
            self.lod_mode = "aggressive"
            self.use_instanced_rendering = self.has_instancing
            self.use_vbo_rendering = self.has_vbo  # VBO für GPU-Beschleunigung
            
        elif self.rendering_tier == RenderingTier.LOW:
            # Intel UHD etc. - trotzdem VBOs wenn verfügbar
            self.max_turbines_recommended = 50000
            self.use_shadows = True
            self.lod_mode = "aggressive"
            self.use_instanced_rendering = False
            self.use_vbo_rendering = self.has_vbo  # VBOs sind auch mit Software schneller
            
        else:  # MINIMAL (llvmpipe, etc.)
            # Software-Rendering - VBOs trotzdem nutzen wenn verfügbar
            self.max_turbines_recommended = 50000
            self.use_shadows = True
            self.lod_mode = "extreme"  # Aggressiveres LOD für Software
            self.use_instanced_rendering = False
            self.use_vbo_rendering = self.has_vbo  # VBOs auch mit llvmpipe ~2x schneller
        
        # RAM-basierte Anpassungen
        if self.ram_gb < 4:
            self.max_turbines_recommended = min(5000, self.max_turbines_recommended)
        elif self.ram_gb < 8:
            self.max_turbines_recommended = min(15000, self.max_turbines_recommended)
    
    def print_summary(self):
        """Gibt Hardware-Zusammenfassung aus."""
        print("\n" + "="*60)
        print("HARDWARE-ERKENNUNG")
        print("="*60)
        print(f"  OS:            {self.os_name} {self.os_version}")
        print(f"  CPU:           {self.cpu_name}")
        print(f"  CPU Kerne:     {self.cpu_cores} physisch, {self.cpu_threads} logisch")
        print(f"  RAM:           {self.ram_gb:.1f} GB")
        print(f"  GPU:           {self.gpu_name}")
        print(f"  GPU Vendor:    {self.gpu_vendor.name}")
        print(f"  OpenGL:        {self.opengl_version}")
        print(f"  GLSL:          {self.glsl_version}")
        
        # Warnung wenn Software-Rendering erkannt
        if self.gpu_vendor == GPUVendor.NONE or 'llvmpipe' in self.gpu_name.lower() or 'mesa' in self.gpu_name.lower():
            print()
            print("  ⚠️  WARNUNG: Software-Rendering erkannt!")
            print("      GPU wird NICHT genutzt. Für GPU-Rendering:")
            print("      - Prüfe ob GPU-Treiber installiert ist")
            print("      - Auf Server: Nutze EGL oder VirtualGL")
        
        print()
        print("  Fähigkeiten:")
        print(f"    VBOs:             {'✓' if self.has_vbo else '✗'}")
        print(f"    Instancing:       {'✓' if self.has_instancing else '✗'}")
        print(f"    Geometry Shader:  {'✓' if self.has_geometry_shader else '✗'}")
        print(f"    Compute Shader:   {'✓' if self.has_compute_shader else '✗'}")
        print(f"    Tessellation:     {'✓' if self.has_tessellation else '✗'}")
        print()
        print("  Empfehlungen:")
        print(f"    Rendering Tier:   {self.rendering_tier.name}")
        print(f"    Max Turbinen:     {self.max_turbines_recommended:,}")
        print(f"    LOD-Modus:        {self.lod_mode}")
        print(f"    Schatten:         {'Ja' if self.use_shadows else 'Nein'}")
        print(f"    VBO-Rendering:    {'Ja (GPU)' if self.use_vbo_rendering else 'Nein (CPU)'}")
        print(f"    Instancing:       {'Ja' if self.use_instanced_rendering else 'Nein'}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für JSON-Export."""
        return {
            'system': {
                'os_name': self.os_name,
                'os_version': self.os_version,
            },
            'cpu': {
                'name': self.cpu_name,
                'cores': self.cpu_cores,
                'threads': self.cpu_threads,
            },
            'ram_gb': self.ram_gb,
            'gpu': {
                'vendor': self.gpu_vendor.name,
                'name': self.gpu_name,
                'driver': self.gpu_driver,
                'opengl_version': self.opengl_version,
                'glsl_version': self.glsl_version,
            },
            'capabilities': {
                'has_instancing': self.has_instancing,
                'has_geometry_shader': self.has_geometry_shader,
                'has_compute_shader': self.has_compute_shader,
                'has_tessellation': self.has_tessellation,
                'has_multi_draw_indirect': self.has_multi_draw_indirect,
            },
            'recommendations': {
                'rendering_tier': self.rendering_tier.name,
                'max_turbines': self.max_turbines_recommended,
                'lod_mode': self.lod_mode,
                'use_shadows': self.use_shadows,
                'use_instanced_rendering': self.use_instanced_rendering,
            }
        }


# Globale Instanz (lazy initialization)
_capabilities: Optional[HardwareCapabilities] = None


def get_capabilities() -> HardwareCapabilities:
    """
    Gibt die Hardware-Capabilities zurück (Singleton).
    
    Wird beim ersten Aufruf erkannt und dann gecacht.
    """
    global _capabilities
    if _capabilities is None:
        _capabilities = HardwareCapabilities.detect()
    return _capabilities


def reset_capabilities():
    """Setzt die Capabilities zurück (für Tests)."""
    global _capabilities
    _capabilities = None
