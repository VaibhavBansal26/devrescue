from devrescue.eval import fuzzy, score

RC = "the 'user_id' key is missing from the input dict"


def test_fuzzy_vs_exact():
    ans = "ROOT CAUSE: input dict lacks the user_id key.\nFIX:\n1. fix"
    assert fuzzy(ans, RC) and not score([{"root_cause": RC}], [ans])["exact"]
    assert not fuzzy("ROOT CAUSE: disk is full.\nFIX:\n1. x", RC)


def test_format_rate():
    assert score([{"root_cause": "x y"}], ["The issue is x y"])["format"] == 0.0
