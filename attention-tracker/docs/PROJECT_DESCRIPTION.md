# EEG Attention Tracker — Project Description

**Status:** problem framing only (no implementation plan in this document)  
**Participant in current LYS sessions:** P33  
**Device:** Kernel Flow 2 (`nirs/flow2`, device name e.g. *Flow2 Danube 187 Hoppip*)

---

## 1. Project idea

Build software that estimates **whether a person was paying attention** during a recorded session, using **EEG** from a Kernel Flow 2 helmet together with a **rich event protocol** of what was happening at each moment (audio words, game commands, phase boundaries, etc.).

The project vision is a **program / pipeline** that, given a session’s neural recording + protocol (and optionally the stimulus audio), produces a engagement estimate for the main task at each moment.

---

## 2. Research question

**Can we tell, from 4-channel Kernel Flow EEG aligned to a detailed session protocol, when a participant is attending to the task versus disengaging — and how does that look across different task types (passive listening vs. interactive gameplay)?**

### What “attention” means here (working definition)

| Context | Rough meaning of “attending” |
|--------|--------------------------------|
| **Perceived speech (audiobook / podcast)** | Neural signal consistent with following the spoken stream (e.g. engagement-related band power, speech tracking / word-locked responses) rather than zoning out |
| **Zork (CLI adventure game)** | Neural (and protocol-linked) patterns consistent with reading game text, deciding, and acting — vs. idle, distracted, or disengaged typing |

Important constraint for current data: **there is little or no independent behavioral ground truth** for “was attending?” during the main task (no comprehension quizzes, no attend/ignore conditions, no continuous self-report). So for existing sessions the scientific product is best framed as a **descriptive engagement / attention-related index from the neural signal**, not yet a fully validated binary classifier.

---

## 3. Hardware and signal

### Kernel Flow 2 (what we actually use)

The Flow 2 is a **hybrid** device:

| Stream | Role in this project |
|--------|----------------------|
| **EEG (electrical)** | Primary focus of the attention tracker |
| **fNIRS (optical)** | Same sessions may also exist in source `.snirf` files; **not required for the current EEG goal**, but available later if both modalities are desired |

### EEG as stored in LYS `.npz` files

From the files in this repo:

- **Channels (4):** `AF4`, `AF3`, `FCz`, `CPz`
- **Sampling rate:** ~500 Hz (stored in `fs_hz`)
- **Arrays:** continuous `data` (samples × 4), `time`, per-sample `impedance`, plus metadata (`subject_id`, `study_id`, `source_snirf`, measurement date/time)
- **No separate hardware trigger channel** in the NPZ — alignment to events relies on **shared timestamps** between the EEG time base and the protocol log
- **Units / gain** are not clearly documented in the NPZ; analysis should prefer **within-recording relative** thresholds rather than textbook µV cutoffs unless calibration is confirmed later

### Practical consequences of only 4 channels

- Sites are useful for **frontal / midline** markers often linked to arousal, control, and some auditory/ERP-style effects  
- **Full-scalp ICA** (classic multi-channel artifact cleaning) is **not well supported** with only 4 sensors  
- Spatial resolution is limited; claims must stay honest about what 4 dry electrodes can and cannot resolve  

---

## 4. Study paradigms (LYS data)

Both paradigms share a similar **session skeleton**, then diverge on the main task.

### Shared structure (typical)

1. **Helmet setup / Kernel phases** (startup, lasers, tuning, ready, recording start)  
2. **Baseline** — ~60 s “nothing happens” (quiet resting-like period)  
3. **Functional localizer** — cued finger-tapping (left / right) alternating with rest blocks (protocol: 3 repeats, 15 s cue / 15 s rest style blocks, 6 cues total in the logs examined)  
4. **Main task** — either passive speech listening **or** interactive Zork  
5. **End** — quit, stop recording, lasers off  

The localizer is important scientifically: it is a period where we **know** the participant is doing something active vs. resting, so it can sanity-check that the 4-channel EEG carries real task-related signal (e.g. movement / engagement-related modulation) before interpreting the harder “attention during the main task” question.

---

### 4.1 Perceived speech (passive listening)

**Experiment name in logs:** `perceived_speech`

**What the participant does**

- Sit with the helmet  
- Baseline → finger-tapping localizer  
- Listen to an audio chunk (audiobook or podcast segment), generally on the order of minutes (design upper bound mentioned: up to ~20 min; individual chunks vary)  
- No requirement in the current design for button presses or comprehension checks during listening  

**What the protocol records**

