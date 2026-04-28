from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

# Transition preference: quality_class → quality_class
# Each key is a (from_quality_class, to_quality_class) pair.
# Value is a float reward/penalty added to the transition score.

TransitionMatrix = Dict[Tuple[str, str], float]


# ── Fusion Jazz transition preferences ────────────────────────────────────────
FUSION_TRANSITIONS: TransitionMatrix = {
    # ── Core II-V-I moves (backbone) ──
    ("min7",    "dom7"):      +2.0,   # ii → V (strongest fusion move)
    ("hdim",    "dom7_alt"):  +2.5,   # iiø → V alt (minor ii-V, very fusion)
    ("hdim",    "dom7"):      +1.5,   # iiø → V (standard minor ii-V)
    ("dom7",    "maj7"):      +2.0,   # V → Imaj7 (resolution)
    ("dom7",    "min7"):      +1.5,   # V → imin7 (minor resolution)
    ("dom7_alt","maj7"):      +2.5,   # Valt → Imaj7 (altered resolution, very jazz)
    ("dom7_alt","min7"):      +2.5,   # Valt → imin7
    ("dom7",    "dom7"):      +1.0,   # dominant pedal / chain (turnaround)
    ("dom7_alt","dom7_alt"):  +0.5,   # altered chain (less common)

    # ── Tritone substitution ──
    ("dom7",    "dom7_alt"):  +1.5,   # pivoting to alt dom before resolution
    # (tritone_sub role detection handles scoring bonus separately)

    # ── Modal / static moves ──
    ("min7",    "min7"):      +1.5,   # modal vamp (Maiden Voyage / Milestones feel)
    ("maj7",    "maj7"):      +1.0,   # Lydian modal stretch
    ("sus",     "sus"):       +1.0,   # Herbie Hancock sus vamp
    ("sus",     "dom7"):      +1.5,   # sus resolves to dom (classic)
    ("sus",     "min7"):      +1.0,   # sus floats to minor
    ("quartal", "min7"):      +1.0,   # quartal → tonal landing

    # ── Chromatic mediant (3rd relations) ──
    ("maj7",    "min7"):      +1.0,   # color move, common in jazz
    ("min7",    "maj7"):      +0.8,
    # (chromatic_med role detection adds bonus separately)

    # ── Secondary dominant approach ──
    ("dom7",    "min7"):      +1.5,   # V/ii → ii (secondary dominant resolving)
    ("dom7",    "maj7"):      +1.0,   # V/IV → IV

    # ── Penalized moves (not idiomatic for fusion) ──
    ("maj_triad","maj_triad"): -1.0,  # plain triads = not jazz enough
    ("min_triad","min_triad"): -1.0,  # plain triads
    ("maj_triad","dom7"):      -0.5,  # triadic → dom feels too rock/pop
    ("dim",     "maj_triad"):  -0.5,  # diminished → plain triad = old-fashioned

    # ── Ambiguous but allowed ──
    ("minmaj7", "dom7_alt"):  +1.0,   # minmaj7 tension → altered resolution
    ("aug",     "maj7"):      +0.8,   # augmented → major (classical move, ok in fusion)
    ("dim7",    "dom7_alt"):  +0.8,   # dim7 → alt dom (chromatic approach)
}

