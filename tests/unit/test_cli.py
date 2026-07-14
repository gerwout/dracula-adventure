"""run_cli.choose_language: the --lang flag and one-key (no-Enter) language selection."""
from run_cli import choose_language


class _KeyIO:
    """A stand-in for ConsoleIO that yields preset single keypresses (as read_key does)."""

    def __init__(self, keys):
        self.keys = list(keys)

    def read_key(self):
        return self.keys.pop(0)


def test_lang_flag_short_circuits():
    assert choose_language(["--lang", "en"]) == "en"
    assert choose_language(["--lang=nl"]) == "nl"


def test_single_key_selection_no_enter():
    assert choose_language([], _KeyIO(["2"])) == "en"          # press 2 -> English
    assert choose_language([], _KeyIO(["1"])) == "nl"          # press 1 -> Dutch


def test_ignores_junk_until_a_valid_number():
    assert choose_language([], _KeyIO(["x", "9", "2"])) == "en"


def test_eof_falls_back_to_the_default_language():
    assert choose_language([], _KeyIO(["stop"])) == "nl"       # first registered language


def test_run_cli_launcher_exposes_main():
    import run_cli
    assert callable(run_cli.main)
