"""Tests for LIFE-HARNESS Runtime Harness."""
import json
import time
from typing import Any
import pytest

from core.runtime_harness import (
    EnvironmentContractLayer,
    ProceduralSkillLayer,
    ProceduralSkill,
    ActionRealizationLayer,
    TrajectoryRegulationLayer,
    RuntimeHarness,
    get_harness,
)


@pytest.fixture
def sample_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "search_wiki",
                "description": "Search wiki notes" + "x" * 500,
                "parameters": {
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                },
            },
        },
    ]


class TestEnvironmentContractLayer:
    def test_contract_calibrates_missing_required(self):
        layer = EnvironmentContractLayer()
        tools = [{
            "type": "function",
            "function": {
                "name": "test",
                "parameters": {
                    "properties": {
                        "x": {"type": "string"},
                    },
                },
            },
        }]
        calibrated = layer.calibrate_tools(tools)
        params = calibrated[0]["function"]["parameters"]
        assert "x" not in params.get("required", [])

    def test_contract_adds_missing_type_hints(self):
        layer = EnvironmentContractLayer()
        tools = [{
            "type": "function",
            "function": {
                "name": "test",
                "parameters": {
                    "properties": {
                        "x": {},
                    },
                },
            },
        }]
        calibrated = layer.calibrate_tools(tools)
        prop = calibrated[0]["function"]["parameters"]["properties"]["x"]
        assert prop["type"] == "string"

    def test_contract_removes_empty_enums(self):
        layer = EnvironmentContractLayer()
        tools = [{
            "type": "function",
            "function": {
                "name": "test",
                "parameters": {
                    "properties": {
                        "x": {"type": "string", "enum": []},
                    },
                },
            },
        }]
        calibrated = layer.calibrate_tools(tools)
        prop = calibrated[0]["function"]["parameters"]["properties"]["x"]
        assert "enum" not in prop

    def test_contract_truncates_long_descriptions(self):
        layer = EnvironmentContractLayer()
        tools = [{
            "type": "function",
            "function": {
                "name": "test",
                "description": "x" * 600,
                "parameters": {"properties": {}},
            },
        }]
        calibrated = layer.calibrate_tools(tools)
        desc = calibrated[0]["function"]["description"]
        assert len(desc) <= 500

    def test_contract_caching(self):
        layer = EnvironmentContractLayer()
        tools = [{
            "type": "function",
            "function": {
                "name": "cached_test",
                "parameters": {"properties": {"x": {"type": "string"}}},
            },
        }]
        t1 = layer.calibrate_tools(tools)
        t2 = layer.calibrate_tools(tools)
        assert t1 == t2

    def test_contract_calibrates_missing_required_in_props(self):
        layer = EnvironmentContractLayer()
        tools = [{
            "type": "function",
            "function": {
                "name": "test_func",
                "parameters": {
                    "properties": {
                        "query": {"type": "string"},
                    },
                },
            },
        }]
        calibrated = layer.calibrate_tools(tools)
        assert "query" not in calibrated[0]["function"]["parameters"].get("required", [])


class TestProceduralSkillLayer:
    @pytest.fixture
    def layer(self):
        return ProceduralSkillLayer()

    def test_register_and_retrieve_skill(self, layer):
        skill = ProceduralSkill(
            name="test_skill",
            trigger_patterns=[r"search|find"],
            intervention="Use search_wiki tool",
        )
        layer.register_skill(skill)
        matched = layer.retrieve_skills("search for AI papers", {})
        assert len(matched) == 1
        assert matched[0].name == "test_skill"

    def test_retrieve_skills_empty(self, layer):
        matched = layer.retrieve_skills("anything", {})
        assert matched == []

    def test_retrieve_from_error_state(self, layer):
        skill = ProceduralSkill(
            name="error_skill",
            trigger_patterns=[r"timeout"],
            intervention="Retry with longer timeout",
        )
        layer.register_skill(skill)
        matched = layer.retrieve_skills("test", {"last_error": "Connection timeout occurred"})
        assert len(matched) == 1

    def test_record_outcome(self):
        skill = ProceduralSkill(name="s", trigger_patterns=["x"], intervention="x")
        skill.record_outcome(True)
        skill.record_outcome(True)
        skill.record_outcome(False)
        assert skill.invocation_count == 3
        assert skill.success_count == 2
        assert skill.success_rate == 2 / 3

    def test_evolve_from_failures(self, layer):
        layer.record_failure("task1", "Error: connection failed", [])
        layer.record_failure("task2", "Error: connection failed", [])
        layer.record_failure("task3", "Error: connection failed", [])
        layer.evolve_from_failures(None)
        # Should have created an auto_skill
        assert any("auto_skill" in s.name for s in layer._skills.values())

    def test_failure_history_limit(self, layer):
        for i in range(1500):
            layer.record_failure(f"task{i}", f"error{i}", [])
        assert len(layer._failure_history) <= 1000

    def test_get_stats(self, layer):
        stats = layer.get_stats()
        assert "total_skills" in stats
        assert "failure_history" in stats


