@echo off
chcp 65001 > nul
echo ================================================
echo    ASUBARNIPAL - CLEANUP & PUSH
echo ================================================
echo.

echo [1/5] Removing tracked files that should be ignored...
echo.

echo Removing .env from git tracking (keeping local file)...
git rm --cached .env 2>nul

echo Removing __pycache__ directories from git...
git rm -r --cached __pycache__ 2>nul
git rm -r --cached */__pycache__ 2>nul
git rm -r --cached */*/__pycache__ 2>nul
git rm -r --cached */*/*/__pycache__ 2>nul

echo Removing venv_linux from git...
git rm -r --cached venv_linux 2>nul

echo Removing data files from git (keeping structure)...
git rm --cached data/*.db 2>nul
git rm --cached data/*.sqlite 2>nul
git rm --cached data/*.faiss 2>nul
git rm --cached data/*.index 2>nul
git rm --cached data/*.json 2>nul
git rm --cached data/*.log 2>nul
git rm --cached data/*.docs.json 2>nul

echo.
echo [2/5] Verifying cleanup...
git status --short
echo.

echo [3/5] Committing cleanup and new files...
git add -A
git commit -m "chore: professional repository cleanup and setup

- Remove .env, __pycache__, venv_linux from git tracking
- Add .github/workflows/ci.yml (tests, lint, import validation)
- Add .github/ISSUE_TEMPLATE/ (bug report, feature request)
- Add .github/PULL_REQUEST_TEMPLATE.md
- Add CODE_OF_CONDUCT.md (Contributor Covenant)
- Add SECURITY.md (vulnerability reporting + best practices)
- Add .env.example (documented template for environment variables)
- Add Makefile (common development commands)
- Update .gitignore (comprehensive patterns)
- Add README.md (professional documentation)
- Add pyproject.toml (PEP 621 modern packaging)
- Add examples/ (4 demo scripts)
- Add tests/ (4 new test modules)
- Add CONTRIBUTING.md (professional guidelines)
- Add LICENSE (MIT)"

if errorlevel 1 (
    echo WARNING: No hay cambios para commit
    echo.
) else (
    echo.
    echo [4/5] Subiendo a remote...
    git push
    if errorlevel 1 (
        echo ERROR: No se pudo hacer push
        echo Verifica tu conexion a internet y credenciales de git
        pause
        exit /b 1
    )
)

echo.
echo [5/5] Verificando estado final...
git log --oneline -3
echo.

echo ================================================
echo    REPOSITORIO ACTUALIZADO EXITOSAMENTE
echo ================================================
echo.
echo Archivos anadidos:
echo   + .github/workflows/ci.yml
echo   + .github/ISSUE_TEMPLATE/bug_report.yml
echo   + .github/ISSUE_TEMPLATE/feature_request.yml
echo   + .github/PULL_REQUEST_TEMPLATE.md
echo   + CODE_OF_CONDUCT.md
echo   + SECURITY.md
echo   + .env.example
echo   + Makefile
echo   + README.md (rewrite)
echo   + pyproject.toml
echo   + examples/ (4 scripts)
echo   + tests/ (4 modulos nuevos)
echo   + CONTRIBUTING.md (rewrite)
echo   + LICENSE
echo   + .gitignore (update)
echo.
echo Archivos eliminados del tracking:
echo   - .env (ahora ignorado)
echo   - __pycache__/ (ahora ignorado)
echo   - venv_linux/ (ahora ignorado)
echo   - data/*.db, *.sqlite, *.faiss, *.json, *.log
echo.
echo Proximos pasos recomendados:
echo   1. Configurar GitHub Topics en la web del repo
echo   2. Crear un Release v2.0.0
echo   3. Activar GitHub Pages para documentacion
echo.
pause
