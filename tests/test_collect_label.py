from devrescue.candidates import dedupe
from devrescue.label import agreement, build_pairs
from devrescue.redact import redact


def test_redact_secrets_and_noise():
    raw = "2025-01-01T00:00:00Z \x1b[31mERR\x1b[0m token=abc123 ghp_" + "a" * 30 + " mail me@x.com postgres://u:pw@h/db"
    out = redact(raw)
    assert "abc123" not in out and "ghp_" not in out and "me@x.com" not in out and ":pw@" not in out
    assert "\x1b" not in out and out.startswith("ERR")


def test_redact_keeps_tail():
    assert redact("a" * 100 + "END", max_chars=10).endswith("END") and len(redact("a" * 100, max_chars=10)) == 10


def test_dedupe():
    assert dedupe(["A  b", "a b", "c", ""]) == ["A  b", "c"]


def test_build_pairs_and_agreement():
    l = [{"prompt": "p", "candidates": ["x", "y", "z"], "best": 0, "worst": 2},
         {"prompt": "q", "candidates": ["x", "y"], "best": 1, "worst": 1}]
    assert build_pairs(l) == [{"prompt": "p", "chosen": "x", "rejected": "z"}]
    b = [{"prompt": "p", "candidates": ["x", "y", "z"], "best": 1, "worst": 2}]
    assert agreement(l, b) == 0.0
