import logging
import os
import time
from typing import Any, Optional

import requests

import config

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self):
        self.base_url = config.OLLAMA_BASE_URL
        self.model = config.OLLAMA_MODEL
        self.ollama_client = None
        self.use_ollama = self._check_ollama()
        self.gemini_keys = config.GEMINI_KEYS or []
        self.current_key_index = 0
        self._init_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is running."""
        try:
            return requests.get(f"{self.base_url}/api/tags", timeout=3).status_code == 200
        except:
            return False
    
    def rotate_gemini(self):
        """Rotate to next Gemini key."""
        if self.gemini_keys:
            self.current_key_index = (self.current_key_index + 1) % len(self.gemini_keys)
            logger.info("🔄 Rotando clave Gemini...")
    
    def _init_ollama(self):
        try:
            from ollama import Client
            self.ollama_client = Client(self.base_url)
            logger.info(f"Ollama client connected to {self.base_url}")
        except ImportError:
            logger.warning("ollama not installed, using HTTP fallback")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")
    
    def chat(self, messages: list[dict], model: str = None, tools: list = None, **kwargs) -> dict:
        start = time.time()
        target_model = model or self.model
        
        standard_messages = self._prepare_messages(messages)
        
        try:
            if self.ollama_client:
                resp = self.ollama_client.chat(
                    model=target_model,
                    messages=standard_messages,
                    tools=tools,
                )
                result = {
                    "response": resp.message.content,
                    "tool_calls": getattr(resp.message, "tool_calls", None) or [],
                    "model": target_model,
                    "time": time.time() - start,
                }
                logger.info(f"🤖 AGENTE - Respuesta recibida de {target_model}")
                return result
            else:
                return self._http_chat(target_model, standard_messages, tools or [], start)
                
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            raise
    
    def _http_chat(self, model: str, messages: list[dict], tools: list, start: float) -> dict:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools if tools else None,
        }
        payload = {k: v for k, v in payload.items() if v}
        
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        
        return {
            "response": data.get("message", {}).get("content", ""),
            "tool_calls": data.get("message", {}).get("tool_calls", []),
            "model": model,
            "time": time.time() - start,
        }
    
    def _prepare_messages(self, messages: list[dict]) -> list[dict]:
        prepared = []
        for msg in messages:
            if isinstance(msg, dict):
                prepared.append(msg)
            elif hasattr(msg, "role") and hasattr(msg, "content"):
                prepared.append({"role": msg.role, "content": msg.content})
        return prepared
    
    def call_agent(self, messages: list[dict], tools: list = None) -> dict:
        return self.chat(messages, tools=tools)
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate with fallback: Ollama → Gemini."""
        max_retries = 3
        delay = 2
        
        for attempt in range(max_retries):
            if self.use_ollama:
                try:
                    result = self.chat([{"role": "user", "content": prompt}], **kwargs)
                    return result.get("response", "")
                except Exception as e:
                    logger.warning(f"⚠️ Ollama retry {attempt+1}: {e}")
            
            if self.gemini_keys:
                try:
                    key = self.gemini_keys[self.current_key_index % len(self.gemini_keys)]
                    result = self._gemini_chat(prompt, key)
                    return result.get("response", "")
                except Exception as e:
                    logger.warning(f"⚠️ Gemini retry {attempt+1}: {e}")
                    self.rotate_gemini()
                    time.sleep(delay)
                    delay *= 2
        
        return "⚠️ Fallo crítico en el razonamiento."
    
    def _gemini_chat(self, prompt: str, key: str) -> dict:
        """Chat using Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"

        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}

        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return {"response": text, "model": "gemini-2.0-flash"}

    # =============================================================================
    # TurboQuant Integration
    # =============================================================================

    def call_with_turbo(self, messages: list[dict], mode: str = "consultor",
                        tools: list = None, **kwargs) -> dict:
        """
        Call LLM with TurboQuant optimizations for a chat mode.
        Auto-detects model and applies optimal settings.
        """
        try:
            from core.turboquant_engine import apply_chat_mode, get_engine

            engine = get_engine()
            apply_result = engine.apply_mode(mode)

            params = engine.get_optimized_params()

            options = params.get("options", {})
            options.update(kwargs)

            result = self.chat(messages, tools=tools, **options)
            result["turbo"] = {
                "mode": mode,
                "context": params["context"],
                "cache_k": params["turbo"]["cache_k"],
                "cache_v": params["turbo"]["cache_v"],
            }

            return result

        except ImportError:
            logger.warning("TurboQuant not available, using standard call")
            return self.chat(messages, tools=tools, **kwargs)
        except Exception as e:
            logger.warning(f"TurboQuant call failed: {e}, falling back to standard")
            return self.chat(messages, tools=tools, **kwargs)

    def get_turbo_status(self) -> dict:
        """Get current TurboQuant status."""
        try:
            from core.turboquant_engine import get_turbo_status as tq_status
            return tq_status()
        except ImportError:
            return {"success": False, "error": "TurboQuant not available"}

    def apply_turbo_mode(self, mode: str) -> dict:
        """Apply a specific TurboQuant mode."""
        try:
            from core.turboquant_engine import apply_chat_mode
            return apply_chat_mode(mode)
        except ImportError:
            return {"success": False, "error": "TurboQuant not available"}


class GeminiRouter:
    def __init__(self):
        self.keys = config.GEMINI_KEYS
        self.current_key = 0
    
    def chat(self, messages: list[dict], model: str = "gemini-2.0-flash", **kwargs) -> dict:
        if not self.keys:
            raise ValueError("No Gemini keys configured")
        
        key = self.keys[self.current_key % len(self.keys)]
        self.current_key += 1
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        
        contents = []
        for msg in messages:
            contents.append({
                "role": msg["role"],
                "parts": [{"text": msg["content"]}],
            })
        
        payload = {"contents": contents}
        
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        return {"response": text, "model": model}
    
    def call_agent(self, messages: list[dict], **kwargs) -> dict:
        return self.chat(messages, **kwargs)


class BraveRouter:
    def __init__(self):
        self.api_key = config.BRAVE_API_KEY
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY not configured")
    
    def search(self, query: str, num_results: int = 10) -> list[dict]:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": num_results}
        
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            })
        
        return results


class BraveCounter:
    def __init__(self):
        self.count = 0
    
    def get_left(self) -> int:
        return 100 - self.count
    
    def decrement(self):
        self.count += 1
    
    def reset(self):
        self.count = 0


def get_llm_router(router_type: str = "ollama") -> LLMRouter | GeminiRouter:
    if router_type == "gemini":
        return GeminiRouter()
    return LLMRouter()