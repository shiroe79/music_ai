from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from tonal_abstraction import TonalFunction
from genre_config import GenreConfig

# Score result container
@dataclass
class ChordScore:
    """Score breakdown for a single chord in the sequence."""
    index: int
    tf: TonalFunction
    transition_score: float       # from transition matrix (pair with previous)
    feature_scores: Dict[str, float]  # per-feature contributions
    total: float                  # sum of all contributions for this chord

@dataclass
class ProgressionScore:
    """Full score result for a chord progression."""
    total_score: float            # overall score (higher = better genre match)
    normalized_score: float       # total / n_chords (comparable across lengths)
    chord_scores: List[ChordScore]
    feature_totals: Dict[str, float]  # summed per feature across all chords
    genre_name: str
    verdict: str                  # human-readable summary


# Individual feature scorers
def _score_transition(tf: TonalFunction, config: GenreConfig) -> float:
    """Look up (prev_quality_class → quality_class) in the transition matrix."""
    if tf.prev_quality_class is None:
        return 0.0
    key = (tf.prev_quality_class, tf.quality_class)
    raw = config.transitions.get(key, 0.0)
    return raw * config.features.w_transition_matrix

def _score_chromatic_role(tf: TonalFunction, config: GenreConfig) -> float:
    """Reward or penalize based on the chromatic role of this chord."""
    fw = config.features
    role = tf.chromatic_role

    if tf.diatonic:
        return fw.w_diatonic_chord

    if role is None:
        # Chromatic but no recognized role = random chromaticism
        return fw.w_chromatic_no_role

    # Has a recognized role
    base = fw.w_chromatic_with_role
    bonus = {
        "tritone_sub":   fw.w_tritone_sub,
        "secondary_dom": fw.w_secondary_dom,
        "chromatic_med": fw.w_chromatic_med,
        "borrowed":      fw.w_borrowed,
        "neapolitan":    fw.w_neapolitan,
        "augmented_6th": fw.w_chromatic_with_role * 0.5,
        "modal_color":   fw.w_chromatic_with_role * 0.3,
    }.get(role, 0.0)
    return base + bonus


def _score_root_movement(tf: TonalFunction, config: GenreConfig) -> float:
    """Score the size of the root movement from the previous chord."""
    if tf.root_move_semitones is None:
        return 0.0
    mv = tf.root_move_semitones
    fw = config.features

    score = 0.0
    if mv in (5, 7):   # perfect 4th or 5th
        score += fw.w_fifth_motion
    if mv in (1, 2):   # semitone or whole-step
        score += fw.w_stepwise_motion
    if mv in (3, 4):   # minor or major 3rd (chromatic mediant)
        score += fw.w_third_motion
    if mv == 6:        # tritone
        # Only bad if it's NOT a tritone sub
        if tf.chromatic_role != "tritone_sub":
            score += fw.w_tritone_motion_raw
    return score


def _score_stability_at_position(
        tf: TonalFunction, 
        position: int,
        n_total: int, 
        phrase_len: int,
        config: GenreConfig) -> float:
    """
    Reward stable chords at phrase starts/ends.
    Position within phrase is computed from global position.
    """
    fw = config.features
    score = 0.0
    pos_in_phrase = position % phrase_len
    is_phrase_start = (pos_in_phrase == 0)
    is_phrase_end   = (pos_in_phrase == phrase_len - 1)
    is_last         = (position == n_total - 1)

    if is_phrase_start:
        score += fw.w_tonic_at_start * tf.stability
    if is_phrase_end or is_last:
        if tf.pull > 0.6:
            # High-pull chord at phrase end = open ending
            score += fw.w_open_phrase_ending
        else:
            score += fw.w_stability_at_boundary * tf.stability
        # Dominant near cadence
        if tf.quality_class in ("dom7", "dom7_alt") and (is_phrase_end or is_last):
            score += fw.w_dominant_near_cadence
    return score


