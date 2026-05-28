"""HASP: Harness-Aware Skill Programs for LLM Agents.

Upgrades passive textual advice into executable Program Functions (PFs)
that activate on failure-prone states and execute deterministic logic.

Based on: arXiv:2605.22306 — HASP: Harness-Aware Skill Programs
for LLM Agents via Multi-Step Interventions.

Key concepts:
- ProgramFunction (PF): executable skill triggered by precondition
- Precondition: (state_condition, context_condition) pair
- Intervention: deterministic action block (retry, fallback, decompose, etc.)
- Auto-evolution: failures trigger PF creation/modification via H-Mem
"""

import json
import logging
import re
import time
from typing import Any, Optional, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Type aliases
StateDict = dict[str, Any]
InterventionResult = dict[str, Any]


# =============================================================================
# Program Function Base
# =============================================================================

class ProgramFunction(ABC):
    """Base class for a Harness-Aware Skill Program.

    Each PF has:
    - name: unique identifier
    - description: when should this PF activate
    - preconditions: list of (field, pattern) pairs checked against state
    - priority: execution priority (higher = runs first)
    """

    def __init__(
        self,
        name: str,
        description: str,
        preconditions: list[tuple[str, str]],
        priority: int = 0,
    ) -> None:
        self.name = name
        self.description = description
        self.preconditions = preconditions
        self.priority = priority
        self.invocation_count: int = 0
        self.success_count: int = 0

    @abstractmethod
    def execute(self, state: StateDict, context: Any) -> InterventionResult:
        """Execute the program function's intervention."""
        ...

    def matches(self, state: StateDict) -> bool:
        """Check if preconditions are satisfied by current state."""
        for field, pattern in self.preconditions:
            value = self._get_nested(state, field)
            if value is None:
                return False
            if not re.search(pattern, str(value), re.IGNORECASE):
                return False
        return True

    def _get_nested(self, d: dict[str, Any], path: str) -> Any:
        parts = path.split(".")
        current: Any = d
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def record_outcome(self, success: bool) -> None:
        self.invocation_count += 1
        if success:
            self.success_count += 1


# =============================================================================
# Built-in Program Functions
# =============================================================================

class RetryPF(ProgramFunction):
    """PF: Retry with modified parameters on failure."""

    def __init__(self) -> None:
        super().__init__(
            name="retry_on_failure",
            description="Reintenta con parámetros modificados tras un error",
            preconditions=[
                ("last_action.status", "error|failure|failed"),
                ("attempt_count", r"\d+"),
            ],
            priority=10,
        )

    def execute(self, state: StateDict, context: Any) -> InterventionResult:
        attempt = state.get("attempt_count", 0)
        max_attempt = state.get("max_attempts", 3)
        if attempt >= max_attempt:
            action = "escalate"
        else:
            action = "retry"
        return {
            "action": action,
            "message": f"Intento {attempt}/{max_attempt}: reintentando con ajustes",
            "modifications": {"temperature": 0.1 + attempt * 0.1},
        }


class DecomposePF(ProgramFunction):
    """PF: Decompose complex task into subtasks."""

    def __init__(self) -> None:
        super().__init__(
            name="decompose_complex_task",
            description="Descompone tareas complejas en subtareas manejables",
            preconditions=[
                ("task.complexity", "high|complex|difficult"),
                ("task.type", "research|analysis|report|investigación"),
            ],
            priority=20,
        )

    def execute(self, state: StateDict, context: Any) -> InterventionResult:
        return {
            "action": "decompose",
            "message": "Descomponiendo tarea compleja en subtareas secuenciales",
            "subtasks": [
                "1) Buscar información general",
                "2) Analizar fuentes clave",
                "3) Sintetizar hallazgos",
                "4) Generar respuesta estructurada",
            ],
        }


class FallbackPF(ProgramFunction):
    """PF: Fallback to simpler model on resource exhaustion."""

    def __init__(self) -> None:
        super().__init__(
            name="fallback_on_exhaustion",
            description="Cambia a modelo más simple cuando falla el principal",
            preconditions=[
                ("last_action.status", "timeout|exhausted|error|rate_limit"),
            ],
            priority=30,
        )

    def execute(self, state: StateDict, context: Any) -> InterventionResult:
        return {
            "action": "fallback",
            "message": "Modelo principal no disponible, usando fallback",
            "modifications": {"model": "ollama", "temperature": 0.5},
        }


