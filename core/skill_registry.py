import inspect
import logging
from typing import Any, Self, Callable

logger = logging.getLogger(__name__)


class SkillRegistry:
    def __init__(self) -> None:
        self.skills: dict[str, Callable] = {}
        self._register_default_skills()
    
    def _register_default_skills(self) -> None:
        from skills import default_skills
        for name, func in inspect.getmembers(default_skills, inspect.isfunction):
            if not name.startswith("_"):
                self.skills[name] = func
                logger.info(f"✅ Skill cargado: {name}")
    
    def get_tools(self) -> list[dict]:
        tools = []
        for name, func in self.skills.items():
            doc = func.__doc__ or "No description"
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": doc.strip().split("\n")[0],
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            })
        
        for tool in tools:
            sig = inspect.signature(self.skills[tool["function"]["name"]])
            for param_name, param in sig.parameters.items():
                tool["function"]["parameters"]["properties"][param_name] = {
                    "type": "string",
                    "description": f"Parameter {param_name}",
                }
                if param.default is inspect.Parameter.empty:
                    tool["function"]["parameters"]["required"].append(param_name)
        
        return tools
    
    def execute(self, tool_name: str, arguments: dict) -> Any:
        if tool_name not in self.skills:
            return {"error": f"Skill {tool_name} not found"}
        
        logger.incoming(f"⚡ [SKILL] {tool_name} | {arguments}")
        
        try:
            func = self.skills[tool_name]
            result = func(**arguments)
            logger.success(f"✅ [SKILL OK] {tool_name}")
            return result
        except Exception as e:
            logger.error(f"❌ [SKILL ERROR] {tool_name}: {e}: {e}")
            return {"error": str(e)}
    
    def list_skills(self) -> list[str]:
        return list(self.skills.keys())