import logging
import os
import time
from typing import Any, Optional
from typing_extensions import Self

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config
from core.type_defs import MessageDict, LLMResponse, ToolCallDict
from core.circuit_breaker import get_circuit_breaker, CircuitBreakerError
from core.runtime_harness import get_harness, RuntimeHarness
from core.skill_programs import get_pf_registry, SkillProgramRegistry

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self) -> None:
        self.base_url: str = config.OLLAMA_BASE_URL
        self.model: str = config.OLLAMA_MODEL
        self.ollama_client: Any = None
        self.use_ollama: bool = self._check_ollama()
        self.gemini_keys: list[str] = config.GEMINI_KEYS or []
        self.current_key_index: int = 0
        self._ollama_cb = get_circuit_breaker("ollama", failure_threshold=5, recovery_timeout=30.0)
        self._gemini_cb = get_circuit_breaker("gemini", failure_threshold=3, recovery_timeout=60.0)
        self._init_ollama()
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            return requests.get(f"{self.base_url}/api/tags", timeout=3).status_code == 200
        except Exception:
            return False
    
    def rotate_gemini(self) -> None:
        """Rotate to next Gemini key."""
        if self.gemini_keys:
            self.current_key_index = (self.current_key_index + 1) % len(self.gemini_keys)
            logger.info("🔄 Rotando clave Gemini...")
    
    def _init_ollama(self) -> None:
        try:
            from ollama import Client
            self.ollama_client = Client(self.base_url)
            logger.info(f"Ollama client connected to {self.base_url}")
        except ImportError:
            logger.warning("ollama not installed, using HTTP fallback")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")
    
    def chat(
        self,
        messages: list[MessageDict],
        model: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
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
                result: LLMResponse = {
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
            logger.error(f"Chat error: {e}: {e}")
            raise
    
    def _http_chat(
        self,
        model: str,
        messages: list[MessageDict],
        tools: list[dict[str, Any]],
        start: float,
    ) -> LLMResponse:
        url = f"{self.base_url}/api/chat"
        payload: dict[str, Any] = {
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
    
    def _prepare_messages(self, messages: list[MessageDict]) -> list[MessageDict]:
        prepared: list[MessageDict] = []
        for msg in messages:
            if isinstance(msg, dict):
                prepared.append(msg)
            elif hasattr(msg, "role") and hasattr(msg, "content"):
                prepared.append({"role": msg.role, "content": msg.content})
        return prepared
    
    def call_agent(
        self,
        messages: list[MessageDict],
        tools: Optional[list[dict[str, Any]]] = None,
        use_harness: bool = False,
        session_id: Optional[str] = None,
    ) -> LLMResponse:
        if use_harness:
            return self.call_with_harness(messages, tools=tools, session_id=session_id)
        return self.chat(messages, tools=tools)

    def call_with_harness(
        self,
        messages: list[MessageDict],
        tools: Optional[list[dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> LLMResponse:
        """Call LLM with all 4 LIFE-HARNESS layers active."""
        harness = get_harness()
        pf_registry = get_pf_registry()
        sid = session_id or f"session_{time.time_ns()}"

        # Layer 1: Calibrate tool definitions
        calibrated_tools = harness.process_tools(tools or [])

        # Layer 2: Inject procedural skills
        task = messages[-1].get("content", "") if messages else ""
        state = {"last_error": "", "attempt_count": 0}
        enriched_messages = harness.inject_skills(task, state, list(messages))

        # Execute matching Program Functions
        pf_state = {
            "last_action.status": "",
            "task.complexity": "normal",
            "task.type": task[:50] if task else "",
            "error_count": 0,
            "attempt_count": 0,
        }
        pf_results = pf_registry.execute_matching(pf_state, None)
        for pf_result in pf_results:
            if pf_result.get("action") in ("retry", "validate"):
                enriched_messages.append({
                    "role": "system",
                    "content": f"[HASP INTERVENTION] {pf_result.get('message', '')}",
                })

        result = self.chat(enriched_messages, tools=calibrated_tools)

        tool_calls = result.get("tool_calls", [])
        for tc in tool_calls:
            harness.record_action(sid, dict(tc))

        interventions = harness.check_trajectory(sid)
        result["harness_interventions"] = interventions  # type: ignore[typeddict-unknown-key]

        harness.cleanup_session(sid)
        return result
    
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate with fallback: Ollama → Gemini with exponential backoff."""
        max_retries = 3
        delay = 2
        
        for attempt in range(max_retries):
            if self.use_ollama:
                try:
                    result = self._ollama_cb.call(
                        self.chat,
                        [{"role": "user", "content": prompt}],
                        **kwargs,
                    )
                    return result.get("response", "")
                except CircuitBreakerError as e:
                    logger.warning(f"⚠️ Ollama circuit breaker OPEN: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ Ollama retry {attempt+1}: {e}")
            
            if self.gemini_keys:
                try:
                    key = self.gemini_keys[self.current_key_index % len(self.gemini_keys)]
                    result = self._gemini_cb.call(self._gemini_chat, prompt, key)
                    return result.get("response", "")
                except CircuitBreakerError as e:
                    logger.warning(f"⚠️ Gemini circuit breaker OPEN: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ Gemini retry {attempt+1}: {e}")
                    self.rotate_gemini()
                    time.sleep(delay)
                    delay *= 2
        
        return "⚠️ Fallo crítico en el razonamiento."
    
    def _gemini_chat(self, prompt: str, key: str) -> LLMResponse:
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

    def call_with_turbo(
        self,
        messages: list[MessageDict],
        mode: str = "consultor",
        model: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Call LLM with TurboQuant optimizations for a chat mode.
        Auto-detects model and applies optimal settings.
        Uses mode-specific model if provided.
        Includes retry logic for robustness.
        """
        max_retries = 3
        last_error: Optional[str] = None
        
        for attempt in range(max_retries):
            try:
                from core.turboquant_engine import apply_chat_mode, get_engine

                engine = get_engine()
                apply_result = engine.apply_mode(mode, model=model)

                params = engine.get_optimized_params()

                options = params.get("options", {})
                options.update(kwargs)

                target_model = model or apply_result.get("model") or self.model

                result = self.chat(messages, model=target_model, tools=tools, **options)
                result["turbo"] = {
                    "mode": mode,
                    "model": target_model,
                    "context": params["context"],
                    "cache_k": params["turbo"]["cache_k"],
                    "cache_v": params["turbo"]["cache_v"],
                }

                logger.info(f"TQ Turbo success: mode={mode}, model={target_model}, attempt={attempt+1}")
                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(f"TQ attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
        
        logger.error(f"TQ all retries failed for mode {mode}. Last error: {last_error}")
        
        try:
            fallback_model = self.model
            result = self.chat(messages, model=fallback_model, tools=tools)
            result["turbo"] = {
                "mode": mode,
                "model": fallback_model,
                "fallback_used": True,
                "error": last_error
            }
            return result
        except Exception as final_error:
            logger.error(f"TQ fallback also failed: {final_error}")
            return {
                "response": "",
                "error": f"LLM failed after {max_retries} retries: {last_error}",
                "turbo": {"mode": mode, "model": "unknown", "failed": True}
            }

    def get_turbo_status(self) -> dict[str, Any]:
        """Get current TurboQuant status."""
        try:
            from core.turboquant_engine import get_turbo_status as tq_status
            return tq_status()
        except ImportError:
            return {"success": False, "error": "TurboQuant not available"}

    def apply_turbo_mode(self, mode: str) -> dict[str, Any]:
        """Apply a specific TurboQuant mode."""
        try:
            from core.turboquant_engine import apply_chat_mode
            return apply_chat_mode(mode)
        except ImportError:
            return {"success": False, "error": "TurboQuant not available"}


class GeminiRouter:
    def __init__(self) -> None:
        self.keys: list[str] = config.GEMINI_KEYS
        self.current_key: int = 0
    
    def chat(
        self,
        messages: list[MessageDict],
        model: str = "gemini-2.0-flash",
        **kwargs: Any,
    ) -> LLMResponse:
        if not self.keys:
            raise ValueError("No Gemini keys configured")
        
        key = self.keys[self.current_key % len(self.keys)]
        self.current_key += 1
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        
        contents: list[dict[str, Any]] = []
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
    
    def call_agent(
        self,
        messages: list[MessageDict],
        **kwargs: Any,
    ) -> LLMResponse:
        return self.chat(messages, **kwargs)


class BraveRouter:
    def __init__(self) -> None:
        self.api_key: str = config.BRAVE_API_KEY
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY not configured")
    
    def search(self, query: str, num_results: int = 10) -> list[dict[str, str]]:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": num_results}
        
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        results: list[dict[str, str]] = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            })
        
        return results


class BraveCounter:
    def __init__(self) -> None:
        self.count: int = 0
    
    def get_left(self) -> int:
        return 100 - self.count
    
    def decrement(self) -> None:
        self.count += 1
    
    def reset(self) -> None:
        self.count = 0


def get_llm_router(router_type: str = "ollama") -> LLMRouter | GeminiRouter:
    if router_type == "gemini":
        return GeminiRouter()
    return LLMRouter()