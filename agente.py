"""
ASUBARNIPAL V18
Entry point that combines interface + wiki engine.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from core.wiki_engine import WikiEngine, guardar_schema, WikiVectorIndex
from core.background_manager import BackgroundManager, AgentState
from core.banner import inicio_completo
from interface import telegram_bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    inicio_completo()
    
    guardar_schema()
    
    logger.info("📚 Wiki Engine listo")
    logger.info(f"📁 Vault: {config.OBSIDIAN_PATH}")
    logger.info(f"🕸️ Grafo: {config.GRAPH_STORE_PATH}")
    
    AgentState().mark_alive()
    
    telegram_bot.main()


if __name__ == "__main__":
    main()