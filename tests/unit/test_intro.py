"""Startup title screen (screenshots SS-6010/21373, EXE 0x52df/0x52b8)."""
from engine.game import new_game
from engine.io import ScriptedIO


def test_play_shows_title_and_serienummer_before_room0():
    io = ScriptedIO(["stop", "n"])
    eng = new_game(io)
    eng.play()
    assert "D R A C U L A   A V O N T U U R" in io.text
    assert "Serienummer:A000002-MSD" in io.text
    assert "(c) 1982 Incore Automatisering" in io.text
    assert "Druk een toets om te beginnen" in io.text
    # ... and room 0 still describes after the intro.
    assert eng.world.rooms[0].lines[0] in io.text


def test_play_clears_screen_after_the_title_screen():
    # After the press-a-key pause, play() must clear the screen (as the original does)
    # before showing the game. Verified via a spy IO that records the call order.
    from engine.io import ScriptedIO

    class SpyIO(ScriptedIO):
        def __init__(self, cmds):
            super().__init__(cmds)
            self.events = []

        def pause(self):
            self.events.append("pause")

        def clear(self):
            self.events.append("clear")

    io = SpyIO(["stop", "n"])
    new_game(io).play()
    # the title screen is drawn, THEN pause, THEN clear, THEN the game starts
    assert io.events == ["pause", "clear"]


def test_consoleio_clear_is_implemented_not_a_noop():
    # ConsoleIO must override clear() (the base class no-ops it).
    from engine.io import ConsoleIO, IO
    assert ConsoleIO.clear is not IO.clear
