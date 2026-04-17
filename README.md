# EDO Pitch Utilities for Symbolic Music Generation

This module provides pitch math and MIDI conversion for **any Equal Division of the Octave (EDO)**. It supports standard 12‑EDO, microtonal 19‑EDO, and N‑EDO via cent‑based approximation.

## Core Concepts

- **N**: number of equal steps per octave (e.g., 12, 19, 31, 53).
- **Pitch height (h)**: integer counting steps from an arbitrary zero (like MIDI note numbers for 12‑EDO).
- **Pitch class**: `h mod N` — identifies the note within an octave.(like 0 = C)
- **Cents**: `1200 * h / N` — absolute pitch in cents (1200 cents = 1 octave).

## Why Pitch Bends for Non‑12‑EDO?

- In **12‑EDO**, each step = 100 cents → MIDI notes align perfectly, no bend needed.
- In **19‑EDO**, each step ≈ 63.16 cents → the pitch falls between standard semitones.  
  We send the **nearest MIDI note** plus a **pitch bend** (up to ±200 cents by default) to reach the exact microtonal frequency.

The `EDOConfig` class handles this conversion automatically via `to_midi_and_bend(h)`.

## EDOConfig Methods

| Method | Description | Example |
|--------|-------------|---------|
| `pitch_class(h)` | Pitch class (0..N-1) | `EDO_12.pitch_class(14)` → `2` (D) |
| `cents(h)` | Cents value | `EDO_19.cents(6)` → `378.9` (≈ microtonal third) |
| `freq(h)` | Frequency in Hz | `EDO_12.freq(60)` → `261.63` |
| `to_midi_and_bend(h)` | (MIDI note, bend) | `EDO_19.to_midi_and_bend(10)` → `(66, 2601)` |
| `interval_cents(h1, h2)` | Absolute interval in cents | `EDO_12.interval_cents(36,67)` → `3100.0` |
| `chromatic_pc_distance(pc1, pc2)` | Minimum steps around the circle | `EDO_12.chromatic_pc_distance(0,11)` → `1` |

## Chord Templates for Arbitrary EDO

The function `get_chord_templates(edo)` returns a dictionary of chord interval patterns (in EDO steps). For N=12 or 19, it uses hand‑tuned templates. For any other N, it approximates intervals using **[cents values of pure just intervals](https://en.wikipedia.org/wiki/Interval_(music)#Size_of_intervals_used_in_different_tuning_systems)**:

| Interval | Just Ratio | Cents | Approx in N‑EDO |
|----------|------------|-------|------------------|
| Major third | 5:4 | 386 | `round(N * 386/1200)` |
| Minor third | 6:5 | 316 | `round(N * 316/1200)` |
| Perfect fifth | 3:2 | 702 | `round(N * 702/1200)` |
| Minor seventh | 16:9 | 996 | `round(N * 996/1200)` |
| Major seventh | 15:8 | 1088 | `round(N * 1088/1200)` |

These numbers are **musically familiar intervals expressed in cents, independent of any EDO**. Scaling them to your EDO step size gives the closest available approximation.

## Usage Examples

```python
from edo import EDO_12, EDO_19, make_edo, get_chord_templates

# 12-EDO
print(EDO_12.pitch_class(14))        # 2 (D)
print(EDO_12.cents(4))               # 400.0 (major third)
print(EDO_12.to_midi_and_bend(60))   # (60, 0)  – no bend

# 19-EDO
print(EDO_19.pitch_class(19))        # 0 (octave)
print(EDO_19.cents(6))               # 378.947...
midi, bend = EDO_19.to_midi_and_bend(10)
print(f"MIDI {midi}, bend {bend}")   # e.g., MIDI 66, bend 2601

# Custom 31-EDO
edo31 = make_edo(31)
print(edo31.cents(1))                # 38.71 cents per step
templates = get_chord_templates(edo31)
print(templates["maj"])              # e.g., [0, 10, 18] (approx major third)