import inspect
from skills import default_skills
for name, func in inspect.getmembers(default_skills, inspect.isfunction):
    if not name.startswith("_"):
        print(f"Skill: {name}")
        break
print("Done")