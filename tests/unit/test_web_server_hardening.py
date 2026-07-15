"""Security-hardening wiring on the web server: Origin allow-list env parsing and the
bounded max message size. (Live Origin *enforcement* is verified against the deployed
server; here we pin the pure config helpers.)"""
from frontends.web import server


def test_allowed_origins_unset_means_no_check(monkeypatch):
    monkeypatch.delenv("DRACULA_WEB_ORIGINS", raising=False)
    assert server._allowed_origins() is None


def test_allowed_origins_parses_comma_list(monkeypatch):
    monkeypatch.setenv("DRACULA_WEB_ORIGINS", "https://a.example, https://b.example ")
    assert server._allowed_origins() == ["https://a.example", "https://b.example"]


def test_allowed_origins_blank_is_none(monkeypatch):
    monkeypatch.setenv("DRACULA_WEB_ORIGINS", "   ")
    assert server._allowed_origins() is None


def test_max_message_size_is_bounded_well_below_1mb():
    assert 0 < server.MAX_MESSAGE_SIZE <= 128 * 1024
