"""Bit-exact reimplementation of the BASRUN pseudo-random number generator.

`DRACULA.EXE` is compiled Microsoft QuickBASIC (~3.22) running on the **BASRUN**
runtime.  Its `RND` is a classic Microsoft 24-bit linear-congruential generator,
decompiled here directly from `BASRUN.EXE` so the Python engine can reproduce the
game's random behaviour exactly.

Provenance (all offsets are into the original read-only `BASRUN.EXE`)
--------------------------------------------------------------------
* The LCG core is BASRUN routine at **file 0x2980 (CS:0x1dc0)**, reached from the
  RND micro-ops (see below).  Disassembly::

      mov ax,[0x3a]          ; seed_lo (24-bit seed, low 16 bits, DGROUP [0x3a])
      mov cx,[0x32]          ; MULT_lo = 0x43FD          (BASRUN DGROUP [0x32])
      mul cx
      xchg di,ax ; mov bx,dx
      mov ax,[0x3c]          ; seed_hi (bits 16..23, DGROUP [0x3c])
      mul cx                 ; seed_hi * MULT_lo         (cross term)
      add bx,ax
      mov ax,[0x34]          ; MULT_hi = 0x0003          (BASRUN DGROUP [0x34])
      mul word [0x3a]        ; MULT_hi * seed_lo         (cross term)
      add bx,ax
      add di,[0x36]          ; += INCR_lo = 0x9EC3       (BASRUN DGROUP [0x36])
      adc bl,[0x38]          ; += INCR_hi = 0x1A (byte)  (BASRUN DGROUP [0x38])
      xor bh,bh              ; keep result to 24 bits
      mov [0x3a],dx ; mov [0x3c],bx     ; store the new 24-bit seed
      mov ax,0x8800 ; jmp 0xcd4         ; normalise the 24-bit seed -> MBF single in [0, 1)

  i.e.  ``seed = (seed * 0x0343FD + 0x1A9EC3) mod 2**24``  and  ``RND = seed / 2**24``.
  RANGE IS **[0, 1)** (= seed / 2**24). This is nailed by the parser-failure selector,
  which does ``INT(RND * 3.0) + 8`` — that yields exactly {8,9,10} (= world.messages[7,8,9],
  the observed failure pool) ONLY for RND in [0,1); a [0,2) range would give {8..13} and
  hit unrelated messages. The describe-time "bird"/spawn gates (RND>0.8 / RND<=0.3, using
  the correctly-decoded DGROUP constants — see below) are scale-invariant with the range,
  so they cannot distinguish [0,1) from [0,2); the multiply-then-floor parser formula can,
  and it fixes the range at [0,1). (An earlier note here claimed [0,2) with thresholds
  1.6/0.6 — that came from decoding the MBF constants with the wrong exponent bias (128
  instead of 129), doubling every value; it is wrong.)
  MBF float constants (bias 129, verified: ``cd cc 4c 7d`` = MBF 0.1): parser threshold
  ``[0x13b4]=0.1``, multiplier ``[0x13b8]=3.0``, addend ``[0x13bc]=8.0``, bird gate
  ``[0x1632]=0.8``, Dracula-spawn gate ``[0x1636]=0.3``.
  The 32-bit LCG constants live in BASRUN's DGROUP right before the "Random Number
  Seed (-32768 to 32767)" RANDOMIZE prompt (BASRUN file 0x232 / 0x236).

* RND is dispatched through the **INT 3Dh** floating-point path, *not* INT 3Fh:
  - ``int3d 0x2a`` (BASRUN CS:0x1dac) = ``RND`` / ``RND(x>0)`` : always advance.
  - ``int3d 0x29`` (BASRUN CS:0x1db1) = ``RND(x)`` with argument handling:
        x  > 0  -> advance (same as above)
        x == 0  -> return the *last* value, do NOT advance
        x  < 0  -> reseed from x's bytes, then advance (BASRUN CS:0x1e00)
  (The INT 3Fh code 0x88 = B$RND worker exists too but the compiled game only
  emits the INT 3Dh forms.)

* RANDOMIZE is ``int3d 0x41`` (BASRUN CS:0x1e17, prompt/convert path) or
  ``int3d 0x42`` (BASRUN CS:0x1e33).  It folds its argument to 16 bits and stores
  it over the *high 16 bits* of the seed (``mov [0x3b],bx``), keeping seed bit 0..7.

Seed source for DRACULA
-----------------------
`DRACULA.EXE` calls **no RANDOMIZE and no TIMER** (verified: INT 3Dh ops 0x41/0x42
and the TIMER op are absent from its instruction stream).  Therefore the seed is
never reseeded and starts at BASRUN's initialised default, **5** (BASRUN.EXE image
`[0x3a]=0x0005`, `[0x3c]=0x0000`).  The game's RND stream is thus fully
deterministic and identical on every run.
"""
from __future__ import annotations


