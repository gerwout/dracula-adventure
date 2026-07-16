from frontends.web import savevalidate as v


def test_name_rules():
    assert v.valid_name("Emma")
    assert v.valid_name("emma van 1")
    assert not v.valid_name("")                 # empty
    assert not v.valid_name("a" * 25)           # too long
    assert not v.valid_name("../etc")           # path chars
    assert not v.valid_name("bad\x00name")      # control char
    assert not v.valid_name(123)                # non-str


def test_pin_rules():
    assert v.valid_pin("123456")                # min 6
    assert v.valid_pin("123456789012")          # max 12
    assert not v.valid_pin("12345")             # 5 digits
    assert not v.valid_pin("1234567890123")     # 13 digits
    assert not v.valid_pin("12a456")            # non-digit
    assert not v.valid_pin(123456)              # non-str


def test_slot_rules_and_normalize():
    assert v.valid_slot("Kasteel")
    assert v.valid_slot("  Begin  ")            # trimmed before check
    assert v.normalize_slot("  Begin  ") == "Begin"
    assert not v.valid_slot("../x")
    assert not v.valid_slot("x" * 25)


def test_trailing_newlines_rejected():
    # Fix 1: fullmatch anchors the entire string, rejecting trailing newlines
    assert not v.valid_pin("123456\n")
    assert not v.valid_pin("123456\r")
    assert not v.valid_name("Emma\n")
    assert not v.valid_slot("Kasteel\n")


def test_non_str_input_rejected():
    # Fix 2: non-str input is rejected without raising
    assert not v.valid_slot(123)


def test_boundary_name_lengths():
    # Boundary cases for name length (1–24)
    assert v.valid_name("a")
    assert v.valid_name("a" * 24)
    assert not v.valid_name("a" * 25)
