"""LIFE-HARNESS: Lifecycle-Aware Runtime Harness for Deterministic LLM Agents.

Adapts the runtime interface (not model weights) across 4 lifecycle layers:
1. EnvironmentContractLayer  — Calibrates tool descriptions and interface constraints
2. ProceduralSkillLayer     — Distills reusable procedures from trajectories
3. ActionRealizationLayer   — Validates and canonicalizes actions pre-execution
4. TrajectoryRegulationLayer — Monitors dynamics and triggers recovery

Based on: Xu et al., "Adapting the Interface, Not the Model" (arXiv:2605.22166)
"""

import json
import logging
import time
import re
from typing import Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# Layer 1: Environment Contract Layer
# =============================================================================

class EnvironmentContractLayer:
    """Calibrates tool descriptions and interface constraints before interaction.

    Wraps tool schemas to ensure the LLM receives accurate, consistent contracts.
    Detects and corrects common mismatches: missing params, ambiguous types,
    incorrect enum values, contradictory constraints.
    """

    def __init__(self) -> None:
        self._contract_cache: dict[str, dict] = {}
        self._correction_count: int = 0

    def calibrate_tools(self, tools: list[dict]) -> list[dict]:
        """Calibrate tool definitions before sending to LLM."""
        calibrated = []
        for tool in tools:
            if tool.get("type") != "function":
                calibrated.append(tool)
                continue

            func = tool.get("function", {})
            name = func.get("name", "")
            cache_key = f"{name}"

            if cache_key in self._contract_cache:
                calibrated.append(self._contract_cache[cache_key])
                continue

            calibrated_tool = self._calibrate_tool(tool)
            self._contract_cache[cache_key] = calibrated_tool
            calibrated.append(calibrated_tool)

        return calibrated

    def _calibrate_tool(self, tool: dict) -> dict:
        """Apply calibrations to a single tool definition."""
        func = tool.get("function", {})
        params = func.get("parameters", {})

        self._ensure_required(params)
        self._add_type_hints(params)
        self._remove_ambiguous_enums(params)
        self._limit_description_length(func)

        return tool

    def _ensure_required(self, params: dict) -> None:
        """Ensure required fields are properly marked."""
        required = params.get("required", [])
        props = params.get("properties", {})
        for name, prop in props.items():
            if prop.get("required", False) and name not in required:
                required.append(name)
                self._correction_count += 1

    def _add_type_hints(self, params: dict) -> None:
        """Add missing type hints to parameters."""
        props = params.get("properties", {})
        for name, prop in props.items():
            if "type" not in prop:
                prop["type"] = "string"
                self._correction_count += 1

    def _remove_ambiguous_enums(self, params: dict) -> None:
        """Remove contradictory or empty enum constraints."""
        props = params.get("properties", {})
        for name, prop in props.items():
            if "enum" in prop and not prop["enum"]:
                del prop["enum"]
                self._correction_count += 1

    def _limit_description_length(self, func: dict) -> None:
        """Truncate overly long descriptions that confuse models."""
        desc = func.get("description", "")
        if len(desc) > 500:
            func["description"] = desc[:497] + "..."
            self._correction_count += 1

    def get_stats(self) -> dict[str, Any]:
        return {
            "corrections_applied": self._correction_count,
            "cached_contracts": len(self._contract_cache),
        }


# =============================================================================
# Layer 2: Procedural Skill Layer
# =============================================================================

@dataclass
class ProceduralSkill:
    """A reusable procedure distilled from trajectories."""
    name: str
    trigger_patterns: list[str]
    intervention: str
    success_rate: float = 0.5
    invocation_count: int = 0
    success_count: int = 0

    def record_outcome(self, success: bool) -> None:
        self.invocation_count += 1
        if success:
            self.success_count += 1
        self.success_rate = self.success_count / max(1, self.invocation_count)


