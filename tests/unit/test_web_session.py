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


def test_menu_offers_new_and_language_after_game_over():
    session, sent, ch, t = run_session([
        {"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "},
        {"kind": "line", "text": CHAIN}])          # play to the win -> game over

    def game_over_start_await_enables_new():
        for m in reversed(sent):
            if m.get("t") == "await" and m.get("mode") == "start":
                menu = m.get("menu")
                return isinstance(menu, dict) and menu.get("new") and menu.get("language")
        return False

    assert wait_until(game_over_start_await_enables_new), \
        "after game-over the menu must let the player start a new game (no soft-lock)"
    ch.close(); t.join(timeout=5)


def test_title_await_key_offers_a_continue_button():
    # The dead 1/2/J/N/spatie row is gone: the title's await:key prompt now carries a
    # single contextual "keys" hint (a ▶ Verder/Continue button), driven by the lexicon
    # so it follows the active language like everything else player-facing.
    session, sent, ch, t = run_session([{"kind": "start", "lang": "nl"}])

    def title_await_has_continue():
        awaits = [m for m in sent if m.get("t") == "await" and m.get("mode") == "key"]
        return bool(awaits) and session.engine is not None and awaits[-1].get("keys") == [
            {"label": session.engine.lex.ui("BTN_CONTINUE"), "ch": " "}]

    assert wait_until(title_await_has_continue)
    ch.close(); t.join(timeout=5)


def test_help_menu_works_at_the_title_screen():
    session, sent, ch, t = run_session([
        {"kind": "start", "lang": "nl"},
        {"kind": "menu", "action": "help"},         # tapped at the title, before dismissing
        {"kind": "key", "ch": " "}])
    assert wait_until(lambda: any(m.get("t") == "help" for m in sent)), \
        "Help must work at the title screen"
    ch.close(); t.join(timeout=5)


def test_worker_terminates_on_disconnect_during_menu_load():
    session, sent, ch, t = run_session([
        {"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "},
        {"kind": "menu", "action": "load"},      # -> do_laad -> WebSaveStore.load() blocks for 'loaded'
    ])
    # wait until the worker is actually blocked waiting for the client's save data
    assert wait_until(lambda: any(m.get("t") == "load" for m in sent))
    ch.close()                                    # disconnect BEFORE the client replies 'loaded'
    t.join(timeout=5)
    assert not t.is_alive(), "worker must terminate after a disconnect during a menu Load"
