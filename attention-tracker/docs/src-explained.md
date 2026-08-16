# `src/` walkthrough — for a Java backend developer

This file is a literal tour of every module under `attention-tracker/src/`.
It is not a research paper. It is “what each file does, what each field
means, and how data moves.” Think of `src/` as a small **hexagonal
pipeline**: one inbound adapter, one domain object, then three
stateless services (clean → features → score) and a presentation
layer (plot).

**What this program is.** Kernel Flow records 4-channel EEG (brain
electrical activity) at ~500 samples/second. This code turns that
recording into a **time series of “attention” numbers**. The number is
**not** a trained classifier and **not** a medical diagnosis. It is a
hand-written formula: *more theta and less alpha than this person’s
own baseline → higher score*. The authors call it an engagement-style
index.

**Java mental model.** `EEGSession` is an immutable record. Adapters
are the only place that knows vendor file formats (like a JPA entity
mapper that you never leak into services). Downstream packages take
`EEGSession` in and return new objects. Nothing mutates in place.

```
LYS .npz  (+ optional .jsonl)
        │
        ▼
  adapters/lys.py          load_lys()
        │
        ▼
     EEGSession            4-ch EEG + metadata  (common/session.py)
        │
        ▼
  clean/pipeline.py        band-pass + spike interpolation
        │
        ▼
  features/*               sliding FFT → alpha/theta power
        │
        ▼
  score/attention.py       baseline-relative z-score
        │
        ▼
  plot/score.py            PNG (or interactive window)
```

The CLI that wires this is **not** in `src/`; it is
`scripts/run_score.py`. `src/` is the library. Tests live in
`tests/` and import the same way: they prepend `src` onto
`sys.path` (Python’s classpath).

---

## 1. How Python packages here map to Java

`src/` is **not** installed as a pip package in the usual way. You run
with `PYTHONPATH=src`. That is equivalent to putting a folder of
`.java` files on the classpath without building a JAR.

Each subdirectory is a **package**. An `__init__.py` is the package
marker. These ones also **re-export** public names so callers can write
`from adapters import load_lys` instead of `from adapters.lys import
load_lys`. That is the same idea as a Java facade class, or a
`package-info` plus a thin public API.

`from __future__ import annotations` at the top of files is a Python
3.7+ switch: type hints are stored as strings and not evaluated at
import time. It lets you write `str | Path` and `EEGSession` without
import-order pain. Ignore it while reading logic.

`@dataclass(frozen=True)` ≈ a Java `record`: auto constructor, auto
equality, **immutable**. After construction you cannot assign fields.
`EEGSession.replace(...)` is the wither / `toBuilder()` pattern:
copy every field, override the ones you pass.

`numpy` (`np`) is the numerical runtime. An `ndarray` is a typed,
contiguous multi-dimensional array (`double[][]` with shape metadata
and vectorized ops). `session.data` is shape `(n_samples, 4)`:
rows = time, columns = electrodes. `session.data[:, 0]` means “every
row, column 0” — the whole AF4 channel. You almost never write
`for` loops over samples; you write array expressions.

`pathlib.Path` is `java.nio.file.Path`. `|` in type hints is
`Optional` / union (`str | Path` = String or Path). `*` in a
function signature (`def clean(session, *, fmin=0.5)`) means
everything after the star is **keyword-only**. You cannot call
`clean(s, 0.5)`; you must write `clean(s, fmin=0.5)`. That is a
deliberate API style so numeric knobs cannot be swapped by accident.

---

## 2. `src/__init__.py`

One line of identity: `__version__ = "0.1.0"`. No pipeline code.
If this folder were installed as a package, that would be
`import src; src.__version__`.

---

## 3. Domain object — `common/session.py`

This is the **only** in-memory model the rest of the code understands.

### Canonical channels

```python
CANONICAL_CHANNELS = ("AF4", "AF3", "FCz", "CPz")
```

These are **10-20 system** scalp sites (the standard EEG naming
grid, like named ports on a bus):

| Name | Where on the head | Why it is here |
|------|-------------------|----------------|
| AF4  | right forehead    | frontal; used for the score |
| AF3  | left forehead     | frontal; used for the score |
| FCz  | midline, front-center | recorded, **not** used in v1 score |
| CPz  | midline, back-center  | recorded, **not** used in v1 score |

