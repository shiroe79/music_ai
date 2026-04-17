"""
EDO pitch math and utilities.
Supports 12, 19 and any N-EDO (Equal Divisions of the Octave).

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

# Convert MIDI note number to pitch height (in 12-EDO steps).
    def _midi_to_h(self, midi):
        return midi  # In 12-EDO, MIDI note == height step


    """
        Convert a pitch height h to (MIDI note number, pitch bend value).
        For microtonal EDOs (e.g., 19-EDO), the bend value is calculated
        relative to the nearest semitone, within the pitch_bend_range.

        Returns:
              (midi_note, bend) where bend is in range [-8192, 8191].
        """

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

# Chord templates for 12-EDO (intervals in EDO steps)
def chord_templates_12():
    return {
        "maj": [0, 4, 7],
        "min": [0, 3, 7],
        "dim": [0, 3, 6],
        "aug": [0, 4, 8],
        "7":   [0, 4, 7, 10],
        "maj7": [0, 4, 7, 11],
        "min7": [0, 3, 7, 10],
    }

# Chord templates for 19-EDO (intervals in EDO steps)
def chord_templates_19():
    return {
        "maj": [0, 6, 11],  # c e and g
        "min": [0, 5, 11],  # c eb and g ...
        "dim": [0, 5, 10],  
        "aug": [0, 6, 12],  
        "7":   [0, 6, 11, 17], 
        "maj7": [0, 6, 11, 18], 
        "min7": [0, 5, 11, 17], 
    }

def get_chord_templates(edo: EDOConfig):
    if edo.N == 12:
        return chord_templates_12()
    elif edo.N == 19:
        return chord_templates_19()
    else:
        # approximate using cents ratios to find step counts for major third, minor third, perfect fifth, etc.
        s = edo.N
        maj3 = round(s * 386 / 1200)
        min3 = round(s * 316 / 1200)
        p5   = round(s * 702 / 1200)
        min7 = round(s * 996 / 1200)
        maj7 = round(s * 1088 / 1200)
        return {
            "maj":  [0, maj3, p5],
            "min":  [0, min3, p5],
            "dom7": [0, maj3, p5, min7],
            "maj7": [0, maj3, p5, maj7],
            "min7": [0, min3, p5, min7],
        }



# 1. pitch_class(h)
# Use Case: Identifying a step/note's name (like "C" or "G").

# 12-EDO example
# Step 2 = D, Step 14 = D (one octave higher), Step 26 = D (two octaves higher)

print(EDO_12.pitch_class(2))   # Output: 2
print(EDO_12.pitch_class(14))  # Output: 2
print(EDO_12.pitch_class(26))  # Output: 2 (All are "D")

# 2. cents(h)
# Use Case: Checking the "ruler" position of a note to compare it against other tuning systems.
# Compare a "Major Third" (Step 4 in 12-EDO vs Step 6 in 19-EDO)

print(EDO_12.cents(4))  # Output: 400.0 (Standard Third)
print(EDO_19.cents(6))  # Output: 378.947 ...

# 3. freq(h)
# Use Case: Setting the actual vibration speed for a digital synthesizer oscillator.
# Calculate frequency for Middle C (if h=60 is C4)

print(EDO_12.freq(60))  # Output: 261.63 Hz


# 4. to_midi_and_bend(h)
# Use Case: Sending instructions to a MIDI keyboard. If the note is microtonal (like in 19-EDO), it calculates how much to "bend" the pitch wheel automatically.

# Step 10 in 19-EDO doesn't exist on a piano
# It returns (MIDI note, Pitch Bend value)
print(EDO_19.to_midi_and_bend(10)) 
# Output: (6, 1293) -> "Play F#, but bend it up quite a bit"

# 5. interval_cents(h1, h2)
# Use Case: Measuring the "distance" of a melodic leap to see if it’s easy for a singer to hit.
# Distance from low C (h=36) to high G (h=67)
print(EDO_12.interval_cents(36, 67)) # Output: 3100.0 cents

# 6. chromatic_pc_distance(pc1, pc2)
# Use Case: Analysis of "Chord Voicing." It helps an algorithm decide if two notes are close together (consonant) or far apart (dissonant).

# Distance between C (0) and B (11)
# It finds the "shortcut" across the octave circle
print(EDO_12.chromatic_pc_distance(0, 11)) # Output: 1 (Because B is just 1 step below C)
