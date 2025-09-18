"""
Math Evaluation Skill
"""
import math

def skill(expression: str) -> float:
    """
    Evaluates a simple mathematical expression.
    WARNING: This uses eval() and is not safe for untrusted input.
             A real implementation should use a safe parser.

    :param expression: The mathematical expression to evaluate.
    :return: The result of the evaluation.
    """
    try:
        # For safety, only allow access to math module functions
        safe_globals = {"__builtins__": None}
        safe_locals = {
            "math": math,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "sqrt": math.sqrt, "pow": math.pow, "pi": math.pi, "e": math.e
        }
        return eval(expression, safe_globals, safe_locals)
    except Exception as e:
        return f"Error evaluating expression: {e}"