The adapter **reorders** whatever column order the `.npz` used into
this tuple. After load, column 0 is always AF4. Downstream code
indexes by **name**, never by “I hope column 2 is FCz.”

### `EEGSession` fields

| Field | Type | Meaning |
|-------|------|---------|
| `data` | `float64` array `(n, 4)` | voltage-like samples. Units are **not** guaranteed µV; LYS exports are uncalibrated. Never apply textbook “±100 µV” cutoffs. |
| `fs` | `float` | sampling rate in **Hertz** (samples per second). ~500. |
| `ch_names` | 4-tuple of `str` | must equal `CANONICAL_CHANNELS` or construction fails. |
| `time` | `float64` array `(n,)` | one timestamp per sample, **seconds**, relative to recording start (starts near 0). Not wall-clock. |
| `subject_id` | `str` | participant, e.g. `"P33"`. |
| `study_id` | `str` | study / file descriptor from the export. |
| `phases` | `dict[str, (start, end)]` | named intervals on the **same** second axis as `time`. Typical keys: `"baseline"`, `"localizer"`, `"task"`. Empty `{}` if no protocol log. |
| `source_path` | `str` | absolute path of the `.npz` (audit trail). |

**Phase** here means “a named stretch of the experiment,” not a
signal-processing phase angle. Baseline ≈ sit quietly. Localizer ≈
cued finger-tapping (used scientifically as a known-active period;
the v1 score does **not** use it). Task ≈ listen to audio or play
Zork.

### Construction and validation (`__post_init__` / `validate`)

Python dataclasses call `__post_init__` after the generated
constructor — like a compact constructor on a Java record.

It:

1. Coerces `data` and `time` to `float64` arrays.
2. Coerces `fs` to Python `float`.
3. Coerces `ch_names` to a tuple (lists are mutable).
4. Calls `validate()`.

`validate()` is a hard contract:

- `data` must be 2-D with **exactly 4** columns.
- channel names must be the canonical four **in that order**.
- `fs > 0`.
- `time` length must equal number of samples (join key: one clock
  tick per row).
- every sample must be finite (`NaN` / `Inf` rejected).
- each phase must have `end >= start`.
- a phase may slightly overhang the recording; it only fails if it
  is **completely** outside `[time[0], time[-1]]`.

Because the class is frozen, `__post_init__` cannot do
`self.data = ...`. It uses `object.__setattr__` — the escape hatch
to write final fields once during construction.

### Helpers

- `n_samples` — `data.shape[0]`.
- `duration_sec` — `time[-1] - time[0]`, or `0` if fewer than 2
  samples. Note this is **span of timestamps**, not
  `n_samples / fs`. For evenly sampled 500 Hz data they agree
  within one sample period.
- `channel_index("AF3")` — name → column. Raises `KeyError` if
  unknown (Java `get` that throws, not `Optional`).
- `replace(**kwargs)` — build a new `EEGSession`. `clean()` uses
  this: `session.replace(data=x)` keeps metadata, swaps the array.

`common/__init__.py` re-exports `CANONICAL_CHANNELS` and
`EEGSession`.

---

## 4. Inbound adapter — `adapters/`

**Hexagonal rule stated in** `adapters/explanation/README.md`:
everything downstream only understands `EEGSession`. Adapters are
the **anti-corruption layer**. Today there is one vendor:
LYS Kernel Flow `.npz` (+ optional `.jsonl`). Future datasets
(SPIS, EEGLAB driving task) should add `adapters/spis.py` etc. and
**map into the same session**, not invent a second DTO.

`adapters/__init__.py` exports `load_lys`.

### 4.1 `adapters/lys.py` — `load_lys(npz_path, jsonl_path=None)`

**`.npz`** is NumPy’s zip-of-arrays (think a zip of named binary
blobs, not JSON). `np.load(..., allow_pickle=True)` opens it.
`allow_pickle` is required because some values (channel name
strings) were saved as Python objects.

**Fields read from the file:**

| Key | Used as |
|-----|---------|
| `data` | must be `(n, 4)` |
| `fs_hz` | → `session.fs` |
| `time` | must have length `n` |
| `channel_names` | 4 names; permuted to canonical order |
| `subject_id`, `study_id` | metadata strings |

**Fields deliberately dropped:** `impedance`, `source_snirf`,
measurement date/time. Impedance is electrode contact quality;
fNIRS (`.snirf`) is the optical twin stream of the same helmet.
Out of scope for this EEG pipeline.

