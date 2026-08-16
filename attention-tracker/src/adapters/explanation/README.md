# Adapters

This folder is the **front door** of the pipeline. Everything downstream
(`clean`, `features`, `score`) only understands one object: `EEGSession`
from `src/common/session.py`. Adapters are the only place that know how
raw files are stored.

```text
LYS .npz  (+ optional .jsonl)
        │
        ▼
  adapters/lys.py   load_lys()
        │
        ▼
     EEGSession     4-ch EEG on a common time axis
        │
        ▼
  clean → features → score
```

Right now there is only one adapter: `lys.py`. Later, other datasets
(SPIS, driving-task EEGLAB, …) should grow their own files here and
**map into the same `EEGSession`**, not invent a second internal format.

## What `load_lys` actually uses

From the `.npz` it keeps:

| Field | Meaning |
|-------|---------|
| `data` | `(n_samples, 4)` EEG, reordered to `AF4, AF3, FCz, CPz` |
| `time` | seconds, one stamp per sample (starts near 0) |
| `fs_hz` | sampling rate (~500 Hz) |
| `channel_names` | must include the four LYS sites |
| `subject_id`, `study_id` | metadata |

From the `.jsonl` it keeps **only phase windows**:

- `baseline_start` / `baseline_end` → `phases["baseline"]`
- `functional_localizer_start` / `_end` → `phases["localizer"]`
- `task_start` plus `quit` or `end_experiment` → `phases["task"]`

Log timestamps are absolute. EEG `time` is relative. The adapter treats
`kernel_start_recording_result` as EEG t ≈ 0 and converts the phase
events onto that axis.

It **ignores** words, game commands, audio paths, and everything else
in the log. Those are still in the file — dump them with the script
below if you want to see them.

## Files you will see next to a session

| File | What it is |
|------|------------|
| `EEG_RAW_study-…npz` | Continuous 4-channel Kernel Flow EEG + impedance + metadata |
| `*_log_*.jsonl` | Timestamped protocol: header comments, then one JSON event per line |
| `.wav` / transcript `.json` | Stimulus (speech sessions). Not loaded by the adapter. |

Typical pairings in this repo:

- `data/lys_data/perceived_speech/audio_movie/` — EEG + full jsonl + wav
- `data/lys_data/perceived_speech/Bill_Ackman_part2/` — EEG + wav + transcript, **no jsonl**
- `data/lys_data/zork_task/` — EEG + full jsonl (game events)

## Dump script

Prints the raw `.npz` keys and the `.jsonl` event types, then shows what
`load_lys` turns them into.

From `attention-tracker/`:

```bash
source .venv/bin/activate
PYTHONPATH=src python src/adapters/explanation/dump_session.py

# one session folder, or a single file
PYTHONPATH=src python src/adapters/explanation/dump_session.py ../data/lys_data/zork_task
PYTHONPATH=src python src/adapters/explanation/dump_session.py ../data/lys_data/zork_task/EEG_RAW_study-zorkdork_sub-p33_desc-bb05ebe.npz

# more example events per type
PYTHONPATH=src python src/adapters/explanation/dump_session.py ../data/lys_data/zork_task --samples 3
```

No argument dumps every known LYS session under `data/lys_data/`.