def _score_unresolved_tension(
        tf: TonalFunction, 
        next_tf: Optional[TonalFunction],
        config: GenreConfig) -> float:
    """
    Penalize if a high-pull chord is followed by another high-pull chord
    (tension piles up without release).
    """
    if next_tf is None:
        return 0.0
    if tf.pull > 0.7 and next_tf.pull > 0.7:
        return config.features.w_unresolved_tension
    return 0.0


def _score_tension_arc(tfs: List[TonalFunction], config: GenreConfig) -> float:
    """
    Score the overall tension arc of the progression.
    - Smooth arc: tension rises and falls gradually (good for jazz)
    - Dramatic arc: tension has sharp spikes (good for prog)
    Measured by the standard deviation of sequential stability changes.
    """
    if len(tfs) < 3:
        return 0.0
    stabilities = [tf.stability for tf in tfs]
    deltas = [ abs(stabilities[i+1] - stabilities[i]) for i in range(len(stabilities)-1)]

    avg_delta = sum(deltas) / len(deltas)
    fw = config.features

    # Smooth arc: prefer low deltas
    smooth_score = fw.w_smooth_tension_arc * max(0, 1.0 - avg_delta * 3)
    # Dramatic arc: prefer high deltas
    dramatic_score = fw.w_dramatic_tension_arc * min(1.0, avg_delta * 3)

    return smooth_score + dramatic_score


def _score_repetition(
        tfs: List[TonalFunction], 
        index: int, 
        config: GenreConfig) -> float:
    """
    Score quality-class repetition patterns.
    Rewards modal vamps (same quality repeated) or alternation (ABAB).
    Penalizes excess repetition (>3 of the same in a row).
    """
    fw = config.features
    if index < 1:
        return 0.0

    score = 0.0
    current_qc = tfs[index].quality_class
    prev_qc    = tfs[index-1].quality_class

    # Same quality repeated
    if current_qc == prev_qc:
        score += fw.w_quality_repetition
        # Check for excess (3+ in a row)
        if index >= 2 and tfs[index-2].quality_class == current_qc:
            if index >= 3 and tfs[index-3].quality_class == current_qc:
                score += fw.w_quality_excess_repetition

    # Alternation: ABAB pattern
    if index >= 3:
        if (tfs[index].quality_class   == tfs[index-2].quality_class and
            tfs[index-1].quality_class == tfs[index-3].quality_class and
            tfs[index].quality_class   != tfs[index-1].quality_class):
            score += fw.w_quality_alternation

    return score


# Main scoring function
def score_progression(
        tfs: List[TonalFunction],
        config: GenreConfig,
        phrase_length: Optional[int] = None) -> ProgressionScore:
    """
    Score a TonalFunction sequence against a GenreConfig.

    Args:
        tfs:           List of TonalFunction (from abstract_progression)
        config:        GenreConfig (FUSION_JAZZ_CONFIG or PROG_ROCK_CONFIG)
        phrase_length: Override phrase length (default: config.phrase_length_beats)

    Returns:
        ProgressionScore with total, per-chord, and per-feature breakdowns.
    """
    if not tfs:
        return ProgressionScore(0, 0, [], {}, config.name, "Empty progression")

    phrase_len = phrase_length or config.phrase_length_beats
    n = len(tfs)
    chord_scores: List[ChordScore] = []
    feature_totals: Dict[str, float] = {}

    # Arc-level score (whole-progression features)
    arc_score = _score_tension_arc(tfs, config)

    for i, tf in enumerate(tfs):
        next_tf = tfs[i+1] if i < n-1 else None
        feat: Dict[str, float] = {}

        feat["transition"]       = _score_transition(tf, config)
        feat["chromatic_role"]   = _score_chromatic_role(tf, config)
        feat["root_movement"]    = _score_root_movement(tf, config)
        feat["position"]         = _score_stability_at_position(tf, i, n, phrase_len, config)
        feat["unresolved"]       = _score_unresolved_tension(tf, next_tf, config)
        feat["repetition"]       = _score_repetition(tfs, i, config)
        feat["arc"]              = arc_score / n   # distribute arc score evenly

        chord_total = sum(feat.values())
        chord_scores.append(ChordScore(
            index=i, tf=tf,
            transition_score=feat["transition"],
            feature_scores=feat,
            total=chord_total,
        ))

        for k, v in feat.items():
            feature_totals[k] = feature_totals.get(k, 0.0) + v

    total_score = sum(cs.total for cs in chord_scores)
    normalized  = total_score / n

    # Verdict
    if normalized > 2.5:
        verdict = f"Excellent match for {config.name}"
    elif normalized > 1.5:
        verdict = f"Good match for {config.name}"
    elif normalized > 0.5:
        verdict = f"Moderate match for {config.name}"
    elif normalized > -0.5:
        verdict = f"Weak match for {config.name}"
    else:
        verdict = f"Poor match — not idiomatic for {config.name}"

    return ProgressionScore(
        total_score=round(total_score, 3),
        normalized_score=round(normalized, 3),
        chord_scores=chord_scores,
        feature_totals={k: round(v, 3) for k, v in feature_totals.items()},
        genre_name=config.name,
        verdict=verdict,
    )



