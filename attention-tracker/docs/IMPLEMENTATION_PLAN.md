# Implementation plan — LYS signal-only attention score

Perfect for LYS Flow data first. Other datasets adapt later; they do not shape the core.

## File structure

```text
attention-tracker/
  src/
    common/
      session.py          # EEGSession — LYS continuous EEG object
    adapters/
      lys.py              # load LYS .npz (+ optional .jsonl phases) → EEGSession
    clean/
      pipeline.py         # band-pass, artifact reject on EEGSession
    features/
      band_power.py       # sliding alpha/theta power from cleaned signal
    score/
      attention.py        # band power → continuous attention(t)
    plot/
      score.py            # standard attention curve figure
  scripts/
    run_score.py          # CLI: LYS session path → score + plot under outputs/
  tests/
    test_session.py
    test_lys_load.py
    test_clean.py
    test_features.py
    test_score.py
  docs/
    action.md
    IMPLEMENTATION_PLAN.md
    PROJECT_DESCRIPTION.md
```

## What each piece does

| Path | Role |
|------|------|
| `common/session.py` | Defines `EEGSession` for LYS only: `data (n×4)`, channels `AF4, AF3, FCz, CPz`, `fs`, `time`, subject/session ids, optional phase windows from the protocol. Validates shape and channel order. |
| `adapters/lys.py` | Reads LYS `EEG_RAW_*.npz`. Optionally reads matching `.jsonl` only to fill phase boundaries (baseline / localizer / task). Returns `EEGSession`. No audio, no words, no game events. |
| `clean/pipeline.py` | Input/output `EEGSession`. Band-pass; reject large artifacts from the signal. Same length, same 4 channels. |
| `features/band_power.py` | Sliding-window alpha and theta power on cleaned data. Pure arrays in/out (plus `fs`). |
| `score/attention.py` | Turns band-power traces into one series `attention(t)`, normalized to the session baseline phase when present. |
| `plot/score.py` | Plots `attention(t)` (and optional band traces) for a run. |
| `scripts/run_score.py` | Wire: load LYS → clean → features → score → save plot/notes under `outputs/…`. |
| `tests/*` | Unit tests per layer; real Way of Kings `.npz` for load smoke. |

## Data flow

```text
LYS .npz (+ optional .jsonl phases)
    → adapters/lys.py
    → EEGSession
    → clean/pipeline.py
    → features/band_power.py
    → score/attention.py
    → plot + outputs/
```

## Later (not in this tree yet)

Extra adapters under `adapters/` that convert other formats **into** the same LYS `EEGSession`. No changes to clean/features/score for that.