# ── Progressive Rock transition preferences ───────────────────────────────────
PROG_ROCK_TRANSITIONS: TransitionMatrix = {
    # ── Modal diatonic moves (backbone) ──
    ("min7",    "min7"):      +1.5,   # Dorian vamp (core prog move)
    ("min7",    "maj_triad"): +2.0,   # i → bIII (Aeolian / natural minor)
    ("maj_triad","min7"):     +1.5,   # bIII → i return
    ("min7",    "maj7"):      +1.0,   # i → bVII maj7 (Mixolydian color)
    ("maj7",    "min7"):      +1.0,   # bVII → i

    # ── Borrowed / modal interchange ──
    ("maj_triad","maj_triad"):+1.5,   # bVII → I, bVI → I (borrowed major triads)
    ("maj7",    "maj_triad"): +1.5,   # IV maj7 → I (pastoral)
    ("min7",    "dom7"):      +1.0,   # modal → functional dom (surprising resolution)

    # ── Chromatic mediant moves (prog fingerprint) ──
    # (chromatic_med detection adds bonus; here we reward the quality pairs)
    ("maj_triad","maj_triad"):+1.5,   # Major → Major 3rd apart (e.g., C → E → Ab)
    ("min7",    "min7"):      +1.0,   # Minor → Minor 3rd apart
    ("maj7",    "min7"):      +1.0,   # Lydian → Dorian (color shift)

    # ── Sus / suspension moves ──
    ("sus",     "maj_triad"): +2.0,   # sus4 → I resolution (very prog)
    ("sus",     "min7"):      +1.5,   # sus → minor (unresolved feel)
    ("maj_triad","sus"):      +1.0,   # moving into suspended texture

    # ── Power chord / bare fifth ──
    ("maj_triad","maj_triad"):+1.0,   # parallel 5ths / power chord sequences
    ("min7",    "maj_triad"): +1.5,   # modal approach

    # ── Diminished as passing ──
    ("dim",     "maj_triad"): +1.5,   # passing dim → major (not ii-V, just passing)
    ("dim",     "min7"):      +1.0,   # passing dim → minor
    ("dim7",    "maj_triad"): +1.0,

    # ── Penalized moves (not idiomatic for prog rock) ──
    ("dom7",    "maj7"):      -1.5,   # V → I functional cadence feels too pop/jazz
    ("hdim",    "dom7_alt"):  -2.0,   # jazz ii-V minor is out of idiom
    ("dom7_alt","min7"):      -2.0,   # altered dominants = jazz, not prog
    ("dom7_alt","maj7"):      -1.5,
    ("quartal", "min7"):      -0.5,   # quartal is unusual in prog (more fusion)
    ("dom7",    "dom7"):      -1.0,   # dominant chains feel jazzy, not prog

    # ── Allowed but neutral ──
    ("aug",     "maj_triad"): +0.5,   # augmented → I (romantic/prog color)
    ("minmaj7", "min7"):      +0.3,   # minmaj7 for brief dark color
}


# ─────────────────────────────────────────────────────────────────────────────


# GTTM Feature weights per genre
@dataclass
class GenreFeatureWeights:
    """
    GTTM-inspired feature weights for genre scoring.
    All weights are floats. (+ = reward, - = penalty).
    """

    # ── Prolongation / tension features ──────────────────────────────────
    # Reward for high stability at phrase starts/endings
    w_stability_at_boundary: float = 1.0

    # Penalty for unresolved tension (high pull chord left unresolved)
    w_unresolved_tension: float = -1.0

    # Reward for smooth stability arc (tension builds then releases)
    w_smooth_tension_arc: float = 1.0

    # Reward for dramatic tension arc (sudden spikes and drops)
    w_dramatic_tension_arc: float = 0.0

    # ── Diatonic vs chromatic balance ────────────────────────────────────
    # Reward for diatonic chord in sequence
    w_diatonic_chord: float = 0.5

    # Reward for chromatic chord with a recognized special role
    w_chromatic_with_role: float = 0.5

    # Penalty for chromatic chord with NO recognized role (random chromaticism)
    w_chromatic_no_role: float = -0.5

    # ── Root movement features ────────────────────────────────────────────
    # Reward for 5th motion (V→I type root movement, 5 or 7 semitones)
    w_fifth_motion: float = 1.0

    # Reward for stepwise root motion (1-2 semitones)
    w_stepwise_motion: float = 0.5

    # Reward for 3rd motion (chromatic mediant, 3-4 semitones)
    w_third_motion: float = 0.0

    # Penalty for tritone root motion (6 semitones) when not a tritone sub
    w_tritone_motion_raw: float = -0.5

    # ── Repetition / variety features ────────────────────────────────────
    # Reward for quality class staying the same (modal vamp)
    w_quality_repetition: float = 0.0

    # Penalty for same quality class repeated too many times (>3 in a row)
    w_quality_excess_repetition: float = -1.0

    # Reward for alternating between two quality classes (ostinato)
    w_quality_alternation: float = 0.0

    # ── Structural / phrase-level features ──────────────────────────────────
    # Reward for dominant chord near phrase end (functional closure)
    w_dominant_near_cadence: float = 0.5

    # Reward for stable chord at phrase start (tonic establishment)
    w_tonic_at_start: float = 0.5

    # Penalty for ending a phrase on a high-pull chord
    w_open_phrase_ending: float = -0.5

    # ── Special chromatic role rewards (genre-specific) ──────────────────
    # Reward when tritone substitution is used
    w_tritone_sub: float = 0.0

    # Reward when secondary dominant is used
    w_secondary_dom: float = 0.0

    # Reward when chromatic mediant is used
    w_chromatic_med: float = 0.0

    # Reward when borrowed chord (modal interchange) is used
    w_borrowed: float = 0.0

    # Reward when neapolitan is used
    w_neapolitan: float = 0.0

    # ── Transition matrix weight ──────────────────────────────────────────
    # Overall multiplier on the transition preference lookup score
    w_transition_matrix: float = 1.0



