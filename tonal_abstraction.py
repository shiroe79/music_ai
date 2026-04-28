from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from edo import EDOConfig, get_chord_templates, get_major_scale_pcs


# Quality classes — coarser grouping than raw chord quality
# These are the "atoms" the genre configs reason about.
#
# Why coarser? Because "maj7" and "maj9" behave the same harmonically in terms of function. We don't want genre configs to list every chord quality — just the functional family.

QUALITY_CLASS = {
    # Stable / tonic-like
    "maj":      "maj_triad",
    "sus2":     "maj_triad",
    "pow":      "maj_triad",
    "maj7":     "maj7",
    "maj9":     "maj7",        # same family

    # Minor / submediant
    "min":      "min_triad",
    "min7":     "min7",
    "min9":     "min7",
    "min11":    "min7",
    "minmaj7":  "minmaj7",     # minor-major 7th: noir, unstable

    # Dominant — the engine of harmonic motion
    "dom7":     "dom7",
    "dom9":     "dom7",
    "dom13":    "dom7",
    "lyd_dom":  "dom7_alt",    # lydian dominant: bright, floating
    "alt":      "dom7_alt",    # altered dominant: dark, chromatic tension

    # Diminished / half-diminished
    "dim":      "dim",
    "dim7":     "dim7",
    "hdim":     "hdim",        # half-dim (m7b5): jazz workhorse

    # Suspended / ambiguous
    "sus4":     "sus",

    # Augmented
    "aug":      "aug",

    # Quartal (no tonal center implied)
    "quartal":  "quartal",
}

# Stability scores for each quality class (0=maximum tension, 1=maximum rest)
QUALITY_STABILITY = {
    "maj_triad":  1.0,
    "maj7":       0.9,
    "min_triad":  0.75,
    "min7":       0.65,
    "minmaj7":    0.45,    # that raised 7th creates unease
    "dom7":       0.35,    # wants to resolve
    "dom7_alt":   0.20,    # altered dominant: high tension
    "sus":        0.50,    # ambiguous, neither tense nor relaxed
    "dim":        0.15,
    "dim7":       0.10,
    "hdim":       0.25,
    "aug":        0.20,
    "quartal":    0.55,    # ambiguous but not tense
}

# how strongly this quality wants to move somewhere.
# High pull = strong directional gravity.
QUALITY_PULL = {
    "maj_triad":  0.1,
    "maj7":       0.1,
    "min_triad":  0.2,
    "min7":       0.25,
    "minmaj7":    0.5,
    "dom7":       0.85,    # classic tritone resolution pull
    "dom7_alt":   0.90,
    "sus":        0.40,
    "dim":        0.70,
    "dim7":       0.75,
    "hdim":       0.55,
    "aug":        0.60,
    "quartal":    0.10,    # quartal harmony floats, doesn't pull
}

# Chromatic roles — what harmonic trick is this chord performing?
# None means diatonic / straightforward.
ChromaticRole = Optional[str]

# Diatonic degree detection ## calc for n-edo ##
def get_diatonic_degree(root_pc: int, tonic_pc: int, edo: EDOConfig) -> Optional[int]:
    """
    Return scale degree (1-7) if root_pc is diatonic in the major scale rooted at tonic_pc. Returns None if chromatic.
    Uses 12-EDO major scale approximation regardless of N
    (the abstraction layer is genre/function-based, not pitch-math-based).
    """
    # Map into 12-EDO pitch class space for degree detection
    interval = (root_pc - tonic_pc) % edo.N
    # MAJOR_SCALE_STEPS = [0, 2, 4, 5, 7, 9, 11]   # I II III IV V VI VII
    MAJOR_SCALE_STEPS = get_major_scale_pcs(edo)
    if interval in MAJOR_SCALE_STEPS:
        return MAJOR_SCALE_STEPS.index(interval) + 1   # 1-indexed
    return None   # chromatic


