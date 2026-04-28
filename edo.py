"""
EDO pitch math and utilities.
Supports any N-EDO (Equal Divisions of the Octave).

This module provides:
- EDOConfig class: encapsulates EDO math, MIDI conversion, pitch bends.
- Chord template functions for 12-EDO, 19-EDO, and generic N-EDO.
"""
class EDOConfig:
    def __init__(self, N=12, base_midi=60, base_freq_hz=261.63, pitch_bend_range=2):
        self.N = N
        self.base_midi = base_midi
        self.base_freq_hz = base_freq_hz
        self.pitch_bend_range = pitch_bend_range

# Return pitch class (0..N-1) for a given pitch height h (in EDO steps).
    def pitch_class(self, h):
        return h % self.N

# Return cents value for a pitch height h.
    def cents(self, h):
        return 1200.0 * h / self.N

# Return frequency in Hz for a pitch height h.
    def freq(self, h):
        cents_offset = self.cents(h) - self.cents(self._midi_to_h(self.base_midi))
        return self.base_freq_hz * (2.0 ** (cents_offset / 1200.0))

# Convert MIDI note number to pitch height (in n-EDO steps).
    def _midi_to_h(self, midi):
        return int(round(midi * self.N / 12))

    def to_midi_and_bend(self, h):
        c = 1200.0 * h / self.N
        midi_float = c / 100.0
        midi_note = round(midi_float)
        midi_note = max(0, min(127, midi_note))
        residual_cents = (midi_float - midi_note) * 100.0
        bend = int(residual_cents / (self.pitch_bend_range * 100.0) * 8191)
        bend = max(-8192, min(8191, bend))
        return midi_note, bend

    # Interval distance calculation in cents and circular pitch-class distance in EDO steps
    def interval_cents(self, h1, h2):
        return abs(self.cents(h2) - self.cents(h1))

    # Circular pitch-class distance in EDO steps
    def chromatic_pc_distance(self, pc1, pc2):
        diff = abs(pc1 - pc2) % self.N
        return min(diff, self.N - diff)

# Preset EDO configs
EDO_12 = EDOConfig(N=12)
EDO_19 = EDOConfig(N=19, pitch_bend_range=2)

# Function for custom of n steps EDOs
def make_edo(n):
    return EDOConfig(N=n)

def get_chord_templates(edo: EDOConfig):
    # approximate using cents ratios to find step counts for major third, minor third, perfect fifth, etc.
    s = edo.N
    # Common interval approximations in cents
    min2  = round(s * 100 / 1200)   # minor 2nd
    maj2  = round(s * 200 / 1200)   # major 2nd
    min3  = round(s * 316 / 1200)   # minor 3rd
    maj3  = round(s * 386 / 1200)   # major 3rd
    p4    = round(s * 498 / 1200)   # perfect 4th
    aug4  = round(s * 590 / 1200)   # augmented 4th / tritone
    p5    = round(s * 702 / 1200)   # perfect 5th
    aug5  = round(s * 814 / 1200)   # augmented 5th
    min6  = round(s * 814 / 1200)   # minor 6th
    maj6  = round(s * 884 / 1200)   # major 6th
    min7  = round(s * 996 / 1200)   # minor 7th
    maj7  = round(s * 1088 / 1200)  # major 7th

    return {
        # Triads
        "maj":    [0, maj3, p5],
        "min":    [0, min3, p5],
        "dim":    [0, min3, p5 - min2],      # diminished 5th
        "aug":    [0, maj3, aug5],
        "sus2":   [0, maj2, p5],
        "sus4":   [0, p4,   p5],
        "pow":    [0, p5],                   # power chord (root + 5th)

        # 7ths
        "maj7":   [0, maj3, p5, maj7],
        "min7":   [0, min3, p5, min7],
        "dom7":   [0, maj3, p5, min7],
        "minmaj7":[0, min3, p5, maj7],
        "hdim":   [0, min3, p5 - min2, min7],   # half-diminished (m7b5)
        "dim7":   [0, min3, p5 - min2, maj6],   # fully diminished 7

        # Extended
        "dom9":   [0, maj3, p5, min7, maj2],
        "dom13":  [0, maj3, p5, min7, maj2, maj6],
        "min9":   [0, min3, p5, min7, maj2],
        "min11":  [0, min3, p5, min7, maj2, p4],
        "maj9":   [0, maj3, p5, maj7, maj2],

        # Altered / Jazz
        "alt":      [0, min3, aug4, min6, min7],     # altered dominant (super-locrian)
        "lyd_dom":  [0, maj3, aug4, p5, min7],       # lydian dominant (#11)
        "quartal":  [0, p4, p5 + min2, p5 + maj2],   # quartal voicing example
    }

def get_major_scale_pcs(edo: EDOConfig) -> list[int]:
    """
    Return the pitch classes (0..N-1) of the major scale for this EDO,starting at tonic=0.
    """
    # Cents values for major scale degrees (1 to 7, relative to tonic)
    cents_offsets = [0, 200, 400, 500, 700, 900, 1100]
    steps = [round(edo.N * cents / 1200) % edo.N for cents in cents_offsets]
    return sorted(set(steps))