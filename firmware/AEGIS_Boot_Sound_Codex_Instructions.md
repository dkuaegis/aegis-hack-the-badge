# AEGIS Hack The Badge — Boot Sound Implementation Instructions

## 1. Goal

Implement a short, cinematic boot sound for the AEGIS Hack The Badge device using the existing ESP32 buzzer.

The target feeling is:

- cinematic
- tactical / cyberpunk
- "system awakening" vibe
- short enough not to annoy users on every boot
- recognizable as an AEGIS-specific boot signature
- synchronized with the OLED boot sequence and, if available, the LED animation

Do **not** simply play a long melody copied from an existing song.  
The boot sound should feel like an original AEGIS device startup sound.

Target duration: **about 1.5–2.0 seconds**.

---

## 2. Assumptions

Assume the device uses:

- ESP32-S3
- 0.96" OLED display
- passive piezo buzzer or equivalent PWM-driven buzzer
- existing AEGIS UI system
- existing boot / home / missions / intel / status / game / complete / admin screens
- LED animation support if already present in the project

Before modifying code, inspect the repository and identify:

1. the buzzer pin definition
2. whether the buzzer is passive or active
3. the current PWM / tone helper implementation
4. the boot-screen initialization flow
5. the OLED boot logo rendering code
6. the LED animation controller, if present
7. whether startup is blocking or event-driven

Reuse existing abstractions where possible instead of introducing duplicate subsystems.

---

# 3. Primary Boot Sound

Implement the following as the default startup signature.

## Sequence

| Step | Note | Frequency | Duration |
|---|---:|---:|---:|
| 1 | A3 | 220 Hz | 180 ms |
| 2 | D4 | 294 Hz | 70 ms |
| 3 | F4 | 349 Hz | 70 ms |
| 4 | A4 | 440 Hz | 90 ms |
| 5 | D5 | 587 Hz | 70 ms |
| 6 | F5 | 698 Hz | 70 ms |
| 7 | A5 | 880 Hz | 100 ms |
| 8 | C6 | 1047 Hz | 100 ms |
| 9 | A5 | 880 Hz | 100 ms |
| pause | silence | — | 60 ms |
| 10 | D6 | 1175 Hz | 450 ms |

Conceptually, it should sound like:

```text
BOOM — da-da-da ↑ da-da-da ↑ — [silence] — BAAAAAM
```

The final note is the main impact point.

---

# 4. Sound Design Requirements

## 4.1 Timing

Do not insert unnecessary gaps between the ascending notes.

The sequence should feel continuous and accelerating.

The only intentional dramatic silence is:

```text
A5 -> 60 ms silence -> D6
```

This silence is important and must remain.

---

## 4.2 Final Note

The final `D6 / 1175 Hz` note should feel noticeably stronger than the previous notes.

If the current buzzer driver supports duty-cycle control, use a slightly stronger duty cycle for the final note.

Example idea:

```text
normal notes: 40–50% duty
final note:   55–65% duty
```

Do not exceed safe electrical limits.

If volume control is unavailable, keep the same duty cycle and rely only on note duration and synchronization for impact.

---

## 4.3 Optional Frequency Sweep

If the buzzer implementation allows smooth frequency changes without destabilizing the boot sequence, add a very short rising sweep immediately before the final silence.

Example:

```text
880 Hz -> 1100 Hz
duration: 80–120 ms
```

This is optional.

Only keep it if it sounds better on the real buzzer.

Do not make the total boot sound longer than roughly 2 seconds.

---

# 5. Recommended Code Structure

Do not place a large hard-coded sequence directly inside `setup()`.

Create or reuse a dedicated audio module.

Preferred structure:

```text
src/
  audio/
    boot_sound.cpp
    boot_sound.h
```

or fit it into the project's existing module layout if different.

Suggested API:

```cpp
void playBootSound();
```

If the project already has a generic sound system, prefer something like:

```cpp
struct ToneStep {
    uint16_t frequency;
    uint16_t durationMs;
};

void playToneSequence(const ToneStep* sequence, size_t count);
void playBootSound();
```

Use project naming conventions instead of blindly copying these names.

---

# 6. Tone Data

Prefer storing the note sequence as data rather than repetitive function calls.

Example representation:

```cpp
struct ToneStep {
    uint16_t frequency;
    uint16_t durationMs;
};

static constexpr ToneStep kBootSound[] = {
    {220, 180},
    {294, 70},
    {349, 70},
    {440, 90},
    {587, 70},
    {698, 70},
    {880, 100},
    {1047, 100},
    {880, 100},
    {0, 60},
    {1175, 450},
};
```

`frequency == 0` should represent silence if that matches the project's audio abstraction.

---

# 7. ESP32 PWM Implementation

Use the existing project implementation if one already exists.

If not, use the ESP32 LEDC / tone-compatible PWM API supported by the project's installed Arduino-ESP32 version.

Do **not** assume a particular LEDC API signature before checking the actual framework version.

The implementation must:

- initialize the buzzer once
- set the desired frequency
- stop output cleanly between notes where necessary
- ensure the buzzer is silent after playback finishes
- avoid leaving the PWM peripheral running audibly after boot

---

# 8. Boot Screen Synchronization

The sound must be synchronized with the AEGIS OLED startup animation.

Desired boot sequence:

```text
Power On

↓
OLED cleared

↓
AEGIS logo appears

↓
low A3 startup tone

↓
ascending boot notes

↓
brief silence

↓
final D6 impact

↓
boot logo / system state visually locks in

↓
transition to Home
```

The final `D6` should coincide with the strongest visual moment.

Recommended final visual state:

```text
AEGIS
SYSTEM ONLINE
```

or the existing AEGIS boot logo if the design intentionally contains no status text.

Do not add `Initializing...` if the current design has already removed that text.

---

# 9. LED Synchronization

If the board already has controllable LEDs, synchronize them with the boot sound.

Do not add a new LED subsystem if none exists.

Recommended behavior:

### Step 1 — A3

Turn on a small center / starting LED indication.

### Steps 2–9

Expand or sweep outward as pitch rises.

Conceptually:

```text
      *
     ***
    *****
   *******
```

or a left-to-right / right-to-left scanning effect depending on the existing hardware.

### Silence

Hold the LEDs briefly.

### Final D6

Flash / illuminate all LEDs simultaneously.

Then transition into the existing idle LED animation.

Avoid excessively rapid flashing.

---

# 10. Non-Blocking Considerations

Inspect the current boot architecture first.

If the existing boot animation is already synchronous and blocking, a simple blocking sound sequence is acceptable.

However, if the UI uses a state machine or event loop, do not introduce long `delay()` chains that freeze unrelated components.

In that case, implement the sound as a timed state machine.

Example concept:

```cpp
struct SoundPlayerState {
    size_t currentStep;
    uint32_t stepStartedAt;
    bool active;
};
```

The audio update can then run from the main loop.

Do not over-engineer this if the current boot sequence is intentionally blocking.

---

# 11. Sound Enable / Disable

Add a single configuration flag so the boot sound can easily be disabled during development or future releases.

Example:

```cpp
#define AEGIS_BOOT_SOUND_ENABLED 1
```

or preferably use the project's existing configuration system.

If disabled:

- boot should continue normally
- no timing-dependent UI bug should occur
- no buzzer output should be produced

---

# 12. Optional Sound Variants

Structure the implementation so alternate themes can be added later.

Potential future modes:

```text
CINEMATIC
TACTICAL
CYBERPUNK
SILENT
```

Do not build a full settings menu unless one already exists.

For this task, only the default cinematic boot sound must be active.

---

# 13. Startup UX Constraints

The boot sound must **not**:

