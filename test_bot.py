#!/usr/bin/env python
"""Test script para debug."""
import sys
print("=== TEST INICIO ===", flush=True)

print("1. config...", flush=True)
import config

print("2. llm_router...", flush=True)
from core.llm_router import LLMRouter

print("3. skill_registry...", flush=True)
from core.skill_registry import SkillRegistry

print("4. rag...", flush=True)
from index.rag import RAGEngine

print("5. AgentState...", flush=True)
from core.background_manager import AgentState

print("6. LLMRouter()...", flush=True)
llm = LLMRouter()

print("7. SkillRegistry()...", flush=True)
skills = SkillRegistry()

print("8. RAGEngine...", flush=True)
from pathlib import Path
rag = RAGEngine(config.INDEX_DIR / "index.faiss")

print("=== SERVICE CREADO ===", flush=True)

print("9. Telegram Application...", flush=True)
from telegram.ext import Application
app = Application.builder().token(config.TELEGRAM_TOKEN).build()

print("=== TODO OK ===", flush=True)