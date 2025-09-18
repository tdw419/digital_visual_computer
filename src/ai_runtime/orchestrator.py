import json
from pathlib import Path
import sqlite3
import importlib.util
import sys
import traceback

class AIRuntime:
    """
    The Orchestrator/Verifier (Ω) of the AI Runtime.
    This class executes plans (ASTs in our IR), manages state,
    and interacts with the Skill Library (Σ) and Memory (Μ).
    """
    def __init__(self, skill_dir="skills", memory_db="memory.db"):
        self.skill_dir = Path(skill_dir)
        self.memory_db = memory_db
        self.mem_conn = None
        self.skills = {}
        self.variables = {}
        self.planner = self._dummy_planner
        self.guardrails = {
            "max_execution_steps": 100,
            "allowed_skills": ["*"]  # Allow all for now
        }
        self._initialize()

    def _initialize(self):
        """Initializes the runtime, loading skills and connecting to memory."""
        self.skill_dir.mkdir(exist_ok=True)
        self.mem_conn = sqlite3.connect(self.memory_db)
        self._load_skills()
        print(f"AI Runtime (Ω) initialized with {len(self.skills)} skills.")

    def _load_skills(self):
        """Dynamically loads all skills from the skill directory."""
        for skill_file in self.skill_dir.glob("*.py"):
            skill_name = skill_file.stem
            try:
                spec = importlib.util.spec_from_file_location(skill_name, skill_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'skill'):
                    self.skills[skill_name] = getattr(module, 'skill')
                else:
                    print(f"Warning: Skill file {skill_file} does not have a 'skill' function.", file=sys.stderr)
            except Exception as e:
                print(f"Error loading skill {skill_name}: {e}", file=sys.stderr)

    def _dummy_planner(self, goal: str) -> list:
        """
        A placeholder for the real Planner (Π).
        It should return a plan (a list of IR nodes).
        """
        print(f"DUMMY_PLANNER: Received goal -> '{goal}'")
        # This would be replaced by a call to the GGUF-based planner
        return [{"op": "TRACE", "args": {"message": "Plan execution started."}}]

    def _resolve_args(self, args):
        """Recursively resolves arguments from variables."""
        if isinstance(args, dict):
            resolved = {}
            for key, value in args.items():
                resolved[key] = self._resolve_args(value)
            return resolved
        elif isinstance(args, list):
            return [self._resolve_args(item) for item in args]
        elif isinstance(args, str) and args in self.variables:
            return self.variables[args]
        else:
            return args

    def execute_plan(self, plan: list):
        """
        Executes a plan, which is a list of IR nodes.
        This is the core of the Orchestrator/Verifier.
        """
        self.variables = {}  # Reset state for each plan
        step_count = 0

        for node in plan:
            if step_count >= self.guardrails["max_execution_steps"]:
                print("GUARDRAIL: Maximum execution steps reached.", file=sys.stderr)
                break

            op = node.get("op")
            args = node.get("args", {})

            # Resolve arguments from variables recursively
            resolved_args = self._resolve_args(args)

            print(f"Executing step {step_count}: {op} with args {resolved_args}")

            if op == "TRACE":
                message = resolved_args.get("message", "")
                data = resolved_args.get("data", "")
                print(f"TRACE: {message} {data}")

            elif op == "CALL":
                skill_name = resolved_args.get("skill")
                params = resolved_args.get("params", {})
                result_to = resolved_args.get("result_to")

                if skill_name in self.skills:
                    try:
                        result = self.skills[skill_name](**params)
                        if result_to:
                            self.variables[result_to] = result
                    except Exception as e:
                        print(f"Error executing skill {skill_name}: {e}", file=sys.stderr)
                else:
                    print(f"Error: Skill '{skill_name}' not found.", file=sys.stderr)

            elif op == "RETURN":
                value = resolved_args.get("value")
                return self.variables.get(value, value) if isinstance(value, str) else value

            step_count += 1

        return self.variables.get("result", "Execution finished.")

    def run_goal(self, goal: str):
        """
        High-level method to run a goal from planning to execution.
        """
        # 1. Get a plan from the planner
        plan = self.planner(goal)

        # 2. Execute the plan
        result = self.execute_plan(plan)

        print(f"Goal '{goal}' completed with result: {result}")
        return result

def main():
    """A simple demonstration of the Orchestrator skeleton."""
    runtime = AIRuntime()

    # Example 1: A simple goal that the dummy planner will handle
    runtime.run_goal("Test the orchestrator.")

    # Example 2: Directly executing a plan that calls a skill
    print("\n--- Direct plan execution with CALL ---")
    direct_plan = [
        {"op": "TRACE", "args": {"message": "Plan to list files in the current directory."}},
        {"op": "CALL", "args": {
            "skill": "list_files",
            "params": {"directory": "."},
            "result_to": "file_list"
            }
        },
        {"op": "RETURN", "args": {"value": "file_list"}}
    ]
    result = runtime.execute_plan(direct_plan)
    print(f"Direct plan result: {result}")

if __name__ == "__main__":
    main()
