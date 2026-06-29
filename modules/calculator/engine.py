"""
modules/calculator/engine.py

A safe arithmetic/scientific expression evaluator. We deliberately do NOT
call bare eval(user_input) -- that would let typed input execute arbitrary
Python (e.g. "__import__('os').system(...)"), which is unacceptable even
in a local desktop app. Instead we compile the expression with Python's ast
module and walk the resulting tree ourselves, only allowing a fixed set of
safe node types, operators, and whitelisted function/constant names.
"""

import ast
import math
import operator

# Whitelisted binary/unary operators -> implementation
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Whitelisted function names -> implementation (scientific mode)
_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log10,
    "ln": math.log,
    "sqrt": math.sqrt,
    "abs": abs,
    "exp": math.exp,
    "factorial": math.factorial,
    "round": round,
}

# Whitelisted constants
_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


class CalculatorError(Exception):
    pass


def evaluate(expression: str) -> float:
    """Parse and evaluate a single arithmetic/scientific expression string.
    Raises CalculatorError with a user-friendly message on anything
    invalid, unsupported, or unsafe."""
    expression = expression.strip()
    if not expression:
        raise CalculatorError("Empty expression")

    # Common calculator notation -> Python operators
    expression = expression.replace("×", "*").replace("÷", "/").replace("^", "**")
    expression = expression.replace("%", "/100")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise CalculatorError("Invalid expression")

    try:
        return _eval_node(tree.body)
    except CalculatorError:
        raise
    except ZeroDivisionError:
        raise CalculatorError("Cannot divide by zero")
    except (ValueError, OverflowError):
        raise CalculatorError("Math error")


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise CalculatorError("Invalid literal")

    if isinstance(node, ast.BinOp):
        op_func = _BIN_OPS.get(type(node.op))
        if op_func is None:
            raise CalculatorError("Unsupported operator")
        return op_func(_eval_node(node.left), _eval_node(node.right))

    if isinstance(node, ast.UnaryOp):
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise CalculatorError("Unsupported operator")
        return op_func(_eval_node(node.operand))

    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise CalculatorError(f"Unknown identifier '{node.id}'")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise CalculatorError("Unsupported function")
        if node.keywords:
            raise CalculatorError("Keyword arguments not supported")
        args = [_eval_node(arg) for arg in node.args]
        return _FUNCTIONS[node.func.id](*args)

    raise CalculatorError("Unsupported expression")