# Genre config: combines transition matrix + feature weights + structural prefs
@dataclass
class GenreConfig:
    # Fingerprint for a genre.
    # This is what gets passed to the GTTM scorer.
    name: str
    description: str

    # Transition preference matrix
    transitions: TransitionMatrix

    # GTTM feature weights
    features: GenreFeatureWeights

    # ── Structural tendencies ──────────────────────────────────────────────
    # Expected phrase length in beats (soft preference, not hard constraint)
    phrase_length_beats: int = 8

    # Tolerance for chromatic moves (0=must be diatonic, 1=anything goes)
    chromaticism_tolerance: float = 0.5

    # Target average stability (0=very tense throughout, 1=very relaxed)
    target_avg_stability: float = 0.5

    # How fast tension should change beat to beat (0=static, 1=volatile)
    tension_volatility: float = 0.3

    # Preferred root movement sizes (semitones), in order of preference
    preferred_root_moves: list = field(default_factory=lambda: [5, 7, 2, 4])

    # Quality classes that are "home base" for this genre (high probability start/end)
    home_quality_classes: list = field(default_factory=lambda: ["maj7", "min7"])


# ─────────────────────────────────────────────────────────────────────────────
# FUSION JAZZ CONFIG
# ─────────────────────────────────────────────────────────────────────────────

FUSION_JAZZ_CONFIG = GenreConfig(
    name="fusion_jazz",
    description=(
        "Jazz fusion: extended chords, ii-V-I backbone, altered dominants, "
        "tritone subs, modal vamps, chromatic approach. "
        "Think: Mahavishnu, Weather Report, Herbie Hancock, Return to Forever."
    ),
    transitions=FUSION_TRANSITIONS,
    features=GenreFeatureWeights(
        # Tension features
        w_stability_at_boundary=1.0,
        w_unresolved_tension=-0.5,      # jazz tolerates more unresolved tension
        w_smooth_tension_arc=0.8,
        w_dramatic_tension_arc=0.3,

        # Diatonic/chromatic balance
        w_diatonic_chord=0.3,           # diatonic is ok but not specially rewarded
        w_chromatic_with_role=1.2,      # chromatic moves WITH a role = very jazz
        w_chromatic_no_role=-0.8,       # random chromaticism = bad

        # Root movement
        w_fifth_motion=1.5,             # ii-V motion (5th) is the jazz backbone
        w_stepwise_motion=0.8,          # chromatic approach steps (very jazz)
        w_third_motion=0.6,             # chromatic mediant ok in fusion
        w_tritone_motion_raw=-0.2,      # tritone motion ok IF it's a tritone sub

        # Repetition
        w_quality_repetition=0.8,       # modal vamps are idiomatic
        w_quality_excess_repetition=-0.5,
        w_quality_alternation=0.3,

        # Structural
        w_dominant_near_cadence=1.5,    # ii-V-I cadential closure = very jazz
        w_tonic_at_start=1.0,
        w_open_phrase_ending=-0.3,      # jazz often leaves phrases open (elision)

        # Special roles
        w_tritone_sub=1.5,              # tritone subs = jazz hallmark
        w_secondary_dom=1.2,            # secondary dominants = jazz
        w_chromatic_med=0.6,
        w_borrowed=0.4,
        w_neapolitan=0.5,

        # Transition matrix
        w_transition_matrix=1.5,        # transitions matter a lot in jazz
    ),
    phrase_length_beats=8,
    chromaticism_tolerance=0.75,        # jazz is very chromatic
    target_avg_stability=0.45,          # slightly below neutral (tension-oriented)
    tension_volatility=0.5,             # tension changes frequently (active harmony)
    preferred_root_moves=[5, 7, 1, 2],  # 5th motion dominant, stepwise approach
    home_quality_classes=["maj7", "min7", "dom7"],
)