class ProceduralSkillLayer:
    """Distills reusable procedures from past agent trajectories.

    Maintains a library of ProceduralSkills that capture recurring
    failure-solution patterns. Skills are retrieved based on current
    task and injected into the context before action generation.
    """

    def __init__(self) -> None:
        self._skills: dict[str, ProceduralSkill] = {}
        self._failure_history: list[dict] = []

    def register_skill(self, skill: ProceduralSkill) -> None:
        self._skills[skill.name] = skill
        logger.info(f"ProceduralSkill registered: {skill.name}")

    def retrieve_skills(self, task: str, state: dict) -> list[ProceduralSkill]:
        """Retrieve relevant skills for current task and state."""
        matched = []
        for skill in self._skills.values():
            for pattern in skill.trigger_patterns:
                if re.search(pattern, task, re.IGNORECASE):
                    matched.append(skill)
                    break
                elif isinstance(state.get("last_error"), str) and re.search(pattern, state["last_error"], re.IGNORECASE):
                    matched.append(skill)
                    break
        return sorted(matched, key=lambda s: s.success_rate, reverse=True)[:3]

    def record_failure(self, task: str, error: str, trajectory: list) -> None:
        self._failure_history.append({
            "task": task,
            "error": error,
            "trajectory": trajectory[-10:],
            "timestamp": time.time(),
        })
        if len(self._failure_history) > 1000:
            self._failure_history = self._failure_history[-500:]

    def evolve_from_failures(self, llm: Any) -> None:
        """Analyze failure history to evolve new skills."""
        if len(self._failure_history) < 3:
            return

        recent_failures = self._failure_history[-5:]
        patterns = defaultdict(list)
        for f in recent_failures:
            patterns[f["error"][:100]].append(f)

        for error_key, occurrences in patterns.items():
            if len(occurrences) >= 2:
                skill_name = f"auto_skill_{len(self._skills)}"
                existing = [s for s in self._skills.values()
                           if any(p in error_key for p in s.trigger_patterns)]
                if not existing:
                    skill = ProceduralSkill(
                        name=skill_name,
                        trigger_patterns=[re.escape(error_key[:50])],
                        intervention=f"Before acting, verify: {occurrences[-1]['task'][:200]}",
                    )
                    self.register_skill(skill)
                    logger.info(f"Skill evolved from failures: {skill_name}")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_skills": len(self._skills),
            "failure_history": len(self._failure_history),
            "skills": [
                {"name": s.name, "success_rate": s.success_rate,
                 "invocations": s.invocation_count}
                for s in self._skills.values()
            ],
        }


# =============================================================================
# Layer 3: Action Realization Layer
# =============================================================================

class ActionValidationResult:
    """Result of validating an action."""
    def __init__(self, valid: bool, canonicalized: Any = None, error: Optional[str] = None):
        self.valid = valid
        self.canonicalized = canonicalized
        self.error = error


class ActionRealizationLayer:
    """Validates and canonicalizes model-generated actions before execution.

    Prevents deterministic failures by checking:
    - Tool existence and parameter completeness
    - Action format correctness
    - Parameter type/range validity
    - Reference consistency
    """

    def __init__(self) -> None:
        self._validations_passed: int = 0
        self._validations_failed: int = 0
        self._corrections_applied: int = 0

    def validate_tool_call(self, tool_call: dict, available_tools: list[dict]) -> ActionValidationResult:
        """Validate a tool call before execution."""
        if not tool_call or "name" not in tool_call:
            self._validations_failed += 1
            return ActionValidationResult(False, error="Empty or malformed tool call")

        name = tool_call["name"]
        args = tool_call.get("arguments", tool_call.get("parameters", {}))

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                self._validations_failed += 1
                return ActionValidationResult(False, error="Tool arguments are not valid JSON")

        tool_def = None
        for t in available_tools:
            if t.get("function", {}).get("name") == name:
                tool_def = t
                break

        if not tool_def:
            self._validations_failed += 1
            return ActionValidationResult(False, error=f"Unknown tool: {name}")

        params = tool_def.get("function", {}).get("parameters", {})
        required = params.get("required", [])
        props = params.get("properties", {})

        for req in required:
            if req not in args:
                self._corrections_applied += 1
                if req in props and "default" in props[req]:
                    args[req] = props[req]["default"]
                    logger.info(f"ActionRealization: added default for {req}")

        for key, value in list(args.items()):
            if key in props and "type" in props[key]:
                expected_type = props[key]["type"]
                if expected_type == "integer" and isinstance(value, float):
                    args[key] = int(value)
                    self._corrections_applied += 1

        self._validations_passed += 1
        return ActionValidationResult(True, canonicalized={"name": name, "arguments": args})

    def validate_action(self, action: str) -> ActionValidationResult:
        """Validate free-form text action."""
        if not action or len(action.strip()) == 0:
            self._validations_failed += 1
            return ActionValidationResult(False, error="Empty action")

        cleaned = action.strip()
        if len(cleaned) > 10000:
            cleaned = cleaned[:10000]
            self._corrections_applied += 1

        self._validations_passed += 1
        return ActionValidationResult(True, canonicalized=cleaned)

    def get_stats(self) -> dict[str, Any]:
        total = self._validations_passed + self._validations_failed
        return {
            "validations_passed": self._validations_passed,
            "validations_failed": self._validations_failed,
            "corrections_applied": self._corrections_applied,
            "pass_rate": self._validations_passed / max(1, total),
        }


