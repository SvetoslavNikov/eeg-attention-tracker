# Attention tracker (LYS)

Signal-only continuous attention score from Kernel Flow 4-channel EEG.

## Setup

```bash
cd attention-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
# one session
PYTHONPATH=src python scripts/run_score.py \
  ../data/lys_data/perceived_speech/audio_movie/EEG_RAW_study-perceivedspeech_sub-p33_desc-95afb90.npz

# all LYS sessions under data/lys_data/
PYTHONPATH=src python scripts/run_score.py --all-lys
```

Plots and notes land under `outputs/lys_data/.../attention/`.

## Pipeline

```text
LYS .npz (+ optional .jsonl phases)
  → adapters/lys.py → EEGSession
  → clean → features (your sliding band power) → score → plot
```

## Tests

```bash
pip install pytest
PYTHONPATH=src pytest tests/ -q
```