# ─────────────────────────────────────────────────────────────────────────────
# PROGRESSIVE ROCK CONFIG
# ─────────────────────────────────────────────────────────────────────────────

PROG_ROCK_CONFIG = GenreConfig(
    name="prog_rock",
    description=(
        "Progressive rock: modal harmony, borrowed chords, chromatic mediants, "
        "sus tension/release, dramatic structural arrivals. "
        "Think: Yes, Genesis, King Crimson, Emerson Lake & Palmer, Tool."
    ),
    transitions=PROG_ROCK_TRANSITIONS,
    features=GenreFeatureWeights(
        # Tension features
        w_stability_at_boundary=1.5,    # prog loves dramatic arrivals at boundaries
        w_unresolved_tension=-0.3,      # prog tolerates some unresolved tension
        w_smooth_tension_arc=0.5,
        w_dramatic_tension_arc=1.5,     # prog LOVES dramatic tension spikes

        # Diatonic/chromatic balance
        w_diatonic_chord=1.0,           # prog is more diatonic than fusion
        w_chromatic_with_role=1.0,      # chromatic with purpose is great
        w_chromatic_no_role=-1.2,       # random chromaticism = bad in prog

        # Root movement
        w_fifth_motion=0.5,             # 5th motion exists but not dominant
        w_stepwise_motion=0.8,          # stepwise modal motion very common
        w_third_motion=2.0,             # chromatic mediant = prog FINGERPRINT
        w_tritone_motion_raw=-1.0,      # tritone motion = wrong genre feel

        # Repetition
        w_quality_repetition=1.2,       # modal ostinatos are prog hallmark
        w_quality_excess_repetition=-0.8,
        w_quality_alternation=1.0,      # i-bVII-i alternation = very prog

        # Structural
        w_dominant_near_cadence=0.0,    # prog AVOIDS functional cadences
        w_tonic_at_start=1.5,           # strong tonic establishment
        w_open_phrase_ending=0.3,       # prog likes open endings (modal)

        # Special roles
        w_tritone_sub=-1.0,             # tritone subs = wrong genre
        w_secondary_dom=-0.5,           # secondary doms feel too jazz
        w_chromatic_med=2.0,            # chromatic mediant = prog signature
        w_borrowed=1.5,                 # borrowed chords (bVII, bVI) = prog
        w_neapolitan=0.8,               # neapolitan ok (King Crimson)

        # Transition matrix
        w_transition_matrix=1.2,
    ),
    phrase_length_beats=8,
    chromaticism_tolerance=0.45,        # more diatonic than jazz
    target_avg_stability=0.55,          # slightly above neutral (modal stability)
    tension_volatility=0.6,             # tension changes dramatically but slowly
    preferred_root_moves=[3, 4, 2, 7],  # 3rd motion first (chromatic mediant)
    home_quality_classes=["min7", "maj_triad", "maj7"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Registry: look up genre by name
# ─────────────────────────────────────────────────────────────────────────────

GENRE_REGISTRY: Dict[str, GenreConfig] = {
    "fusion_jazz": FUSION_JAZZ_CONFIG,
    "prog_rock":   PROG_ROCK_CONFIG,
}

def get_genre(name: str) -> GenreConfig:
    if name not in GENRE_REGISTRY:
        raise ValueError(f"Unknown genre '{name}'. Available: {list(GENRE_REGISTRY)}")
    return GENRE_REGISTRY[name]