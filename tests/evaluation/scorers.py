"""Scoring logic for evaluation scenarios."""

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ScoreResult:
    """Result of scoring a single task."""
    task_id: int
    task_name: str
    level: int
    passed: bool
    functionality_score: float = 0.0
    content_score: float = 0.0
    state_score: float = 0.0
    performance_score: float = 0.0
    total_score: float = 0.0
    error: Optional[str] = None
    response_text: str = ""
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def grade(self) -> str:
        if self.total_score >= 90:
            return "A"
        elif self.total_score >= 75:
            return "B"
        elif self.total_score >= 60:
            return "C"
        elif self.total_score >= 40:
            return "D"
        else:
            return "F"


def score_functionality(response_text: Optional[str], error: Optional[str]) -> float:
    """Score 0-100: did the command execute without error?"""
    if error:
        return 0.0
    if response_text and len(response_text.strip()) > 0:
        return 100.0
    return 0.0


def score_content(
    response_text: str,
    expected_keywords: Optional[list[str]] = None,
    min_length: int = 20,
) -> float:
    """Score 0-100: is the response relevant and complete?"""
    if not response_text:
        return 0.0

    text_lower = response_text.lower()

    length_score = min(100.0, (len(response_text) / max(min_length, 1)) * 100)

    if not expected_keywords:
        return length_score

    matched = sum(1 for kw in expected_keywords if kw.lower() in text_lower)
    keyword_score = (matched / len(expected_keywords)) * 100 if expected_keywords else 100

    return (length_score * 0.3) + (keyword_score * 0.7)


def score_state(state_checks: dict[str, bool]) -> float:
    """Score 0-100: is the system in the correct state after execution?"""
    if not state_checks:
        return 100.0

    passed = sum(1 for v in state_checks.values() if v)
    return (passed / len(state_checks)) * 100


def score_performance(duration_seconds: float, max_allowed: float = 30.0) -> float:
    """Score 0-100: was the response fast enough?"""
    if duration_seconds <= max_allowed * 0.5:
        return 100.0
    elif duration_seconds <= max_allowed:
        return 75.0
    elif duration_seconds <= max_allowed * 2:
        return 50.0
    elif duration_seconds <= max_allowed * 4:
        return 25.0
    else:
        return 0.0


def score_fidelity(response: str, ground_truth_text: str) -> float:
    """Score 0-100: factual accuracy against source.
    
    Args:
        response: Respuesta del agente
        ground_truth_text: Texto completo del paper/documento fuente
    
    Returns:
        Score de fidelidad (0-100)
    """
    from tests.evaluation.fidelity_checker import FidelityChecker
    
    checker = FidelityChecker(ground_truth_text)
    report = checker.check_response("", response)
    return report.score


def calculate_total(
    functionality: float,
    content: float,
    state: float,
    performance: float,
    fidelity: float = 100.0,
) -> float:
    """Calculate weighted total score.
    
    Args:
        functionality: Score de funcionalidad (0-100)
        content: Score de contenido (0-100)
        state: Score de estado (0-100)
        performance: Score de performance (0-100)
        fidelity: Score de fidelidad factual (0-100, default 100 para no penalizar si no se mide)
    
    Returns:
        Score total ponderado (0-100)
    """
    return (
        functionality * 0.30
        + content * 0.20
        + state * 0.15
        + performance * 0.10
        + fidelity * 0.25
    )


def score_task(
    response_text: str,
    error: Optional[str],
    duration_seconds: float,
    expected_keywords: Optional[list[str]] = None,
    state_checks: Optional[dict[str, bool]] = None,
    max_time: float = 30.0,
    min_length: int = 20,
) -> ScoreResult:
    """Score a complete task execution."""
    func = score_functionality(response_text, error)
    content = score_content(response_text, expected_keywords, min_length)
    state = score_state(state_checks or {})
    perf = score_performance(duration_seconds, max_time)
    total = calculate_total(func, content, state, perf)

    return ScoreResult(
        task_id=0,
        task_name="",
        level=1,
        passed=total >= 50 and func > 0,
        functionality_score=func,
        content_score=content,
        state_score=state,
        performance_score=perf,
        total_score=round(total, 1),
        error=error,
        response_text=response_text[:500] if response_text else "",
        duration_seconds=round(duration_seconds, 2),
    )


@dataclass
class EvaluationReport:
    """Aggregated evaluation report."""
    date: str
    total_tasks: int = 0
    passed_tasks: int = 0
    total_score: float = 0.0
    total_duration: float = 0.0
    brave_calls: int = 0
    results: list[ScoreResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return (self.passed_tasks / max(1, self.total_tasks)) * 100

    @property
    def avg_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.total_score for r in self.results) / len(self.results)

    def by_level(self) -> dict[int, dict]:
        levels = {}
        for r in self.results:
            if r.level not in levels:
                levels[r.level] = {"total": 0, "passed": 0, "scores": []}
            levels[r.level]["total"] += 1
            levels[r.level]["scores"].append(r.total_score)
            if r.passed:
                levels[r.level]["passed"] += 1

        for level_data in levels.values():
            scores = level_data["scores"]
            level_data["avg_score"] = round(sum(scores) / max(1, len(scores)), 1)
            level_data["pass_rate"] = round(
                (level_data["passed"] / max(1, level_data["total"])) * 100, 1
            )
            del level_data["scores"]

        return levels
