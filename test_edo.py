from edo import EDO_12, EDO_19, make_edo, get_chord_templates, get_major_scale_pcs

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


print(get_chord_templates(make_edo(12)))
print(get_chord_templates(make_edo(13)))


# Testing major scale pitch classes for different EDOs
print(get_major_scale_pcs(make_edo(12)))
print(get_major_scale_pcs(make_edo(19)))
print(get_major_scale_pcs(make_edo(31)))