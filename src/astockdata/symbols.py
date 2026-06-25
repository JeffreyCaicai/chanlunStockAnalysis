import re


def normalize_code(code: str) -> str:
    """Normalize common A-share ticker formats to a six-digit code."""
    text = code.strip().upper()
    text = re.sub(r"^(SH|SZ|BJ)", "", text)
    text = re.sub(r"\.(SH|SZ|BJ)$", "", text)
    if not re.fullmatch(r"\d{6}", text):
        raise ValueError(f"Invalid A-share code: {code!r}")
    return text


def market_prefix(code: str) -> str:
    code = normalize_code(code)
    if code.startswith(("6", "9")):
        return "sh"
    if code.startswith("8"):
        return "bj"
    return "sz"


def secid(code: str) -> str:
    code = normalize_code(code)
    market_id = "1" if code.startswith(("6", "9")) else "0"
    return f"{market_id}.{code}"