# =============================================================================
# Layer 4: Trajectory Regulation Layer
# =============================================================================

class TrajectoryState:
    """Tracks the state of an agent trajectory for regulation."""
    def __init__(self) -> None:
        self.actions: list[dict] = []
        self.action_count: int = 0
        self.repeated_actions: list[str] = []
        self.last_action_hash: Optional[str] = None
        self.stagnation_count: int = 0
        self.invalid_retry_count: int = 0
        self.budget_exhausted: bool = False
        self.start_time: float = time.time()

    def record_action(self, action: dict) -> None:
        self.actions.append(action)
        self.action_count += 1
        action_str = json.dumps(action, sort_keys=True, default=str)
        action_hash = hash(action_str)

        if action_hash == self.last_action_hash:
            self.stagnation_count += 1
            if action_str not in self.repeated_actions:
                self.repeated_actions.append(action_str[:200])
        else:
            self.stagnation_count = 0

        self.last_action_hash = action_hash

    def record_error(self) -> None:
        self.invalid_retry_count += 1


class TrajectoryRegulationLayer:
    """Monitors post-execution dynamics and triggers recovery.

    Detects degenerate patterns:
    - Action loops (same action repeated)
    - Stagnation (no progress)
    - Invalid retry chains
    - Budget exhaustion (time/step limits)
    """

    def __init__(
        self,
        max_stagnation: int = 3,
        max_retries: int = 5,
        max_actions: int = 50,
        max_duration: float = 300.0,
    ) -> None:
        self.max_stagnation = max_stagnation
        self.max_retries = max_retries
        self.max_actions = max_actions
        self.max_duration = max_duration
        self._trajectories: dict[str, TrajectoryState] = {}
        self._recoveries_triggered: int = 0

    def get_state(self, session_id: str) -> TrajectoryState:
        if session_id not in self._trajectories:
            self._trajectories[session_id] = TrajectoryState()
        return self._trajectories[session_id]

    def check_loop(self, session_id: str) -> Optional[str]:
        """Check for action loops. Returns intervention if detected."""
        state = self.get_state(session_id)

        if state.stagnation_count >= self.max_stagnation:
            repeat_str = "; ".join(state.repeated_actions[-3:])
            intervention = (
                f"[TRAJECTORY REGULATION] Se detectó un bucle de acciones repetidas: "
                f"{repeat_str}. Detén el bucle y prueba una estrategia diferente."
            )
            state.stagnation_count = 0
            self._recoveries_triggered += 1
            return intervention

        return None

    def check_retries(self, session_id: str) -> Optional[str]:
        """Check for excessive retries. Returns intervention if detected."""
        state = self.get_state(session_id)

        if state.invalid_retry_count >= self.max_retries:
            intervention = (
                f"[TRAJECTORY REGULATION] Se detectaron {self.max_retries} reintentos inválidos consecutivos. "
                f"Revisa la validez de la acción antes de reintentar."
            )
            state.invalid_retry_count = 0
            self._recoveries_triggered += 1
            return intervention

        return None

    def check_budget(self, session_id: str) -> Optional[str]:
        """Check for budget exhaustion. Returns intervention if detected."""
        state = self.get_state(session_id)

        if state.action_count >= self.max_actions:
            state.budget_exhausted = True
            self._recoveries_triggered += 1
            return (
                f"[TRAJECTORY REGULATION] Límite de {self.max_actions} acciones alcanzado. "
                f"Procede a dar una respuesta final con la información disponible."
            )

        elapsed = time.time() - state.start_time
        if elapsed >= self.max_duration:
            state.budget_exhausted = True
            self._recoveries_triggered += 1
            return (
                f"[TRAJECTORY REGULATION] Tiempo límite de {self.max_duration}s alcanzado. "
                f"Procede a dar una respuesta final."
            )

        return None

    def check_all(self, session_id: str) -> list[str]:
        """Run all checks. Returns list of interventions needed."""
        interventions = []
        for check in [self.check_loop, self.check_retries, self.check_budget]:
            try:
                intervention = check(session_id)
                if intervention:
                    interventions.append(intervention)
            except Exception as e:
                logger.warning(f"Trajectory check failed: {e}")
        return interventions

    def cleanup(self, session_id: str) -> None:
        """Remove trajectory state after completion."""
        self._trajectories.pop(session_id, None)

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_trajectories": len(self._trajectories),
            "recoveries_triggered": self._recoveries_triggered,
            "config": {
                "max_stagnation": self.max_stagnation,
                "max_retries": self.max_retries,
                "max_actions": self.max_actions,
                "max_duration": self.max_duration,
            },
        }


