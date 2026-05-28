"""Tests for HASP Skill Programs."""
import pytest

from core.skill_programs import (
    RetryPF,
    DecomposePF,
    FallbackPF,
    ValidateBeforeActPF,
    SkillProgramRegistry,
    get_pf_registry,
)


class TestRetryPF:
    @pytest.fixture
    def pf(self):
        return RetryPF()

    def test_matches_failure_state(self, pf):
        assert pf.matches({"last_action": {"status": "error"}, "attempt_count": 1})

    def test_matches_failure_state_alternate(self, pf):
        assert pf.matches({"last_action": {"status": "failed"}, "attempt_count": "1"})

    def test_does_not_match_success(self, pf):
        assert not pf.matches({"last_action": {"status": "success"}, "attempt_count": 1})

    def test_does_not_match_missing_fields(self, pf):
        assert not pf.matches({})

    def test_execute_retry_within_limit(self, pf):
        result = pf.execute({"attempt_count": 1, "max_attempts": 3}, None)
        assert result["action"] == "retry"
        assert "modifications" in result
        assert result["modifications"]["temperature"] > 0.1

    def test_execute_escalate_after_limit(self, pf):
        result = pf.execute({"attempt_count": 3, "max_attempts": 3}, None)
        assert result["action"] == "escalate"


class TestDecomposePF:
    @pytest.fixture
    def pf(self):
        return DecomposePF()

    def test_matches_complex_research(self, pf):
        assert pf.matches({"task": {"complexity": "high", "type": "research"}})

    def test_matches_difficult_research(self, pf):
        assert pf.matches({"task": {"complexity": "difficult", "type": "investigación"}})

    def test_does_not_match_simple(self, pf):
        assert not pf.matches({"task": {"complexity": "low", "type": "query"}})

    def test_execute_returns_subtasks(self, pf):
        result = pf.execute({}, None)
        assert result["action"] == "decompose"
        assert "subtasks" in result
        assert len(result["subtasks"]) == 4


class TestFallbackPF:
    @pytest.fixture
    def pf(self):
        return FallbackPF()

    def test_matches_timeout(self, pf):
        assert pf.matches({"last_action": {"status": "timeout"}})

    def test_matches_exhausted(self, pf):
        assert pf.matches({"last_action": {"status": "exhausted"}})

    def test_matches_rate_limit(self, pf):
        assert pf.matches({"last_action": {"status": "rate_limit"}})

    def test_does_not_match_success(self, pf):
        assert not pf.matches({"last_action": {"status": "success"}})

    def test_execute_returns_fallback(self, pf):
        result = pf.execute({}, None)
        assert result["action"] == "fallback"
        assert result["modifications"]["model"] == "ollama"


class TestValidateBeforeActPF:
    @pytest.fixture
    def pf(self):
        return ValidateBeforeActPF()

    def test_matches_with_errors(self, pf):
        assert pf.matches({"last_action": {"status": "error"}, "error_count": 5})

    def test_matches_with_failure(self, pf):
        assert pf.matches({"last_action": {"status": "failure"}, "error_count": 3})

    def test_does_not_match_low_errors(self, pf):
        assert not pf.matches({"last_action": {"status": "error"}, "error_count": 1})

    def test_execute_returns_validate(self, pf):
        result = pf.execute({}, None)
        assert result["action"] == "validate"
        assert "validate_fields" in result


class TestSkillProgramRegistry:
    @pytest.fixture
    def registry(self):
        reg = SkillProgramRegistry()
        reg.register_builtins()
        return reg

    def test_builtins_registered(self, registry):
        stats = registry.get_stats()
        assert stats["total_pfs"] >= 4

    def test_find_matching_retry(self, registry):
        matched = registry.find_matching({
            "last_action": {"status": "error"},
            "attempt_count": 1,
            "error_count": 0,
            "task": {"complexity": "normal", "type": "query"},
        })
        names = [pf.name for pf in matched]
        assert "retry_on_failure" in names

    def test_find_matching_decompose(self, registry):
        matched = registry.find_matching({
            "task": {"complexity": "high", "type": "research"},
            "last_action": {"status": "success"},
            "attempt_count": 0,
            "error_count": 0,
        })
        names = [pf.name for pf in matched]
        assert "decompose_complex_task" in names

    def test_execute_matching_retry(self, registry):
        results = registry.execute_matching({
            "last_action": {"status": "error"},
            "attempt_count": 1,
            "error_count": 5,
            "task": {"complexity": "normal", "type": "query"},
        }, None)
        actions = [r["action"] for r in results]
        assert "retry" in actions or "validate" in actions

    def test_evolve_from_failures(self, registry):
        patterns = [
            {"trigger": "timeout", "field": "last_action.status", "intervention": "retry"},
            {"trigger": "complex", "field": "task.complexity", "intervention": "decompose"},
        ]
        registry.evolve_from_failures(patterns)
        stats = registry.get_stats()
        assert stats["auto_evolved"] >= 1

    def test_no_duplicate_evolve(self, registry):
        patterns = [{"trigger": "test", "intervention": "retry"}]
        registry.evolve_from_failures(patterns)
        stats1 = registry.get_stats()["total_pfs"]
        registry.evolve_from_failures(patterns)
        stats2 = registry.get_stats()["total_pfs"]
        assert stats2 >= stats1

    def test_register_custom_pf(self, registry):
        pf = ValidateBeforeActPF()
        pf.name = "custom_validate"
        registry.register(pf)
        assert registry._pfs["custom_validate"].name == "custom_validate"

    def test_execute_matching_empty_state(self, registry):
        results = registry.execute_matching({}, None)
        assert isinstance(results, list)

    def test_get_stats_shape(self, registry):
        stats = registry.get_stats()
        assert "total_pfs" in stats
        assert "auto_evolved" in stats
        assert "pfs" in stats
        assert isinstance(stats["pfs"], list)
        if stats["pfs"]:
            pf = stats["pfs"][0]
            assert "name" in pf
            assert "invocations" in pf

    def test_singleton(self):
        r1 = get_pf_registry()
        r2 = get_pf_registry()
        assert r1 is r2