`_channel_order` builds a permutation list: for each canonical
name, find its index in the file. Missing name → `ValueError`.
Then `data = data[:, order]` reorders **columns**. After that
`ch_names` is overwritten with `CANONICAL_CHANNELS` so the
session cannot disagree with the array.

**JSONL protocol log.** JSONL = one JSON object per line
(newline-delimited events). Optional. Used **only** to fill
`phases`. Words, game commands, audio paths, localizer cue
details are ignored on purpose.

Lookup order for the log:

1. explicit `jsonl_path` argument, else
2. `_guess_jsonl`: if the `.npz`’s folder contains **exactly one**
   `*.jsonl`, use it, else
3. no phases (`{}`).

**Time-base conversion** (`_phases_from_jsonl`) is the subtle
part. EEG `time` is relative (≈ 0 at recording start). Log
`timestamp` is **absolute** (unix-like). The adapter finds
`event.event_type == "kernel_start_recording_result"` with
`ok` true (default true if missing) and treats that event’s
timestamp as EEG t ≈ 0. Every later event becomes
`timestamp - rec_start`. If that event is missing, it falls
back to the **first** log line.

Phase mapping:

| Log `event_type` | Phase key | Role |
|------------------|-----------|------|
| `baseline_start` | `baseline` | start |
| `baseline_end` | `baseline` | end |
| `functional_localizer_start` | `localizer` | start |
| `functional_localizer_end` | `localizer` | end |
| `task_start` | `task` | start |
| `quit` or `end_experiment` | `task` | end (first one wins) |

A phase is stored only if **both** start and end exist. The
interval is clipped to `[eeg_t0, eeg_t1]` (`time[0]`, `time[-1]`).
If after clipping `end <= start`, the phase is dropped.

`_parse_jsonl_events` skips blank lines and `#` comments. The
dump script (below) also parses `# key: value` header comments;
`load_lys` does not need them.

### 4.2 `adapters/explanation/` — documentation + dump CLI

Not imported by the pipeline.

`README.md` restates the adapter contract and lists typical
session folders (`audio_movie`, `Bill_Ackman_part2` with **no**
jsonl, `zork_task`).

`dump_session.py` is a **read-only inspector**. You point it at a
folder, `.npz`, or `.jsonl`. It prints:

- every `.npz` key, shapes, first/last EEG rows, per-channel
  min/mean/max, time duration and median `dt`;
- jsonl header comments, event-type histogram, phase-ish
  timeline in EEG-relative seconds, sample payloads;
- then `load_lys(...)` and the resulting `EEGSession` so you can
  see **what was dropped**.

Default with no args: dump the three known LYS sessions under
`data/lys_data/`. `--samples N` prints N example events per type.

This is your `curl`/`jq` for the binary session files.

---

## 5. Cleaning — `clean/pipeline.py`

`clean(session) -> EEGSession`. Pure-ish service: copy the
voltage array, filter it, interpolate spikes, return
`session.replace(data=x)`. Length and channel count **never**
change. Time axis is untouched.

Think of it as a servlet filter that returns a new request
object, not a mutating interceptor.

### Step A — zero-phase Butterworth band-pass

**Band-pass** keeps frequencies between `fmin` (default 0.5 Hz)
and `fmax` (default 40 Hz) and attenuates the rest.

Why those numbers:

- Below ~0.5 Hz: slow drift, sweat, electrode offset — not
  brain “waves” we care about.
- Above 40 Hz: muscle (EMG), line noise neighborhood, and
  this score only needs theta (4–8) and alpha (8–13). Gamma
  in `DEFAULT_BANDS` goes to 45 Hz, but the attention path
  does not use it. The 40 Hz cap is a conservative cleaner.

**Nyquist frequency** = `fs / 2`. Digital sampling can only
represent frequencies strictly below half the sample rate.
At 500 Hz, Nyquist is 250 Hz. Filter cutoffs are expressed as
fractions of Nyquist (`low = fmin/nyq`, `high = fmax/nyq`)
because that is what SciPy’s `butter` expects. They are also
clamped so you never request 0 or 1.0 (invalid).

**Butterworth** is a standard IIR filter family: maximally
flat passband, no ripples. Order `4` means a reasonably
steep roll-off without being numerically nasty.

**`filtfilt`** runs the filter **forward then backward**.
A normal IIR filter delays the signal (phase shift). Running
it both ways **cancels** that delay: peaks stay at the same
times. That is “zero-phase.” Cost: it is **offline only** —
you need the whole recording. You cannot do this in a live
streaming consumer without a different design.

