import logging
import os
import time
from typing import Any

import requests

import config

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self):
        self.base_url = config.OLLAMA_BASE_URL
        self.model = config.OLLAMA_MODEL
        self.ollama_client = None
        self._init_ollama()
    
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
        result = self.chat([{"role": "user", "content": prompt}], **kwargs)
        return result.get("response", "")


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