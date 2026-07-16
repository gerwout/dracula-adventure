"""Save/load routes through a pluggable SaveStore (default = the save file)."""
from engine.game import new_game
from engine.io import ScriptedIO
from engine.savegame import FileSaveStore


class DictStore:
    """In-memory store (stands in for the web client's localStorage)."""
    def __init__(self):
        self.data = None
    def save(self, data):
        self.data = dict(data)
        return True
    def load(self):
        return dict(self.data) if self.data is not None else None


def test_do_bewaar_and_do_laad_round_trip_through_the_store():
    store = DictStore()
    eng = new_game(ScriptedIO([]), explore=True, store=store)
    eng.submit("ga zuid")                 # room 0 -> 1
    saved_room = eng.room
    eng.do_bewaar(None)
    assert store.data is not None and store.data["room"] == saved_room
    assert eng.world.message_text(185) in eng.io.text
    eng.submit("ga noord")                # 1 -> 0
    assert eng.room != saved_room
    eng.do_laad(None)
    assert eng.room == saved_room         # restored from the store


def test_do_laad_reports_no_save_when_store_empty():
    eng = new_game(ScriptedIO([]), explore=True, store=DictStore())
    eng.do_laad(None)                     # store empty -> the load-fail message, no crash
    assert eng.world.message_text(188) in eng.io.text


def test_do_stop_j_answer_saves_via_store():
    store = DictStore()
    eng = new_game(ScriptedIO(["J"]), explore=True, store=store)   # 'J' = save on quit
    eng.do_stop(None)
    assert store.data is not None
    assert not eng.running


def test_file_store_is_the_default_and_writes_the_file(tmp_path):
    store = FileSaveStore(tmp_path / "s.json")
    eng = new_game(ScriptedIO([]), explore=True, store=store)
    eng.do_bewaar(None)
    assert (tmp_path / "s.json").exists()
    eng.submit("ga zuid")
    eng.do_laad(None)
    assert eng.room == 0                  # restored to the saved starting room