`padlen` is how many samples SciPy uses to pad the edges so
the filter does not explode at t=0. It is capped by signal
length (`x.shape[0] - 1`) so short test arrays still work.

Each channel is filtered independently (`for ch in range(4)`).
There is no spatial mixing. With only 4 electrodes you cannot
do full-scalp ICA (Independent Component Analysis — the usual
“remove blinks as a component” method). This cleaner is
intentionally dumb and 1-D.

### Step B — MAD spike interpolation

LYS voltages are **not calibrated**, so no “if |x| > 150 µV
drop it.” Instead: **robust z-score per channel**.

- `median` of the channel.
- `MAD` = median absolute deviation = median(|x − median|).
  Robust cousin of standard deviation; a few huge spikes
  barely move it.
- For roughly Gaussian data, `σ ≈ 1.4826 * MAD`.
- A sample is **bad** if `|x − median| > artifact_z * 1.4826 * MAD`.
  Default `artifact_z=8` is very conservative: only extreme
  outliers (cough, cable yank), not ordinary EEG.

`_interp_mask` walks **runs** of consecutive bad samples
(linear scan, not regex):

- Run length `<= interp_max_samples` (default **2 seconds**
  of samples, `int(round(2 * fs))`): **linear interpolation**
  from neighboring **good** samples (`np.interp`). Short
  spikes disappear; length unchanged.
- Run longer than that: do **not** invent a 3-second curve
  from distant neighbors. Set those samples to the median of
  good samples. A long artifact becomes a flat line, not a
  fake oscillation that would leak into alpha/theta power.
- If a channel has **zero** good samples, leave it as-is.

If `MAD <= 0` (literally constant channel), skip that
channel.

`clean/__init__.py` exports `clean`.

---

## 6. Features — turning voltage into band power

“Features” here means **numeric descriptors**, not ML
feature-store features. The descriptor is **how much energy
sits in each brain-wave band**, every 0.5 s.

### 6.1 `features/bands.py` — named Hertz ranges

```
DEFAULT_BANDS (half-open: fmin <= f < fmax)
  delta  0.5–4
  theta  4–8
  alpha  8–13
  beta   13–30
  gamma  30–45

ATTENTION_BANDS (what the score actually uses)
  theta  4–8
  alpha  8–13
```

**EEG bands** are conventional frequency buckets, like HTTP
status classes:

- **Delta** — deep sleep / very slow; not used for attention v1.
- **Theta** — 4–8 Hz. In this formula, **higher** relative
  theta is treated as more engaged / active.
- **Alpha** — 8–13 Hz. Often rises with relaxed wakefulness
  and eyes-closed rest. Here, **higher** relative alpha
  **lowers** the score.
- **Beta / gamma** — defined for the generic slider, unused
  by `score_attention`.

Half-open intervals avoid double-counting the 8 Hz bin as
both theta and alpha.

### 6.2 `features/types.py` — `BandWindowResult`

One sliding window’s result (a row in a result set):

| Field | Meaning |
|-------|---------|
| `block` | 0-based window index |
| `offset_samples` | start index in the 1-D signal |
| `offset_sec` | `offset_samples / sfreq` — start time **relative to sample 0**, not yet shifted by `session.time[0]` |
| `powers` | `{"alpha": 12.3, "theta": ...}` **absolute** power, not relative |

Frozen dataclass. Pure data.

### 6.3 `features/band_power.py` — the FFT engine

`sliding_band_powers(signal, sfreq, window_sec=2, hop_sec=0.5,
bands=None) -> list[BandWindowResult]`

**Pure function.** 1-D float vector in, list out. No files, no
`EEGSession`, no plotting. Ported from older scripts.

**Sliding window.** At 500 Hz, `window_sec=2` → 1000 samples.
`hop_sec=0.5` → step 250 samples. Windows **overlap**
(2.0 − 0.5 = 1.5 s shared). Overlap makes the later attention
curve smoother. Last incomplete window is **dropped** (same
as a `while (start + window <= n)` loop).

Rejects: `sfreq/window/hop <= 0`, window shorter than 2
samples, hop shorter than 1 sample, signal shorter than one
window, anything not 1-D.

**Per window:**

