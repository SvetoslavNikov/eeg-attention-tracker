# Attention tracker

Signal-only continuous attention score from EEG (Kernel Flow or OpenBCI).

## Setup

```bash
cd attention-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
# LYS Kernel Flow session
PYTHONPATH=src python scripts/run_score.py \
  ../data/lys_data/perceived_speech/audio_movie/EEG_RAW_study-perceivedspeech_sub-p33_desc-95afb90.npz

# all LYS sessions under data/lys_data/
PYTHONPATH=src python scripts/run_score.py --all-lys

# OpenBCI recording folder (RAW txt + protocol JSON)
PYTHONPATH=src python scripts/run_score.py \
  ../data/openbci_eeg_data/Svetoslav\ Recording --no-show
```

Opens an interactive plot in the browser (zoom, pan, hover for mm:ss values).
HTML + notes land under `outputs/.../attention/`. Use `--no-show` to
save without opening.

## Pipeline

```text
LYS .npz (+ optional .jsonl phases)
  or OpenBCI-RAW*.txt (+ optional protocol JSON)
  → adapters/lys.py or adapters/openbci.py → EEGSession
  → clean → features (sliding band power) → score → plot
```

OpenBCI time is `sample_index / fs` (GUI timestamps are bursty). Railed
channels are dropped. Cue-protocol events (`listen carefully`, `Wander around`,
`Wait a little bit`) become `listen` / `wander` / `baseline` phases.

## Tests

```bash
pip install pytest
PYTHONPATH=src pytest tests/ -q
```