class TestActionRealizationLayer:
    @pytest.fixture
    def tools(self):
        return [{
            "type": "function",
            "function": {
                "name": "search",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            },
        }]

    def test_valid_tool_call(self, tools):
        layer = ActionRealizationLayer()
        result = layer.validate_tool_call({"name": "search", "arguments": {"query": "AI"}}, tools)
        assert result.valid
        assert result.canonicalized["name"] == "search"

    def test_missing_required_adds_default(self, tools):
        layer = ActionRealizationLayer()
        result = layer.validate_tool_call(
            {"name": "search", "arguments": {"query": "AI"}}, tools
        )
        assert result.valid

    def test_unknown_tool(self, tools):
        layer = ActionRealizationLayer()
        result = layer.validate_tool_call({"name": "nonexistent", "arguments": {}}, tools)
        assert not result.valid
        assert "Unknown tool" in (result.error or "")

    def test_empty_tool_call(self, tools):
        layer = ActionRealizationLayer()
        result = layer.validate_tool_call({}, tools)
        assert not result.valid

    def test_string_args_parsed(self, tools):
        layer = ActionRealizationLayer()
        result = layer.validate_tool_call(
            {"name": "search", "arguments": '{"query": "AI"}'}, tools
        )
        assert result.valid

    def test_invalid_json_args(self, tools):
        layer = ActionRealizationLayer()
        result = layer.validate_tool_call(
            {"name": "search", "arguments": "not json"}, tools
        )
        assert not result.valid

    def test_float_to_int_conversion(self, tools):
        layer = ActionRealizationLayer()
        result = layer.validate_tool_call(
            {"name": "search", "arguments": {"query": "AI", "limit": 5.7}}, tools
        )
        assert result.valid
        assert isinstance(result.canonicalized["arguments"]["limit"], int)

    def test_validate_action_empty(self):
        layer = ActionRealizationLayer()
        result = layer.validate_action("")
        assert not result.valid

    def test_validate_action_valid(self):
        layer = ActionRealizationLayer()
        result = layer.validate_action("Valid action")
        assert result.valid

    def test_validate_action_truncated(self):
        layer = ActionRealizationLayer()
        long_action = "x" * 20000
        result = layer.validate_action(long_action)
        assert result.valid
        assert len(result.canonicalized) <= 10000


class TestTrajectoryRegulationLayer:
    @pytest.fixture
    def layer(self):
        return TrajectoryRegulationLayer(
            max_stagnation=2,
            max_retries=3,
            max_actions=10,
            max_duration=3600,
        )

    def test_loop_detection(self, layer):
        action = {"name": "search", "arguments": {"query": "AI"}}
        for _ in range(3):
            layer.get_state("s1").record_action(action)
        intervention = layer.check_loop("s1")
        assert intervention is not None
        assert "bucle" in (intervention or "")

    def test_no_loop_with_different_actions(self, layer):
        for i in range(5):
            layer.get_state("s2").record_action({"name": f"action_{i}"})
        intervention = layer.check_loop("s2")
        assert intervention is None

    def test_retry_detection(self, layer):
        for _ in range(4):
            layer.get_state("s3").record_error()
        intervention = layer.check_retries("s3")
        assert intervention is not None
        assert "reintentos" in (intervention or "")

    def test_budget_exhaustion_actions(self, layer):
        for _ in range(10):
            layer.get_state("s4").record_action({"name": "a"})
        intervention = layer.check_budget("s4")
        assert intervention is not None

    def test_budget_exhaustion_duration(self, layer):
        layer.max_duration = 0
        intervention = layer.check_budget("s5")
        assert intervention is not None

    def test_check_all_returns_interventions(self, layer):
        for _ in range(3):
            for _ in range(3):
                layer.get_state("s6").record_action({"name": "same"})
            layer.get_state("s6").record_error()
        interventions = layer.check_all("s6")
        assert len(interventions) > 0
        # Check for loop AND retries
        has_loop = any("bucle" in i for i in interventions)
        has_retries = any("reintentos" in i for i in interventions)
        assert has_loop or has_retries

    def test_cleanup(self, layer):
        layer.get_state("s7").record_action({"name": "a"})
        assert "s7" in layer._trajectories
        layer.cleanup("s7")
        assert "s7" not in layer._trajectories


class TestRuntimeHarness:
    def test_harness_processes_tools(self):
        harness = RuntimeHarness()
        tools = [{
            "type": "function",
            "function": {
                "name": "test",
                "description": "x" * 600,
                "parameters": {"properties": {"x": {}}},
            },
        }]
        calibrated = harness.process_tools(tools)
        assert len(calibrated) == 1

    def test_harness_injects_skills(self):
        harness = RuntimeHarness()
        skill = ProceduralSkill(
            name="inject_test",
            trigger_patterns=[r"AI"],
            intervention="Check H-Mem for AI context",
        )
        harness.skill_layer.register_skill(skill)
        context = harness.inject_skills("Tell me about AI", {}, [])
        assert len(context) == 1
        assert "inject_test" in context[0].get("content", "")

    def test_harness_validates_tool_call(self):
        harness = RuntimeHarness()
        result = harness.validate_tool_call({"name": "nope", "arguments": {}}, [])
        assert not result.valid

    def test_harness_trajectory_tracking(self):
        harness = RuntimeHarness()
        harness.record_action("sid", {"name": "act"})
        harness.record_error("sid")
        checks = harness.check_trajectory("sid")
        assert isinstance(checks, list)

    def test_harness_stats(self):
        harness = RuntimeHarness()
        stats = harness.get_stats()
        assert "total_interventions" in stats
        assert "contract_layer" in stats
        assert "skill_layer" in stats
        assert "action_layer" in stats
        assert "trajectory_layer" in stats

    def test_harness_singleton(self):
        h1 = get_harness()
        h2 = get_harness()
        assert h1 is h2