1. `chunk = chunk - mean(chunk)` — remove **DC** (0 Hz
   offset). Otherwise the FFT’s first bin eats the mean
   voltage and swamps everything.
2. Multiply by a **Hann window** (`np.hanning`). A raw
   rectangular cut has sharp edges → spectral leakage
   (energy smears into neighboring frequencies). Hann
   tapers the edges to zero. Cost: you lose a bit of
   amplitude, corrected next.
3. `window_power = mean(hann²)` — scalar used to **undo**
   the energy the taper removed, so power is comparable
   across window lengths.

`_absolute_band_powers` is a **one-sided periodogram**:

1. `np.fft.rfft` — real FFT. Input is real voltages, so
   the negative-frequency half is redundant. Output length
   is `n/2 + 1` complex bins.
2. Power = `|complex|²`.
3. Divide by `n` (length normalization).
4. Divide by `window_power` (Hann compensation).
5. Double all bins except DC (and Nyquist if `n` even).
   That folds the discarded negative frequencies back so
   the numbers are **one-sided** power.

`rfftfreq(n, d=1/sfreq)` is the Hertz axis of those bins
(0, Δf, 2Δf, …, Nyquist). Frequency resolution
`Δf ≈ sfreq / n = 1 / window_sec`. A 2 s window → 0.5 Hz
bins. That is why a 2 s window can separate 4–8 from 8–13
at all.

For each band, take bins with `fmin <= f < fmax` (clipped
to `[0, Nyquist]`). If no bin lands in the band, power is
`0.0`. Otherwise **mean** of those bins — not the sum.
So this is **mean spectral density in the band**, not
integrated band energy. Fine for ratios; do not compare
these numbers to papers that integrate.

**Note:** the file contains a leftover triple-quoted block
that pastes `DEFAULT_BANDS` / `ATTENTION_BANDS` again. It
is a string literal sitting between imports and `__all__`.
It does not execute. Real band constants live in
`features/bands.py`. `band_power` imports `DEFAULT_BANDS`
from there. `features/__init__.py` re-exports
`DEFAULT_BANDS` from `band_power`, so the public name
still works.

### 6.4 `features/multichannel.py` — session-level wrapper

`session_band_powers(session, channels=None, window_sec=2,
hop_sec=0.5, bands=None) -> SessionBandPowers`

This is the **service** the scorer calls.

Defaults: channels `AF3`, `AF4` (frontal pair); bands
`ATTENTION_BANDS` (theta + alpha only). `FCz` and `CPz` are
ignored unless you pass them.

For each requested channel it slices `session.data[:, idx]`,
runs `sliding_band_powers`, and stacks results.

**Time alignment.** `BandWindowResult.offset_sec` is “seconds
from sample index 0.” EEG `time[0]` is usually ~0 but is not
guaranteed. The wrapper:

- converts each window to a **center** time:
  `offset_sec + window_sec/2` (so a window covering 0–2 s
  is plotted at 1.0 s);
- then adds `session.time[0]`.

Now `t` lives on the same axis as `phases`.

**Channel average.** For each band, stack the per-channel
series and `mean` them. `powers["alpha"]` is therefore
“mean frontal alpha,” not a single electrode.

`SessionBandPowers` fields:

| Field | Meaning |
|-------|---------|
| `t` | `(n_windows,)` center times, EEG seconds |
| `powers` | band → `(n_windows,)` mean across selected channels |
| `per_channel` | channel → band → `(n_windows,)` (kept; scorer currently uses the mean) |
| `window_sec`, `hop_sec` | echoed knobs |

---

## 7. Score — `score/attention.py`

Two entry points:

- `score_attention(session, ...)` — computes band powers,
  then scores.
- `score_from_band_powers(session, bp, ...)` — same formula
  if you already have `SessionBandPowers` (avoids a second
  FFT if you are experimenting).

### Formula (v1, fully explicit)

```
baseline_alpha = median(alpha[t in baseline window])
baseline_theta = median(theta[t in baseline window])

alpha_rel = alpha / baseline_alpha
theta_rel = theta / baseline_theta
raw       = theta_rel - alpha_rel
attention = (raw - mean(raw)) / std(raw)    # z-score over whole session
```

**Why divide by this person’s baseline.** Absolute power
varies with hair, contact, skull, gain. Ratios cancel a
static scale factor. Median (not mean) so a few wild
windows in the baseline period do not set the denominator.

