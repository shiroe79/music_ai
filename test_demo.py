from edo import EDO_12
from tonal_abstraction import abstract_progression
from genre_config import FUSION_JAZZ_CONFIG, PROG_ROCK_CONFIG
from gttm_scorer import compare_genres, score_progression, explain_score

chords = [(0,'maj7'), (9,'min7'), (2,'min7'), (7,'dom7'), (0,'maj7')]
funcs  = abstract_progression(chords, tonic_pc=0, edo=EDO_12)
result = score_progression(funcs, FUSION_JAZZ_CONFIG)

print(result.total_score)
explain_score(result)


# ii - V - I in C
chords = [(2,'min7'), (7,'dom7'), (0,'maj7')]
funcs  = abstract_progression(chords, tonic_pc=0, edo=EDO_12)
compare_genres(funcs, [FUSION_JAZZ_CONFIG, PROG_ROCK_CONFIG], chords)


# Cmaj7 → G7 → Am7 → G7 → Dm7 → G7 → Cmaj7
# Pitch classes (12-EDO): C=0, G=7, A=9, D=2
chords = [
    (0, 'maj7'),   # Cmaj7
    (7, 'dom7'),   # G7
    (9, 'min7'),   # Am7
    (7, 'dom7'),   # G7
    (2, 'min7'),   # Dm7
    (7, 'dom7'),   # G7
    (0, 'maj7'),   # Cmaj7
]

funcs = abstract_progression(chords, tonic_pc=2, edo=EDO_12)

# Compare fusion jazz vs prog rock
compare_genres(funcs, [FUSION_JAZZ_CONFIG, PROG_ROCK_CONFIG], chords=chords)

#  This should be more to rock side
# C5 – G5 – A5 – F5  (power chords)
# Pitch classes: C=0, G=7, A=9, F=5
# Quality 'pow' = power chord (root + fifth, no third)
chords = [
    (0, 'pow'),   # C5
    (7, 'pow'),   # G5
    (9, 'pow'),   # A5
    (5, 'pow'),   # F5
]

funcs = abstract_progression(chords, tonic_pc=0, edo=EDO_12)  # key of C major
compare_genres(funcs, [FUSION_JAZZ_CONFIG, PROG_ROCK_CONFIG], chords=chords)

