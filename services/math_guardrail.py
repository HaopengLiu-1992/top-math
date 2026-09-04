import ast
import re
from fractions import Fraction


_SUPERSCRIPT_DIGITS = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
}
_PURE_EXPRESSION = re.compile(r"^[0-9().+\-*/\s]+$")
_NUMBER_OR_EXPRESSION = re.compile(r"^[=\s]*[0-9().+\-*/\s]+$")


def validate(homework: dict, difficulty_policy: str) -> list[str]:
    errors: list[str] = []
    parts = homework.get("parts") or {}
    if not isinstance(parts, dict):
        return ["parts must be an object"]
    expected_counts = {"part1": 20, "part2": 12, "part3": 3}

    if difficulty_policy == "challenge":
        for part, expected in expected_counts.items():
            items = parts.get(part)
            if not isinstance(items, list) or len(items) != expected:
                errors.append(f"{part} must contain exactly {expected} questions")

    ids = []
    for part_name in expected_counts:
        for item in parts.get(part_name) or []:
            if not isinstance(item, dict):
                errors.append(f"{part_name} contains a non-object question")
                continue
            if item.get("id"):
                ids.append(item["id"])
            if not item.get("question") or item.get("answer") in (None, ""):
                errors.append(f"{item.get('id', part_name)} needs a question and answer")
    if len(ids) != len(set(ids)):
        errors.append("question ids must be unique")

    for item in parts.get("part1") or []:
        question = str(item.get("question", "")).strip()
        normalized = _normalize_expression(question)
        if not normalized or not _PURE_EXPRESSION.fullmatch(normalized):
            continue
        try:
            expected = _evaluate(normalized)
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
            continue
        answer_text = str(item.get("answer", "")).strip()
        normalized_answer = _normalize_expression(answer_text.lstrip("= "))
        if not normalized_answer or not _NUMBER_OR_EXPRESSION.fullmatch(normalized_answer):
            errors.append(f"{item.get('id', 'part1')}: pure calculation needs a numeric answer")
            continue
        try:
            actual = _parse_numeric_answer(normalized_answer)
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
            errors.append(f"{item.get('id', 'part1')}: answer is not a valid number")
            continue
        if actual != expected:
            errors.append(
                f"{item.get('id', 'part1')}: answer mismatch for {question}; "
                f"expected {_format_fraction(expected)}, received {answer_text}"
            )
    return errors


def _normalize_expression(value: str) -> str:
    expanded = []
    previous = ""
    in_exponent = False
    for char in value:
        if char in _SUPERSCRIPT_DIGITS:
            if not in_exponent and (previous.isdigit() or previous == ")"):
                expanded.append("**")
            expanded.append(_SUPERSCRIPT_DIGITS[char])
            in_exponent = True
        else:
            expanded.append(char)
            in_exponent = False
        previous = char
    value = "".join(expanded)
    value = value.replace("×", "*").replace("·", "*").replace("÷", "/")
    value = value.replace("−", "-").replace("^", "**").replace(",", "")
    return value.strip()


def _evaluate(expression: str) -> Fraction:
    node = ast.parse(expression, mode="eval")
    return _eval_node(node.body)


def _parse_numeric_answer(value: str) -> Fraction:
    mixed = re.fullmatch(r"(-?\d+)\s+(\d+)\s*/\s*(\d+)", value)
    if mixed:
        whole, numerator, denominator = (int(part) for part in mixed.groups())
        fraction = Fraction(numerator, denominator)
        return Fraction(whole) - fraction if whole < 0 else Fraction(whole) + fraction
    return _evaluate(value)


def _eval_node(node: ast.AST) -> Fraction:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Fraction(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow) and right.denominator == 1 and abs(right) <= 12:
            return left ** right.numerator
    raise ValueError("unsupported arithmetic expression")


def _format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"
