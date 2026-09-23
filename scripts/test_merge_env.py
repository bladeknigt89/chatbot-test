from pathlib import Path

from merge_env import merge_env_from_example, parse_env_entries, parse_env_keys


def test_parse_skips_comments_and_duplicates():
    text = (
        "# comment\n"
        "A=1\n"
        "\n"
        "B=two\n"
        "A=ignored\n"
        "# C=nope\n"
    )
    assert parse_env_entries(text) == [("A", "1"), ("B", "two")]
    assert parse_env_keys(text) == {"A", "B"}


def test_merge_creates_env_from_example(tmp_path: Path):
    example = tmp_path / ".env.example"
    env_path = tmp_path / ".env"
    example.write_text("FOO=bar\nBAZ=qux\n", encoding="utf-8")
    added = merge_env_from_example(env_path=env_path, example_path=example)
    assert added == ["FOO", "BAZ"]
    assert env_path.read_text(encoding="utf-8") == "FOO=bar\nBAZ=qux\n"


def test_merge_appends_only_missing_keys(tmp_path: Path):
    example = tmp_path / ".env.example"
    env_path = tmp_path / ".env"
    example.write_text(
        "# new stuff\n"
        "KEEP_ME=example-default\n"
        "NEW_KEY=from-example\n"
        "ALSO_NEW=42\n",
        encoding="utf-8",
    )
    env_path.write_text("KEEP_ME=user-value\nOLD_ONLY=stay\n", encoding="utf-8")
    added = merge_env_from_example(env_path=env_path, example_path=example)
    assert added == ["NEW_KEY", "ALSO_NEW"]
    text = env_path.read_text(encoding="utf-8")
    assert "KEEP_ME=user-value" in text
    assert "OLD_ONLY=stay" in text
    assert "NEW_KEY=from-example" in text
    assert "ALSO_NEW=42" in text
    assert "KEEP_ME=example-default" not in text


def test_merge_noop_when_complete(tmp_path: Path):
    example = tmp_path / ".env.example"
    env_path = tmp_path / ".env"
    example.write_text("A=1\nB=2\n", encoding="utf-8")
    env_path.write_text("A=x\nB=y\n", encoding="utf-8")
    before = env_path.read_text(encoding="utf-8")
    assert merge_env_from_example(env_path=env_path, example_path=example) == []
    assert env_path.read_text(encoding="utf-8") == before