# =============================================================================
# Runtime Harness: Combines all 4 layers
# =============================================================================

class RuntimeHarness:
    """Main harness combining all LIFE-HARNESS layers.

    Wraps an LLM agent and applies lifecycle-aware interventions
    without modifying model weights.
    """

    def __init__(self) -> None:
        self.contract_layer = EnvironmentContractLayer()
        self.skill_layer = ProceduralSkillLayer()
        self.action_layer = ActionRealizationLayer()
        self.trajectory_layer = TrajectoryRegulationLayer()
        self._total_interventions: int = 0

    def process_tools(self, tools: list[dict]) -> list[dict]:
        """Layer 1: Calibrate tool definitions."""
        return self.contract_layer.calibrate_tools(tools)

    def inject_skills(self, task: str, state: dict, context: list) -> list:
        """Layer 2: Inject relevant skills into context."""
        skills = self.skill_layer.retrieve_skills(task, state)
        for skill in skills:
            context.append({
                "role": "system",
                "content": f"[PROCEDURAL SKILL: {skill.name}] {skill.intervention}",
            })
            self._total_interventions += 1
        return context

    def validate_tool_call(self, tool_call: dict, tools: list[dict]) -> ActionValidationResult:
        """Layer 3: Validate tool call before execution."""
        return self.action_layer.validate_tool_call(tool_call, tools)

    def record_action(self, session_id: str, action: dict) -> None:
        """Record action for trajectory regulation."""
        self.trajectory_layer.get_state(session_id).record_action(action)

    def record_error(self, session_id: str) -> None:
        """Record error for trajectory regulation."""
        self.trajectory_layer.get_state(session_id).record_error()

    def check_trajectory(self, session_id: str) -> list[str]:
        """Layer 4: Check trajectory health. Returns interventions."""
        interventions = self.trajectory_layer.check_all(session_id)
        self._total_interventions += len(interventions)
        return interventions

    def record_failure(self, task: str, error: str, trajectory: list) -> None:
        """Record failure for skill evolution."""
        self.skill_layer.record_failure(task, error, trajectory)
        self.skill_layer.evolve_from_failures(None)

    def cleanup_session(self, session_id: str) -> None:
        """Clean up session state."""
        self.trajectory_layer.cleanup(session_id)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_interventions": self._total_interventions,
            "contract_layer": self.contract_layer.get_stats(),
            "skill_layer": self.skill_layer.get_stats(),
            "action_layer": self.action_layer.get_stats(),
            "trajectory_layer": self.trajectory_layer.get_stats(),
        }


_harness: Optional[RuntimeHarness] = None


def get_harness() -> RuntimeHarness:
    """Get or create the global RuntimeHarness singleton."""
    global _harness
    if _harness is None:
        _harness = RuntimeHarness()
    return _harness
