"""Strip secrets/PII and noise from raw logs before storing or labeling them."""
import re

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z\s?", re.M)
_PATTERNS = [
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "<GITHUB_TOKEN>"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "<AWS_KEY>"),
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "<API_KEY>"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"), "Bearer <TOKEN>"),
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b(\s*[=:]\s*)\S+"), r"\1\2<REDACTED>"),
    (re.compile(r"://([^:/\s]+):([^@/\s]+)@"), r"://\1:<REDACTED>@"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<EMAIL>"),
]


def redact(text: str, max_chars: int = 6000) -> str:
    text = _TS.sub("", _ANSI.sub("", text))
    for pat, rep in _PATTERNS:
        text = pat.sub(rep, text)
    return text[-max_chars:]  # failures are usually at the end