class BasrunRNG:
    """The BASRUN 24-bit LCG, bit-for-bit.

    >>> r = BasrunRNG()          # default seed 5, as the game starts
    >>> round(r.rnd(), 7)
    0.1677659
    >>> round(r.rnd(), 7)
    0.17808
    """

    MULT = 0x0343FD          # 214013   (BASRUN DGROUP [0x32]/[0x34])
    INCR = 0x1A9EC3          # 1744579  (BASRUN DGROUP [0x36]/[0x38])
    MASK = 0xFFFFFF          # 24-bit modulus (2**24)
    _SCALE = float(1 << 24)  # 16777216.0 -> RND in [0, 1)

    #: BASRUN's initialised seed (BASRUN.EXE image [0x3a]/[0x3c]); the value the
    #: game runs with because it never issues RANDOMIZE.
    DEFAULT_SEED = 5

    def __init__(self, seed: int = DEFAULT_SEED):
        self.seed = seed & self.MASK
        # RND(0) returns the last generated value; before the first advance the
        # runtime yields seed/2**24 for the initial seed.
        self._last = self.seed / self._SCALE

    # -- core ---------------------------------------------------------------
    def _advance(self) -> float:
        self.seed = (self.seed * self.MULT + self.INCR) & self.MASK
        self._last = self.seed / self._SCALE
        return self._last

    def rnd(self, x: float = 1.0) -> float:
        """QuickBASIC ``RND(x)``.

        ``x > 0`` (and the no-argument ``RND``) advance the generator and return
        the next value in ``[0, 1)``.  ``x == 0`` returns the last value without
        advancing.  ``x < 0`` reseeds from ``x`` and then returns one value.
        """
        if x < 0:
            self.reseed_from_float(x)
            return self._advance()
        if x == 0:
            return self._last
        return self._advance()

    def random(self) -> float:
        """No-argument ``RND`` (``int3d 0x2a``): always advance."""
        return self._advance()

    # -- seeding ------------------------------------------------------------
    def reseed(self, seed24: int) -> None:
        """Set the full 24-bit seed directly (bits 0..23)."""
        self.seed = seed24 & self.MASK
        self._last = self.seed / self._SCALE

    def randomize(self, n: int) -> None:
        """``RANDOMIZE n`` semantics.

        BASRUN overwrites the seed's high 16 bits (bits 8..23) with the argument
        and keeps the low 8 bits (``mov [0x3b],bx``).  For an integer ``n`` the
        16-bit value stored is ``n & 0xFFFF``.  (QuickBASIC's fold of a
        floating-point RANDOMIZE argument XORs the two mantissa words before this
        store; DRACULA never issues RANDOMIZE, so only the integer form is
        modelled here.)
        """
        v = n & 0xFFFF
        self.seed = ((v << 8) | (self.seed & 0xFF)) & self.MASK
        self._last = self.seed / self._SCALE

    def reseed_from_float(self, x: float) -> None:
        """``RND(x<0)`` reseed (BASRUN CS:0x1e00).

        The runtime takes the 4-byte MBF representation of ``x`` and mixes its
        bytes into the 24-bit seed.  DRACULA never uses negative RND arguments;
        this is provided for completeness and mixes the IEEE bytes analogously so
        the same input reseeds deterministically.
        """
        import struct
        b = struct.pack("<f", float(x))          # 4 bytes, low..high
        lo = b[0] | (b[1] << 8)
        hi = b[2] | (b[3] << 8)
        dl = (lo + ((hi >> 8) & 0xFF)) & 0xFF
        carry = 1 if (lo & 0xFF) + ((hi >> 8) & 0xFF) > 0xFF else 0
        dh = ((lo >> 8) + carry) & 0xFF
        al = (hi + (1 if dh == 0 and carry else 0)) & 0xFF
        self.seed = ((dl | (dh << 8)) | (al << 16)) & self.MASK
        self._last = self.seed / self._SCALE

    # -- game-specific convenience -----------------------------------------
    def parser_failure_message_index(self) -> int:
        """Reproduce DRACULA's parser-failure message selection — the value stored
        in ``[0xe34]``; the printed text is ``world.messages[index - 1]``.

        Handler at DRACULA.EXE 0x00e02..0x00e2c (see docs/parser-failure.md)::

            r1 = RND                           ' int3d 0x2a
            IF r1 <= 0.1 THEN record = 7       ' [0x13b4] = MBF 0.1 ; -> messages[6]  (~10%)
            ELSE record = INT(RND * 3.0) + 8   ' 2nd RND * [0x13b8]=3.0, +[0x13bc]=8.0
                                               '   -> {8,9,10} = messages[7,8,9] (~30% each)

        Returns the record index in {7, 8, 9, 10}. This is only the random pool; the
        room-0 help block (messages[230] after 4 consecutive fails) and the room-31
        special (messages[267]) are handled by the engine's turn/counter logic.
        """
        r1 = self.random()
        if r1 <= 0.1:
            return 7
        return int(self.random() * 3.0) + 8


# Backwards-friendly module-level default instance factory.
def new_game_rng() -> BasrunRNG:
    """A generator seeded exactly as the game starts (seed 5, no RANDOMIZE)."""
    return BasrunRNG(BasrunRNG.DEFAULT_SEED)


if __name__ == "__main__":  # pragma: no cover - quick self-check
    r = BasrunRNG()
    seq = [round(r.rnd(), 7) for _ in range(8)]
    print("seed=5 first 8 RND (in [0,1)):", seq)
    assert seq[0] == 0.1677659, seq
    print("bird gate (RND>0.8):", ["B" if v > 0.8 else "." for v in seq])
    g = new_game_rng()
    print("first 8 parser-failure records:",
          [g.parser_failure_message_index() for _ in range(8)])
