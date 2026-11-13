from devrescue.synth import generate


def test_generate_unique_and_valid():
    pairs, incs = generate(200, seed=1)
    assert len(pairs) == len(incs) > 100
    assert len({p["prompt"] for p in pairs}) == len(pairs)
    for p in pairs:
        assert p["chosen"].startswith("ROOT CAUSE:") and p["rejected"] != p["chosen"]
        assert "{" not in p["prompt"] and "{" not in p["chosen"]  # all slots filled


def test_deterministic():
    assert generate(50, seed=3) == generate(50, seed=3)


def test_hard_negatives_are_formatted_but_wrong():
    easy, _ = generate(100, seed=2, hard_frac=0.0)
    hard, _ = generate(100, seed=2, hard_frac=1.0)
    assert [p["prompt"] for p in easy] == [p["prompt"] for p in hard]  # same prompts either way
    assert all(p["rejected"].startswith("ROOT CAUSE:") and p["rejected"] != p["chosen"] for p in hard)
    assert not any(p["rejected"].startswith("ROOT CAUSE:") for p in easy)
