#!/bin/bash
# Script de commit para Asubarnipal V20
# Ejecuta: bash scripts/commit_v20.sh

set -e

cd /mnt/c/Asubarnipal

echo "📦 Stageando archivos..."
git add core/vault_manager.py
git add core/turboquant_config.py
git add core/turboquant_modes.py
git add core/turboquant_engine.py
git add interface/handlers/vault.py
git add interface/handlers/validators.py
git add skills/vault_skills.py
git add skills/optimize_llm.py

git add config.py
git add core/wiki.py
git add core/llm_router.py
git add index/rag.py
git add interface/handlers/chat.py
git add interface/handlers/agente.py
git add interface/handlers/busqueda.py
git add interface/handlers/wiki.py
git add interface/handlers/__init__.py
git add interface/telegram_bot.py
git add AGENTS.md
git add data/manual_agente.md

echo "📝 Creando commit..."
git commit -m "feat: Multi-vault support + TurboQuant optimization

- Add vault management (7 commands, 7 skills)
- Add TurboQuant engine for LLM optimization
- Add input validation (validators.py)
- Add /rate command for agent feedback
- Update manual to V20
- All handlers use structured logging"

echo "✅ Commit creado!"
git log --oneline -3