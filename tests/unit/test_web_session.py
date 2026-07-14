"""Session controller: a full playthrough over a fake channel, and two concurrent
sessions that stay fully isolated."""
import threading
import time

from frontends.web.webio import Channel
from frontends.web.session import Session
from tests.unit.test_full_playthrough import WALKTHROUGH
from tests.unit.i18n_walkthrough import render_walkthrough

CHAIN = " . ".join(WALKTHROUGH)
# The same winning walkthrough rendered into English surface commands (take note,
# go south, ...). An English game translates the input words, so the Dutch CHAIN would
# not parse in it; the English session must be driven with English commands to win.
# This is the repo's own established pattern (tests/unit/test_playthrough_i18n.py).
EN_CHAIN = " . ".join(render_walkthrough(WALKTHROUGH, "en"))


def run_session(events):
    """Run a Session in a worker thread, feeding `events`; return (session, sent)."""
    sent = []
    lock = threading.Lock()
    ch = Channel(lambda m: (lock.acquire(), sent.append(m), lock.release()) and None)
    session = Session(ch)
    t = threading.Thread(target=session.run, daemon=True)
    t.start()
    for ev in events:
        ch.put(ev)
    return session, sent, ch, t


def wait_until(pred, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.02)
    return False


def test_session_plays_a_full_game_to_the_win_nl():
    session, sent, ch, t = run_session([
        {"kind": "start", "lang": "nl"},
        {"kind": "key", "ch": " "},        # dismiss the title
        {"kind": "line", "text": CHAIN},   # the whole game in one chained command
    ])
    assert wait_until(lambda: session.engine is not None and session.engine.won)
    ch.close(); t.join(timeout=5)
    out = "".join(m.get("text", "") for m in sent if m.get("t") == "out")
    assert session.engine.world.message_text(281).splitlines()[0] in out


def test_two_concurrent_sessions_stay_isolated():
    # A in Dutch, B in English, played at the same time.
    a_sess, a_sent, a_ch, a_t = run_session([
        {"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "},
        {"kind": "line", "text": CHAIN}])
    b_sess, b_sent, b_ch, b_t = run_session([
        {"kind": "start", "lang": "en"}, {"kind": "key", "ch": " "},
        {"kind": "line", "text": EN_CHAIN}])   # English game -> English commands
    assert wait_until(lambda: a_sess.engine and a_sess.engine.won)
    assert wait_until(lambda: b_sess.engine and b_sess.engine.won)
    # Different engine + world objects -> no shared mutable state.
    assert a_sess.engine is not b_sess.engine
    assert a_sess.engine.world is not b_sess.engine.world
    # Language stayed isolated: A ran nl, B ran en.
    assert a_sess.engine.lang == "nl" and b_sess.engine.lang == "en"
    for ch, t in ((a_ch, a_t), (b_ch, b_t)):
        ch.close(); t.join(timeout=5)


def test_isolated_state_after_different_moves():
    a_sess, *_a = run_session([{"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "},
                               {"kind": "line", "text": "ga zuid"}])   # 0 -> 1
    b_sess, *_b = run_session([{"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "}])
    assert wait_until(lambda: a_sess.engine and a_sess.engine.room == 1)
    assert wait_until(lambda: b_sess.engine and b_sess.engine.room == 0)
    # run_session returns (session, sent, ch, t); after `a_sess, *_a` the channel is
    # _a[1] (a Thread has no .close(), so closing _a[1] — not _a[2] — is what unblocks
    # each worker at teardown).
    _a[1].close(); _b[1].close()