def detect_chromatic_role(
        root_pc: int, 
        quality_class: str,
        tonic_pc: int, 
        prev_root_pc: Optional[int],
        edo: EDOConfig) -> ChromaticRole:
    """
    Heuristic detection of special harmonic roles.
    This is intentionally rule-based (no ML) — these are music theory facts.
    """
    interval_from_tonic = (root_pc - tonic_pc) % edo.N

    # Neapolitan: bII (one semitone above tonic), usually major triad
    if interval_from_tonic == 1 and quality_class in ("maj_triad", "maj7"):
        return "neapolitan"

    # Borrowed bVII (common in rock, prog, jazz)
    if interval_from_tonic == 10 and quality_class in ("maj_triad", "dom7"):
        return "borrowed"

    # Tritone sub: dominant chord whose root is a tritone from the "expected" V
    # V is 7 semitones from tonic, tritone sub root is 1 semitone from tonic (or 6 from V)
    if quality_class in ("dom7", "dom7_alt") and interval_from_tonic == 1:
        return "tritone_sub"

    # Secondary dominant: dom7 chord not on V (degree 5)
    degree = get_diatonic_degree(root_pc, tonic_pc, edo)
    if quality_class in ("dom7", "dom7_alt") and degree not in (5, None):
        return "secondary_dom"

    # Chromatic mediant: root is a major or minor 3rd from previous root
    if prev_root_pc is not None:
        mv = abs(root_pc - prev_root_pc) % edo.N
        mv = min(mv, edo.N - mv)
        if mv in (3, 4) and quality_class in ("maj_triad", "min_triad", "maj7", "min7"):
            return "chromatic_med"

    # Augmented chord or altered dominant implies aug6 territory
    if quality_class in ("aug", "dom7_alt"):
        degree = get_diatonic_degree(root_pc, tonic_pc, edo)
        if degree is None:
            return "augmented_6th"

    return None


# TonalFunction: the abstraction unit
@dataclass(frozen=True)
class TonalFunction:
    """
    The tonal abstraction of a chord.
    This is what the GTTM scorer and genre configs reason about.
    No raw pitch content — only function and relationship metadata.
    """
    # Diatonic degree (1–7) or None if chromatic
    degree: Optional[int]

    # Quality class (coarser than raw quality)
    quality_class: str

    # How stable/relaxed this chord feels (0=tense, 1=relaxed)
    stability: float

    # Whether the root is diatonic in the current key
    diatonic: bool

    # Special harmonic role (None = plain diatonic function)
    chromatic_role: ChromaticRole

    # How strongly this chord wants to move forward (0=static, 1=strong pull)
    pull: float

    # Root movement from previous chord in semitones (None if first chord)
    root_move_semitones: Optional[int]

    # The quality class of the *previous* chord (for transition scoring)
    prev_quality_class: Optional[str]

    def __repr__(self):
        deg = f"deg={self.degree}" if self.degree else "chromatic"
        role = f" [{self.chromatic_role}]" if self.chromatic_role else ""
        return (f"TF({deg}, {self.quality_class}{role}, "
                f"stab={self.stability:.2f}, pull={self.pull:.2f})")


# Chord → TonalFunction converter
def chord_to_tonal_function(
        root_pc: int,
        quality: str,
        tonic_pc: int,
        edo: EDOConfig,
        prev_root_pc: Optional[int] = None,
        prev_quality: Optional[str] = None
        ) -> TonalFunction:

    qclass = QUALITY_CLASS.get(quality, "maj_triad")
    stability = QUALITY_STABILITY.get(qclass, 0.5)
    pull = QUALITY_PULL.get(qclass, 0.3)
    degree = get_diatonic_degree(root_pc, tonic_pc, edo)
    diatonic = (degree is not None)
    chromatic_role = detect_chromatic_role(root_pc, qclass, tonic_pc,
                                            prev_root_pc, edo)

    # Root movement in semitones 
    if prev_root_pc is not None:
        mv = (root_pc - prev_root_pc) % edo.N
        root_move = min(mv, edo.N - mv)
    else:
        root_move = None

    prev_qclass = QUALITY_CLASS.get(prev_quality, None) if prev_quality else None

    return TonalFunction(
        degree=degree,
        quality_class=qclass,
        stability=stability,
        diatonic=diatonic,
        chromatic_role=chromatic_role,
        pull=pull,
        root_move_semitones=root_move,
        prev_quality_class=prev_qclass,
    )


# Sequence abstraction: convert a chord sequence to TonalFunction sequence
def abstract_progression(chords: List[Tuple[int, str]],
                        tonic_pc: int,
                        edo: EDOConfig) -> List[TonalFunction]:
    result = []
    prev_root = None
    prev_quality = None
    for root_pc, quality in chords:
        tf = chord_to_tonal_function(
            root_pc, 
            quality, 
            tonic_pc, 
            edo,
            prev_root, 
            prev_quality
            )
        result.append(tf)
        prev_root = root_pc
        prev_quality = quality
    return result