- Phase boundaries: baseline, functional localizer cues/rests, `task_start`, quit/end  
- **`perceived_word` events** — each spoken word with `start_ms` / `end_ms` (relative to audio) and a confidence score (forced alignment)  
- Occasional `escape_overlay` events (status / UI-related; whether they are visually distracting should be checked against the UI design)  
- Session notes (e.g. cough during session)

**Stimulus materials (when present)**

- Audio file (`.wav`)  
- Word / transcript timing (in the session log and/or a separate transcript `.json`)  

**Example sessions in this repo**

| Session folder | Content (summary) | EEG file | Protocol / stimulus |
|----------------|-------------------|----------|---------------------|
| `data/lys_data/perceived_speech/audio_movie/` | Brandon Sanderson, *The Way of Kings* chunk (~5.5 min audio); session 55; notes: coughed | `EEG_RAW_...95afb90.npz` (~281k samples, ~9.4 min @ ~500 Hz) | Full `.jsonl` log + `.wav` (849 `perceived_word` events in the log) |
| `data/lys_data/perceived_speech/Bill_Ackman_part2/` | Lex Fridman podcast segment (Bill Ackman) | `EEG_RAW_...f1f9380.npz` (~636k samples, ~21 min) | `.wav` + word-timed transcript `.json` (thousands of word entries); **no full session `.jsonl` in folder** |

**Attention-relevant framing**

- Task is **passive**: attention is covert  
- Protocol gives **when each word occurred**, which enables word-locked / speech-tracking style analyses later  
- **No labels** in-file for “attending vs not” during the audio  

---

### 4.2 Zork task (interactive CLI game)

**Experiment name in logs:** `zork_task`  
**Study id naming in files:** e.g. `zorkdork`

**What the participant does**

- Same baseline + functional localizer skeleton  
- Plays **Zork** (Infocom / Frotz-style CLI adventure) on a laptop: read text, type commands, explore rooms, manage inventory/score  
- Operator note for design evolution: **newer protocol may force a pause (~10 s) before each command** so players cannot spam input; the session file currently in the repo **may predate** that constraint (commands appear with variable decision times, some short)

**What the protocol records (richer behavioral structure than pure listening)**

From the example log (`zork_task_log_20260629_153057.jsonl`, session 30, P33):

- Same Kernel / baseline / localizer events as speech  
- `task_start` / `game_start` (game id, world version, room, whether game was **resumed**)  
- `game_output` — text the player saw  
- `state_snapshot` — room, score, inventory, description  
- `user_command` — raw input, normalized verb/args, timing  
- `decision_time` — ms spent before a command  
- `room_transition` — movement through the world  
- `escape_overlay`, quit, end recording  

**Example session in this repo**

| Session folder | Content (summary) | EEG file | Protocol |
|----------------|-------------------|----------|----------|
| `data/lys_data/zork_task/` | Zork gameplay after baseline+localizer; game **resumed** mid-progress (e.g. turn ~228, living room, score 103); ~17+ min of play until ctrl_q | `EEG_RAW_...bb05ebe.npz` (~644k samples, ~21.5 min) | Full `.jsonl` log |

**Attention-relevant framing**

- Task is **active and self-paced**: attention fluctuates with reading, planning, typing, waiting for output  
- Protocol gives **natural markers** (commands, decision latency, room changes, text onsets) that can be used as structure for neural analysis  
- Still **not** a designed attend/ignore experiment; “attention” remains partly inferred unless future probes or the forced pre-command pause are used as design features  

---

## 5. Data inventory (this repository)

### 5.1 LYS primary data (`data/lys_data/`)

```
data/lys_data/
  perceived_speech/
    audio_movie/          # Way of Kings + EEG + full session log
    Bill_Ackman_part2/    # Podcast audio + EEG + transcript JSON (no jsonl log yet)
  zork_task/              # Zork EEG + full session log
```

Common pairing for analysis:

| Asset | Role |
|-------|------|
| `EEG_RAW_study-...npz` | Continuous 4-ch EEG + time + impedance + metadata |
| `*_log_*.jsonl` | Timestamped protocol (phases, words, commands, …) |
| `.wav` | Acoustic stimulus (speech paradigms) |
| transcript / word JSON | Word timings if not fully in the log |

Source sessions also reference **`.snirf`** (full Kernel measurement including optical); those files are not necessarily checked into this repo but are named in EEG metadata.

### 5.2 External / comparison datasets (`data/other_dataset/`)

Present for method development, baselines, or literature-aligned validation — **not** LYS Kernel sessions:

- **SPIS Resting-State Dataset** — pre-SART eyes open/closed style EEG (multi-subject `.mat`)  
- **Sustained attention driving task** — multi-channel EEG during a driving / attention paradigm (EEGLAB `.set` / `.fdt`, plus description PDF)

These support a broader “attention EEG” research program but are a different device, montage, and experimental design from Flow 2.

### 5.3 Code / project tree (current)

```
attention-tracker/     # intended analysis package (mostly scaffold)
  docs/                # this description lives here
  src/common|psd|trf/  # placeholders for shared tools, band-power, TRF-style work
  outputs/             # mirrored result slots for each dataset (psd / trf notes & plots)
  notebooks/, scripts/, tests/
old_stuff/             # earlier band-power / sliding-window experiments
```

---

## 6. Goal

### Primary goal

**Deliver a working program (analysis pipeline) that, for a Kernel Flow session, estimates attention / engagement during the main task from EEG (+ protocol, + audio when available).**

Concretely, for a given session the desired output is along the lines of:

- A **time-resolved score or profile** over the main task (listening window or gameplay window)  
- Grounded in **protocol timestamps** (phases, words, commands)  
- Documented as **what the score means** (descriptive neural index vs. validated “attending yes/no”)  

### Supporting goals

1. **Sanity and quality** — use baseline and functional localizer to show the recording is usable and that expected task-related EEG effects appear when behavior is known.  
2. **Two task families under one roof** — same hardware and shared session skeleton; task-specific interpretation for **speech** vs **Zork**.  
3. **Honest science under missing labels** — with current data, prioritize a **descriptive engagement index**; treat supervised “attention classifier” as a later goal once behavioral probes exist.  
4. **Optional audio path** — for speech, acoustic envelope / word onsets unlock speech-tracking style measures that are strongly motivated in the auditory attention literature.  
5. **Extensibility** — more participants, more sessions, optional fNIRS, optional comparison datasets.

### Explicit non-goals (for now)

- Claiming a clinically or product-validated binary “attentive / not attentive” detector from the **current unlabeled** main-task segments alone  
- Full fNIRS pipeline as a dependency of the first EEG deliverable  
- Replacing the experimental portal / Kernel acquisition stack (this project **consumes** exports + logs)

---

## 7. Open constraints and known issues (from data + prior discussion)

These shape the problem; they are not a solution plan.

| Issue | Why it matters |
|-------|----------------|
| **No main-task attention labels** on existing speech (and limited labeling story for Zork) | Limits validation; index ≠ proven classifier |
| **4 channels only** | Constrains artifact methods and spatial claims |
| **No hardware triggers in NPZ** | Alignment depends on log ↔ EEG timestamps |
| **Artifacts** (e.g. cough noted in speech session; large shared spikes possible) | Must be detectable from signal + notes |
| **Zork protocol may have changed** (forced pause before commands) | Older logs may not match current design |
| **Incomplete pairing** (e.g. Bill Ackman EEG without full jsonl in folder) | Some sessions need missing logs/files before full analysis |
| **UI events** (`escape_overlay`) | May or may not be visual distractors |
| **Units/gain unclear** | Prefer relative, within-session features |

---

## 8. Success criteria (high level)

The project is succeeding when:

1. A new researcher can read **this document** and understand the studies, data, and goal without the prior chat history.  
2. Sessions can be described as: **device + participant + phases + main task + available files**.  
3. The eventual software answers, for a session: **“when during the main task does the EEG look more vs less engagement-like?”** with transparent methods and limitations.  
4. Speech and Zork are both in scope, with shared acquisition logic and task-specific interpretation.  
5. Future protocol improvements (comprehension probes, target words, enforced pauses) are recognized as the path to **supervised validation**.

---

## 9. One-paragraph summary

This project uses **Kernel Flow 2 four-channel EEG** and **timestamped experiment logs** from LYS sessions (participant P33 and future subjects) to estimate **attention / engagement** during two paradigms that share a baseline and finger-tapping localizer: **passive listening to speech** (word-aligned audiobook/podcast) and **interactive Zork play** (command- and state-rich CLI gameplay). The research goal is to turn continuous neural data plus protocol into a clear, time-resolved picture of whether the participant was engaged with the stimulus or task. Current main-task recordings largely **lack independent attention labels**, so the immediate scientific target is a **protocol-aligned descriptive engagement measure**, with a longer-term path toward a validated detector as behavioral probes and more data are added.

---

*Document purpose: shared problem statement only. Implementation and analysis plans will live in separate docs when we decide to write them.*
