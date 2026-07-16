"""Session-level integration: NamedWebSaveStore wired via player_store/limiter/ip, plus
the per-turn named autosave that keeps the active slot current without an explicit save."""
import threading

from frontends.web.webio import Channel
from frontends.web.session import Session
from frontends.web.playersaves import PlayerSaveStore
from frontends.web.authlimiter import AuthLimiter
from tests.unit.test_web_session import wait_until


def _run(events, ps, lim):
    sent = []
    ch = Channel(lambda m: sent.append(m))
    s = Session(ch, player_store=ps, limiter=lim, ip="ip")
    t = threading.Thread(target=s.run, daemon=True); t.start()
    for ev in events:
        ch.put(ev)
    return s, sent, ch, t


def test_menu_save_then_autosave_updates_slot(tmp_path):
    ps = PlayerSaveStore(tmp_path, b"pep")
    s, sent, ch, t = _run([
        {"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "},
        {"kind": "line", "text": "ga zuid"},                 # 0 -> 1
        {"kind": "menu", "action": "save"},                  # opens save dialog
        {"kind": "save-submit", "name": "Emma", "pin": "123456", "slot": "Kasteel"},
        {"kind": "line", "text": "ga noord"},                # 1 -> 0, should autosave to Kasteel
    ], ps, AuthLimiter())
    def autosaved_room_0():
        saved = ps.load("Emma", "123456", "Kasteel")
        return saved is not None and saved["room"] == 0
    assert wait_until(autosaved_room_0)                      # autosave captured the later move
    ch.close(); t.join(timeout=5)


def test_menu_load_restores_room(tmp_path):
    ps = PlayerSaveStore(tmp_path, b"pep")
    ps.save("Emma", "123456", "Kasteel", {"room": 11, "obj_loc": {}, "state": {}, "fail_counter": 0}, "nl")
    s, sent, ch, t = _run([
        {"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "},
        {"kind": "menu", "action": "load"},
        {"kind": "list-submit", "name": "Emma", "pin": "123456"},
        {"kind": "load-pick", "name": "Emma", "pin": "123456", "slot": "Kasteel"},
    ], ps, AuthLimiter())
    assert wait_until(lambda: s.engine is not None and s.engine.room == 11)
    ch.close(); t.join(timeout=5)


def test_new_game_after_load_does_not_overwrite_loaded_slot(tmp_path):
    ps = PlayerSaveStore(tmp_path, b"pep")
    ps.save("Emma", "123456", "Kasteel", {"room": 11, "obj_loc": {}, "state": {}, "fail_counter": 0}, "nl")
    s, sent, ch, t = _run([
        {"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "},
        {"kind": "menu", "action": "load"},
        {"kind": "list-submit", "name": "Emma", "pin": "123456"},
        {"kind": "load-pick", "name": "Emma", "pin": "123456", "slot": "Kasteel"},
        # now active=Kasteel, engine restored to room 11 -- start a brand-new game
        {"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "},
        {"kind": "line", "text": "ga zuid"},                 # new game: room 0 -> 1, triggers autosave
    ], ps, AuthLimiter())
    assert wait_until(lambda: s.engine is not None and s.engine.room == 1)
    assert ps.load("Emma", "123456", "Kasteel")["room"] == 11
    ch.close(); t.join(timeout=5)


def test_autosave_re_engages_after_cold_resume(tmp_path):
    # Cold resume rebuilds a fresh Session from the disk token-snapshot: no menu "save"
    # happens in this game -- the identity must come back purely from resume_active (the
    # persisted key+slot), so the next turn's autosave re-engages without the player
    # manually saving again.
    ps = PlayerSaveStore(tmp_path, b"pep")
    pre_state = {"room": 11, "obj_loc": {}, "state": {}, "fail_counter": 0}
    ps.save("Emma", "123456", "Kasteel", pre_state, "nl")
    resume_active = {"key": ps.key_for("Emma", "123456"), "slot": "Kasteel"}

    sent = []
    ch = Channel(lambda m: sent.append(m))
    s = Session(ch, player_store=ps, limiter=AuthLimiter(), ip="ip",
                resume_state=pre_state, resume_lang="nl", resume_active=resume_active)
    t = threading.Thread(target=s.run, daemon=True); t.start()
    ch.put({"kind": "line", "text": "ga zuid"})    # dorpsstraat (11) exits[1]=8 -> room 8
    assert wait_until(lambda: s.engine is not None and s.engine.room == 8)
    saved = ps.load("Emma", "123456", "Kasteel")
    assert saved is not None and saved["room"] == 8, \
        "autosave must re-engage after cold resume and capture the NEW room"
    ch.close(); t.join(timeout=5)