- exceed ~2 seconds
- sound like a random Arduino tutorial melody
- resemble a ringtone
- repeatedly beep at the same pitch
- use a long recognizable copyrighted melody
- block the entire device for several seconds
- introduce OLED flicker
- interfere with button initialization
- prevent Wi-Fi / storage / mission-state initialization
- leave the buzzer active after boot

---

# 14. Interaction With Existing Completion Event

Do not modify the existing all-solved completion behavior unless required to avoid audio conflicts.

The project may already have a separate completion sequence involving:

```text
Congratulations!

AEGIS{PWN3D!}

You solved all problems XD
```

and the LED victory animation.

The boot sound should remain a distinct startup signature.

If a completion / victory sound already exists, do not reuse the exact same melody.

---

# 15. Priority Order

Implement in this order:

1. inspect existing buzzer implementation
2. create / clean up reusable tone-sequence abstraction if needed
3. implement the cinematic boot sequence
4. integrate it into the startup flow
5. synchronize final note with OLED boot impact
6. synchronize LEDs if available
7. add an enable/disable configuration flag
8. verify no audio continues after boot
9. verify boot remains stable across reset / cold boot

---

# 16. Hardware Test Checklist

Test on the actual badge hardware.

Verify:

- [ ] buzzer works immediately after power-on
- [ ] every intended pitch is distinguishable
- [ ] A3 does not become too quiet for the physical buzzer
- [ ] high notes do not sound painfully sharp
- [ ] final D6 has the strongest perceived impact
- [ ] 60 ms silence before D6 is audible as a dramatic pause
- [ ] OLED animation remains smooth
- [ ] LEDs remain synchronized
- [ ] buttons work after boot
- [ ] Wi-Fi / storage initialization still succeeds
- [ ] rebooting repeatedly does not break the PWM driver
- [ ] buzzer is completely silent after the sequence finishes
- [ ] entire startup sound remains near 2 seconds or less

---

# 17. Real-Hardware Tuning

The frequency response of cheap piezo buzzers varies significantly.

After implementation, tune using the physical badge rather than assuming the theoretical notes will sound perfect.

Allowed tuning range:

```text
frequency: ±5–10%
duration:  ±20–40 ms
```

If `A3 / 220 Hz` is too weak on the actual buzzer, raise it to approximately:

```text
247 Hz
262 Hz
294 Hz
```

but preserve the low-to-high progression.

If `D6 / 1175 Hz` is too harsh, reduce it slightly to approximately:

```text
1047–1100 Hz
```

The emotional progression is more important than exact music-theory correctness.

---

# 18. Acceptance Criteria

The implementation is complete when:

1. powering on or resetting the badge triggers the AEGIS boot sound exactly once
2. the sound lasts approximately 1.5–2.0 seconds
3. it clearly progresses from low pitch to high pitch
4. there is a deliberate short silence before the final impact tone
5. the final tone is synchronized with the strongest OLED boot visual
6. LEDs are synchronized if the project already supports them
7. disabling boot sound through configuration does not affect startup
8. buzzer output is fully stopped after the sequence
9. existing screens and application logic remain unchanged
10. code is organized according to the repository's existing architecture

---

# 19. Codex Implementation Instruction

Before writing code:

1. inspect the repository structure
2. locate all buzzer / PWM / tone-related code
3. locate boot-screen and UI state transitions
4. locate LED control code
5. identify the Arduino-ESP32 / PlatformIO framework version
6. adapt the implementation to the APIs actually available in the project

Do not replace working project abstractions unnecessarily.

After implementation:

1. build the project
2. fix all compile errors
3. check for warnings introduced by the change
4. summarize modified files
5. explain the boot timing flow
6. identify any values that should be tuned on real hardware
7. do not modify unrelated application behavior

---

## Final Target Experience

The intended user experience is:

```text
[device powers on]

low mechanical startup tone

        ↓

rapid cinematic pitch rise

        ↓

      silence

        ↓

   FINAL IMPACT

        ↓

        AEGIS
    SYSTEM ONLINE
```

The badge should feel less like an Arduino project starting up and more like a dedicated cyber-security device coming online.
