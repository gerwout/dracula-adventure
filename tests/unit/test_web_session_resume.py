from frontends.web.webio import Channel
from frontends.web.session import Session
from tests.unit.test_web_session import run_session, wait_until  # reuse harness


def test_safe_engine_never_lets_an_exception_kill_the_worker():
    # The worker-level backstop: any engine error on attacker input must be swallowed
    # (returning False), never propagate out and hang the client.
    s = Session(Channel(lambda m: None))

    def boom():
        raise ValueError("engine blew up")

    assert s._safe_engine(boom) is False
    assert s._safe_engine(lambda: None) is True


def run_session_ex(events, **kw):
    import threading
    sent = []
    ch = Channel(lambda m: sent.append(m))
    session = Session(ch, **kw)
    t = threading.Thread(target=session.run, daemon=True); t.start()
    for ev in events:
        ch.put(ev)
    return session, sent, ch, t


def test_autosnapshot_fires_each_turn():
    snaps = []
    session, sent, ch, t = run_session_ex(
        [{"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "},
         {"kind": "line", "text": "ga zuid"}],
        token="tokX", snapshotter=lambda st, lang: snaps.append((st, lang)))
    assert wait_until(lambda: session.engine and session.engine.room == 1)
    assert snaps and snaps[-1][0]["room"] == 1 and snaps[-1][1] == "nl"
    ch.close(); t.join(timeout=5)


def test_resume_state_restores_and_skips_intro():
    # a snapshot in room 1; resume should redraw room 1 (no title screen) and accept a command
    session, sent, ch, t = run_session_ex(
        [{"kind": "line", "text": "ga noord"}],   # 1 -> 0
        token="tokY", resume_state={"room": 1}, resume_lang="nl")
    assert wait_until(lambda: session.engine and session.engine.room == 0)
    text = "".join(m.get("text", "") for m in sent if m.get("t") == "out")
    assert "D R A C U L A" not in text          # intro/title was skipped
    ch.close(); t.join(timeout=5)
