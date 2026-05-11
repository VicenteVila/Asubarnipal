#!/usr/bin/env python
"""Test script simple para verificar que el bot carga."""
import sys
print("=== TEST INICIO ===", flush=True)

try:
    print("1. Importando config...", flush=True)
    import config
    print(f"   OBSIDIAN_PATH: {config.OBSIDIAN_PATH}", flush=True)
    print(f"   TOKEN: {config.TELEGRAM_TOKEN[:10] if config.TELEGRAM_TOKEN else 'None'}...", flush=True)
except Exception as e:
    print(f"ERROR config: {e}", flush=True)
    sys.exit(1)

try:
    print("2. Importando telegram...", flush=True)
    import telegram
    print("   telegram OK", flush=True)
except Exception as e:
    print(f"ERROR telegram: {e}", flush=True)
    sys.exit(1)

try:
    print("3. Importando app.service...", flush=True)
    from app.service import AsubarnipalService
    print("   service imported", flush=True)
    service = AsubarnipalService()
    print("   service created OK", flush=True)
except Exception as e:
    print(f"ERROR service: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("4. Importando BackgroundManager...", flush=True)
    from core.background_manager import BackgroundManager
    print("   BackgroundManager OK", flush=True)
except Exception as e:
    print(f"ERROR BackgroundManager: {e}", flush=True)

try:
    print("5. Creando Telegram App...", flush=True)
    from telegram.ext import Application
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    print("   Telegram App OK", flush=True)
except Exception as e:
    print(f"ERROR Telegram App: {e}", flush=True)
    sys.exit(1)

print("=== TODOS LOS IMPORTS OK ===", flush=True)
print("El bot está listo para iniciar. Saldrá un error si el token es inválido.", flush=True)
print("Para iniciar el bot real usa: python -m interface.telegram_bot", flush=True)