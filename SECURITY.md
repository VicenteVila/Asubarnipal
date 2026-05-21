# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

We take the security of Asubarnipal seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### **Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via [GitHub Issues](https://github.com/VicenteVila/Asubarnipal/issues) with the label `security`.

You should receive a response within 48 hours. If for some reason you do not, please follow up via the same channel.

### What to Include

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Preferred Languages

We prefer all communications to be in English or Spanish.

## Security Best Practices

### For Users

1. **Never commit `.env` files** - Your Telegram token, API keys, and secrets must stay private
2. **Use strong Telegram bot tokens** - Regenerate if compromised
3. **Rotate API keys regularly** - Especially Gemini and Brave keys
4. **Keep Ollama on localhost** - Do not expose Ollama API to the internet
5. **Review ingested URLs** - Malicious URLs could inject harmful content

### For Contributors

1. **No secrets in code** - Use environment variables via `.env`
2. **Sanitize user input** - All Telegram inputs are validated via `interface/handlers/validators.py`
3. **No hardcoded credentials** - Use `config.py` + `python-dotenv`
4. **Review dependencies** - Check for known vulnerabilities in `requirements.txt`

## Known Security Considerations

| Area | Status | Notes |
|------|--------|-------|
| Telegram Token | Environment variable | Stored in `.env`, never committed |
| Gemini API Keys | Environment variable | Rotated automatically by router |
| Brave API Key | Environment variable | Monthly limit enforced |
| Ollama API | Local only | Default: `127.0.0.1:11434` |
| SQLite Database | File-based | No external exposure |
| FAISS Index | File-based | No external exposure |

## Dependency Security

We recommend regularly updating dependencies and checking for vulnerabilities:

```bash
# Check for outdated packages
pip list --outdated

# Audit dependencies
pip audit

# Update requirements
pip freeze > requirements.txt
```