# Explain / pretty-print
CHORD_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def _chord_label(root_pc: int, quality: str) -> str:
    return f"{CHORD_NAMES[root_pc % 12]}{quality}"

def explain_score(
        result: ProgressionScore,
        chords: Optional[List[Tuple[int,str]]] = None) -> None:
    """
    Print a human-readable breakdown of a ProgressionScore.

    Args:
        result: ProgressionScore from score_progression()
        chords: Optional list of (root_pc, quality) to show chord names
    """
    print(f"\n{'═'*60}")
    print(f"  Genre:  {result.genre_name}")
    print(f"  Score:  {result.total_score:.2f}  "
          f"(normalized: {result.normalized_score:.2f} per chord)")
    print(f"  Verdict: {result.verdict}")
    print(f"{'─'*60}")
    print(f"  Feature totals:")
    for feat, val in sorted(result.feature_totals.items(),
                            key=lambda x: -abs(x[1])):
        bar = '█' * int(abs(val) * 2) if val >= 0 else '░' * int(abs(val) * 2)
        sign = '+' if val >= 0 else '-'
        print(f"    {feat:<20s}  {sign}{abs(val):.2f}  {bar}")
    print(f"{'─'*60}")
    print(f"  Per-chord breakdown:")
    for cs in result.chord_scores:
        if chords and cs.index < len(chords):
            # label = str(cs.tf.quality_class)
            label = _chord_label(*chords[cs.index]) #-- only for 12- EDO
        else:
            label = str(cs.tf.quality_class)
        role  = f"[{cs.tf.chromatic_role}]" if cs.tf.chromatic_role else ""
        deg   = f"deg{cs.tf.degree}" if cs.tf.degree else "chrom"
        sign  = '+' if cs.total >= 0 else ''
        print(f"    [{cs.index}] {label:<12s} {deg:<7s} {role:<16s}"
              f" score={sign}{cs.total:.2f}")
    print(f"{'═'*60}\n")


def compare_genres(
        tfs: List[TonalFunction],
        configs: List[GenreConfig],
        chords: Optional[List[Tuple[int,str]]] = None) -> None:
    """
    Score the same progression against multiple genre configs and compare.
    Useful for understanding how genre-specific a progression is.
    """
    results = [(cfg.name, score_progression(tfs, cfg)) for cfg in configs]
    results.sort(key=lambda x: -x[1].normalized_score)

    print(f"\n{'═'*60}")
    print(f"  Genre comparison  ({len(tfs)} chords)")
    print(f"{'─'*60}")
    for name, res in results:
        bar_len = max(0, int((res.normalized_score + 2) * 6))
        bar = '█' * bar_len
        print(f"  {name:<20s}  {res.normalized_score:+.2f}  {bar}")
        print(f"    → {res.verdict}")
    print(f"{'═'*60}")
    if chords:
        # print(f"  Progression: {' → '.join(str(c[1]) for c in chords)}")
        print(f"  Progression: {' → '.join(_chord_label(*c) for c in chords)}")  #-- only for 12-EDO