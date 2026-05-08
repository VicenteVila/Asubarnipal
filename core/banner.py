"""Asubarnipal V18 - Banner ASCII"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


BANNER = r"""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║     🦁  ASUBARNIPAL V18 - ARQUITECTO DE GRAFOS DE CONOCIMIENTO          ║
    ║                                                                          ║
    ║        ██████  ███████ ████████  ██████  ███    ██ ██ ████████         ║
    ║       ██       ██         ██    ██    ██ ████   ██ ██ ██               ║
    ║       ██   ███ █████      ██    ██    ██ ██ ██  ██ ██ ██████           ║
    ║       ██    ██ ██         ██    ██    ██ ██  ██  ██ ██ ██               ║
    ║        ██████  ███████    ██     ██████  ██   ████ ██ ██               ║
    ║                                                                          ║
    ║     ┌─────────────────────────────────────────────────────────────┐     ║
    ║     │  🐎  Guerrero a caballo enfrentando al león del saber     │     ║
    ║     │  🏹  Arquitecto de grafos de conocimiento - Obsidian      │     ║
    ║     │  🛡️  Procesando multimedia, web, PDFs y YouTube          │     ║
    ║     └─────────────────────────────────────────────────────────────┘     ║
    ║                                                                          ║
    ║        ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       ║
    ║        │  🤖 LLM │───→│  🕸️ GRAFO│───→│  📚 WIKI │───→│  🗺️ MOC  │       ║
    ║        └─────────┘    └─────────┘    └─────────┘    └─────────┘       ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
"""


DIOS_ASIRIO = r"""
                          ╱╲
                         ╱  ╲
                        ╱ ▽ ╲
                       ╱     ╲
                      ╱  ↓↔   ╲
                     ╱─────────╲
                    ╱           ╲
                   ╱  ╭───╮     ╲
                  ╱   │ ♔ │      ╲
                 ╱    ╰───╯       ╲
                ╱                ╲
               ╱    ♔    ♔       ╲
               ╲               ╱
                ╲           ╱
                 ╲       ╱
                  ╲╱╲
                   ╲│╱
                   ╱│╲
                  ╱ │ ╲
                 ╱  │  ╲
                ╱   │   ╲
               ╱    │    ╲
              ╱     │     ╲
             ╱      │      ╲
            ╱       │       ╲
           ╱        │        ╲
          ╱═╪╪╪╪╪╪╪╪╪╪╪╪╪═╲
          ╲                ╱
           ╲            ╱
            ╲        ╱
             ╲    ╱
              ╲╱
"""


def mostrar_banner():
    """Muestra el banner principal."""
    print(BANNER)


def mostrar_dios_asirio():
    """Muestra el relieve del dios asirio."""
    print(DIOS_ASIRIO)


def imagen_a_ascii(img, ancho=80):
    """Convierte una imagen PIL a arte ASCII."""
    caracteres = "@%#*+=-:. "
    ratio = img.height / img.width
    alto = int(ancho * ratio * 0.5)
    img = img.resize((ancho, alto))
    img = img.convert('L')
    pixeles = img.getdata()
    ascii_str = ""
    for i, pixel in enumerate(pixeles):
        indice = int((pixel / 255) * (len(caracteres) - 1))
        ascii_str += caracteres[indice]
        if (i + 1) % ancho == 0:
            ascii_str += "\n"
    return ascii_str


def cargar_imagen_ascii(base_dir=None):
    """Busca y carga la imagen asubarnipal.png."""
    if not HAS_PIL:
        print("\n  📦 Instala Pillow: pip install Pillow")
        return
    
    if base_dir is None:
        base_dir = Path(__file__).parent
    
    candidates = [
        base_dir / "asubarnipal.png",
        base_dir / "asubarnipal.jpg",
        base_dir.parent / "asubarnipal.png",
        base_dir.parent / "asubarnipal.jpg",
    ]
    
    imagen_path = None
    for ruta in candidates:
        if ruta.exists():
            imagen_path = ruta
            break
    
    if imagen_path:
        try:
            img = Image.open(imagen_path)
            ascii_str = imagen_a_ascii(img, ancho=80)
            print("\n" + "═" * 82)
            print("  🖼️  RELIEVE ASUBARNIPAL CARGADO DESDE:", imagen_path)
            print("═" * 82)
            print(ascii_str)
            print("═" * 82 + "\n")
        except Exception as e:
            print(f"\n  ⚠️ No se pudo cargar la imagen: {e}\n")
    else:
        print("\n  💡 Tip: Coloca 'asubarnipal.png' para ver el relieve.\n")


def inicio_completo():
    """Secuencia de inicio completa con banner y arte."""
    mostrar_banner()
    print()
    cargar_imagen_ascii()
    print("  🏛️ Asubarnipal V18 listo para servir.\n")


if __name__ == "__main__":
    inicio_completo()