class ValidateBeforeActPF(ProgramFunction):
    """PF: Validate action before executing (for repetitive errors)."""

    def __init__(self) -> None:
        super().__init__(
            name="validate_before_act",
            description="Valida la acción antes de ejecutarla",
            preconditions=[
                ("last_action.status", "error|failure"),
                ("error_count", r"[3-9]|\d{2,}"),
            ],
            priority=5,
        )

    def execute(self, state: StateDict, context: Any) -> InterventionResult:
        return {
            "action": "validate",
            "message": "Múltiples errores detectados: validando próxima acción antes de ejecutar",
            "validate_fields": ["tool_name", "arguments", "format"],
        }


# =============================================================================
# Skill Program Registry
# =============================================================================

class SkillProgramRegistry:
    """Registry of Program Functions that the harness can query."""

    def __init__(self) -> None:
        self._pfs: dict[str, ProgramFunction] = {}
        self._auto_evolved: int = 0

    def register(self, pf: ProgramFunction) -> None:
        self._pfs[pf.name] = pf
        logger.info(f"PF registered: {pf.name}")

    def register_builtins(self) -> None:
        """Register all built-in Program Functions."""
        for pf_cls in [
            RetryPF,
            DecomposePF,
            FallbackPF,
            ValidateBeforeActPF,
        ]:
            pf: ProgramFunction = pf_cls()  # type: ignore[abstract]
            if pf.name not in self._pfs:
                self.register(pf)

    def find_matching(self, state: StateDict) -> list[ProgramFunction]:
        """Find all PFs whose preconditions match the current state."""
        matched = []
        for pf in self._pfs.values():
            try:
                if pf.matches(state):
                    matched.append(pf)
            except Exception as e:
                logger.warning(f"PF match error for {pf.name}: {e}")
        return sorted(matched, key=lambda p: p.priority, reverse=True)

    def execute_matching(self, state: StateDict, context: Any) -> list[InterventionResult]:
        """Execute all matching PFs and return their interventions."""
        matched = self.find_matching(state)
        results = []
        for pf in matched:
            try:
                result = pf.execute(state, context)
                results.append(result)
                pf.record_outcome(result.get("status") != "error")
            except Exception as e:
                logger.error(f"PF execution error for {pf.name}: {e}")
                pf.record_outcome(False)
                results.append({"action": "error", "message": str(e)})
        return results

    def evolve_from_failures(self, failure_patterns: list[dict[str, Any]]) -> None:
        """Auto-evolve new PFs from recurring failure patterns."""
        for pattern in failure_patterns:
            pf_name = f"auto_pf_{int(time.time())}"
            if pf_name in self._pfs:
                continue
            trigger = pattern.get("trigger", "")
            field = pattern.get("field", "last_action.status")
            intervention_type = pattern.get("intervention", "retry")

            pf: ProgramFunction
            if intervention_type == "decompose":
                pf = DecomposePF()
            elif intervention_type == "fallback":
                pf = FallbackPF()
            else:
                pf = RetryPF()

            pf.name = pf_name
            pf.preconditions = [(field, re.escape(trigger[:50]))]
            self.register(pf)
            self._auto_evolved += 1
            logger.info(f"PF auto-evolved: {pf_name}")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_pfs": len(self._pfs),
            "auto_evolved": self._auto_evolved,
            "pfs": [
                {"name": pf.name, "invocations": pf.invocation_count,
                 "success_count": pf.success_count, "priority": pf.priority}
                for pf in self._pfs.values()
            ],
        }

    def list_pfs(self) -> list[dict[str, Any]]:
        """List all registered Program Functions with details."""
        result = []
        for pf in self._pfs.values():
            result.append({
                "name": pf.name,
                "description": pf.description,
                "preconditions": pf.preconditions,
                "priority": pf.priority,
                "invocations": pf.invocation_count,
                "success_count": pf.success_count,
            })
        return result

    def execute_pf(self, name: str, state: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Execute a specific Program Function by name."""
        pf = self._pfs.get(name)
        if pf is None:
            return None
        if not pf.matches(state):
            return None
        try:
            result = pf.execute(state, None)
            pf.record_outcome(result.get("status") != "error")
            return result
        except Exception as e:
            logger.error(f"PF execution error for {name}: {e}")
            pf.record_outcome(False)
            return {"error": str(e)}


_registry: Optional[SkillProgramRegistry] = None


def get_pf_registry() -> SkillProgramRegistry:
    """Get or create the global SkillProgramRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = SkillProgramRegistry()
        _registry.register_builtins()
    return _registry