**Why theta − alpha.** Sketch of the literature this
imitates: active / engaged states often show relatively
more theta and relatively less alpha than quiet rest.
The test `test_score.py` encodes the intended direction:
synthesize 60 s of 10 Hz (alpha), then 60 s of 6 Hz
(theta); mean attention in the second half must be
**higher**.

**Why z-score the raw difference.** `raw` is dimensionless
but its spread still depends on how wild the session was.
Z-scoring (`(x − μ) / σ`) forces the session curve to
mean 0, std 1. **Consequence:** you **cannot** compare a
value of `+1.2` across two recordings as “more attention
than the other subject.” You can only say “this moment is
high **for this session**.” If `σ ≈ 0` (flat raw), the
code emits zeros instead of dividing by zero.

### Baseline window selection (`_baseline_window`)

1. If `session.phases` has `"baseline"`, use that
   `(start, end)` — the protocol’s quiet period.
2. Else use `[time[0], time[0] + baseline_fallback_sec]`
   (default **60 s**). This is how `Bill_Ackman_part2`
   works: no jsonl, so first minute is treated as rest.

Then windows whose **center** `t` falls inside that
interval are averaged (median). If **no** window center
lands inside (odd clipping), fall back to the first
`baseline_fallback_sec / hop_sec` windows.

If a baseline median is `<= 0` (should not happen with
real power), replace with `mean(band) + 1e-20` so
division stays defined.

### `AttentionResult`

| Field | Meaning |
|-------|---------|
| `t` | same window centers as band powers |
| `attention` | z-scored index |
| `alpha`, `theta` | absolute mean-frontal power |
| `alpha_rel`, `theta_rel` | divided by baseline |
| `baseline_alpha`, `baseline_theta` | the two scalars |
| `subject_id`, `study_id` | copied for plot titles |

`score/__init__.py` exports `AttentionResult` and
`score_attention`.

---

## 8. Plot — `plot/score.py`

`plot_attention(result, session=None, save_path=None, title=None)`.

Three stacked Matplotlib panels, shared X axis (seconds):

1. `attention(t)` with a y = 0 line (session mean).
2. `alpha_rel` and `theta_rel` with y = 1 (baseline).
3. absolute alpha/theta on a **log** Y axis.

If `session` is passed, each phase is a translucent
vertical span (`axvspan`): baseline gray, localizer red-ish,
task a fourth color. Legend labels are de-duplicated
because the span is drawn on all three axes.

If `save_path` is set: switch Matplotlib to the `Agg`
backend (no GUI window — correct for servers/CI),
create parent dirs, save PNG at 150 dpi, `plt.close`.
If not: `plt.show()` (interactive).

`plot/__init__.py` exports `plot_attention`.

---

## 9. How a request actually runs

`scripts/run_score.py` (outside `src/`, but this is the
composition root):

```python
session = load_lys(npz, jsonl)
session = clean(session)          # unless --skip-clean
result  = score_attention(session)
plot_attention(result, session, save_path=.../attention_score.png)
# plus a tiny notes.md with fs, duration, phases, mean z, baselines
```

`--all-lys` loops three known folders. Output mirrors the
data tree under `outputs/lys_data/.../attention/`.

Tests (`tests/`) lock the contracts you should trust:

| Test | Claim |
|------|--------|
| `test_session` | shape, names, duration |
| `test_clean` | shape preserved; a 1e6 spike is reduced |
| `test_features` | 10 Hz sine → alpha ≫ theta; 2-D input rejected |
| `test_score` | low-alpha / high-theta half scores higher |
| `test_lys_load` | real `audio_movie` file loads, cleans, scores (skipped if data absent) |

---

## 10. What `src/` does **not** do

Keep this list in your head so the code’s honesty stays
visible:

- No machine learning, no trained weights, no sklearn model.
- No word-locked ERPs, no speech envelope tracking, no Zork
  command locking — the jsonl words/commands are unused.
- No fNIRS.
- No live / streaming path (`filtfilt` needs the whole take).
- No cross-session comparable units (z-score is within-session).
- No claim of ground-truth “was attending?” There is usually
  no quiz or attend/ignore condition in the files.
- FCz / CPz are loaded and cleaned but ignored by the default
  score.
- `localizer` is stored on the session and shaded on the plot;
  it is not an input to the formula.

That is the entire `src/` tree: one immutable session object,
one file mapper, one offline cleaner, one sliding FFT, one
arithmetic score, one plotter.
