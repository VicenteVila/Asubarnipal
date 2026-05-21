#!/bin/bash
# Commit directo sin git add
cd /mnt/c/Asubarnipal

echo "🔧 Verificando archivos..."

for f in core/vault_manager.py core/turboquant_config.py core/turboquant_modes.py core/turboquant_engine.py interface/handlers/vault.py skills/vault_skills.py skills/optimize_llm.py; do
    if [ -f "$f" ]; then
        echo "  ✅ $f"
    else
        echo "  ❌ $f (no existe)"
    fi
done

echo ""
echo "📝 Commit..."
git commit -m "feat: Multi-vault + TurboQuant (V20)

New features:
- VaultManager for multi-vault support
- TurboQuant engine for LLM optimization
- Input validation system
- /rate command for feedback
- 7 new vault commands
- 5 new TQ skills

Files: vault_manager.py, turboquant_*.py, vault.py, validators.py
" --allow-empty

git log --oneline -3