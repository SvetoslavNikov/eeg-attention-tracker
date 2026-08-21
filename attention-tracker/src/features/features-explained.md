# `features/` — what this folder does

Turn cleaned EEG voltages into **band power over time**: how much
energy sits in each brain-wave type, every ~0.5 s.

This folder does **not** decide attention. That is `score/`.

```
cleaned EEGSession
        │
        ▼
  multichannel.session_band_powers   ← what the scorer calls
        │  (AF3 / AF4 by default)
        ▼
  band_power.sliding_band_powers     ← 1-D FFT engine
        │
        ▼
  SessionBandPowers  { t, powers["theta"], powers["alpha"], ... }
        │
        ▼
  score/attention.py
```

| File | Purpose |
|------|---------|
| `bands.py` | Named Hz ranges for each wave type |
| `types.py` | Result object for **one** 2 s window of **one** channel |
| `band_power.py` | Sliding FFT on a 1-D signal |
| `multichannel.py` | Run that on a 4-channel `EEGSession`, average selected electrodes |
| `__init__.py` | Public re-exports |
| `features-explained.md` | This file |

---

## `bands.py` — the Hz dictionary

Nothing is computed here. Two maps, half-open (`fmin <= f < fmax`),
so 8 Hz is alpha, not theta.

| Name | Range | Used by attention v1? |
|------|--------|------------------------|
| delta | 0.5–4 Hz | no |
| theta | 4–8 Hz | **yes** |
| alpha | 8–13 Hz | **yes** |
| beta | 13–30 Hz | no |
| gamma | 30–45 Hz | no |

- **`DEFAULT_BANDS`** — all five. Used if you call the 1-D engine
  with no band list.
- **`ATTENTION_BANDS`** — theta + alpha only. `session_band_powers`
  defaults to this.

---

## `types.py` — one window’s result

Immutable record for **one 2-second slice of one channel**.

```python
BandWindowResult(
    block=3,              # window number 0, 1, 2, …
    offset_samples=1500,  # start index in the 1-D signal
    offset_sec=3.0,       # that start in seconds, from sample 0
    powers={"theta": 12.3, "alpha": 8.1, ...},  # absolute, not %
)
```

`offset_sec` is **not** yet shifted by `session.time[0]`. The
multichannel wrapper does that.

---

## `band_power.py` — the FFT engine (one channel)

Does **not** know about sessions or electrodes. Input: a 1-D voltage
array + sampling rate. Output: a list of `BandWindowResult`.

Default: **2 s window**, **0.5 s hop** (windows overlap). Last
incomplete window is dropped.

```
|------ window 0 ------|
        |------ window 1 ------|
                |------ window 2 ------|
0s     0.5s    1.0s    1.5s    2.0s
```

Per window, before the FFT: subtract the mean (kill DC / 0 Hz),
multiply by a Hann taper (reduce spectral leakage). Then:

### What each FFT line returns

Input `windowed_chunk` is already demeaned + Hann’d. At 500 Hz and
2 s, `n = 1000`.

```python
frequency_spectrum = np.fft.rfft(windowed_chunk)
```

Complex array, length `n/2 + 1` → **501** numbers. Real FFT: input
is real voltages, so negative frequencies are dropped.

Each bin is `a + bi` for one frequency. At a 2 s window the Hz axis
is `0, 0.5, 1.0, …, 250` (Nyquist = `fs/2`). You cannot plot this
yet — it still has phase.

```python
amplitude_spectrum = np.abs(frequency_spectrum)
```

Same length, now **real**. `abs(a+bi) = sqrt(a²+b²)`. Phase gone.
Each bin is “how strong is this frequency.”

```python
power_spectrum = amplitude_spectrum**2
```

Energy, not wave height. A 2× bigger wave → 4× the power. This is
what later gets averaged inside theta / alpha.

```python
power_spectrum = power_spectrum / n
```

Divide by 1000. Without this, a longer window produces bigger FFT
numbers even if the voltage is the same.

```python
power_spectrum = power_spectrum / window_power
```

Hann taper zeros the edges, so it removes energy on purpose.
`window_power = mean(hann²)` (~0.375 for Hann). Dividing puts that
energy back.

```
windowed_chunk          1000 real voltages
        │  rfft
        ▼
frequency_spectrum      501 complex  (sine + cosine per Hz)
        │  abs
        ▼
amplitude_spectrum      501 real     (strength per Hz)
        │  **2
        ▼
power_spectrum          501 real     (energy per Hz)
        │  / n
        ▼
                        comparable across window lengths
        │  / window_power
        ▼
                        Hann energy put back
```

After those five lines the code doubles every bin except DC (and
Nyquist if `n` is even) so the spectrum is **one-sided** power.
Then each band is the **mean** of bins whose Hz falls in that
range (`fmin <= f < fmax`). No bins in range → `0.0`.

This is mean spectral density in the band, not an integral. Fine
for ratios; do not compare these numbers to papers that integrate.

**Note:** the file has a leftover triple-quoted block that pastes
`DEFAULT_BANDS` / `ATTENTION_BANDS` again. It is a string sitting
between imports and `__all__`. It does not execute. Real constants
live in `bands.py`.

---

## `multichannel.py` — apply that to a real session

This is what `score/attention.py` calls.

Defaults:

- channels **AF3, AF4** (forehead pair). FCz / CPz ignored unless
  you pass them.
- bands **`ATTENTION_BANDS`** (theta + alpha).
- 2 s window, 0.5 s hop.

For each selected channel it runs `sliding_band_powers`, then
averages channels so you get one theta series and one alpha series.

### `SessionBandPowers` fields

| Field | Meaning |
|--------|---------|
| `t` | Window **center** times on the EEG clock (`session.time[0]` already added). One number per window, not per sample. |
| `powers` | `{band → array of length n_windows}`. Each value is the **mean of the selected channels** for that band at that window. |
| `per_channel` | Same numbers before averaging: `channel → band → (n_windows,)`. |
| `window_sec` | FFT window length. Default **2.0**. |
| `hop_sec` | How far the window slides. Default **0.5**. |

So `powers["alpha"][i]` is mean frontal alpha in window `i`, not
“that second of every electrode.”

Time: `BandWindowResult.offset_sec` is “seconds from sample 0.”
The wrapper converts each window to a **center**
(`offset_sec + window_sec/2`) then adds `session.time[0]`, so `t`
matches `phases`.

### Concrete return value

Toy recording: **6 seconds**, 500 Hz. AF3 and AF4 are the same mix
(strong 10 Hz alpha, weaker 6 Hz theta). FCz/CPz are noise and are
ignored.

```python
SessionBandPowers(
    t = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
    #     ↑ window 0 center (covers 0–2 s)
    #                    last window covers 4–6 s, center 5.0

    powers = {
        "theta": [63.6, 63.4, 64.5, 63.6, 62.5, 62.0, 62.4, 62.0, 62.4],
        "alpha": [802,  804,  798,  796,  797,  800,  798,  800,  800],
    },
    # slot i = mean(AF3, AF4) for that window
    # alpha >> theta because the sine was 10 Hz

    per_channel = {
        "AF3": {"theta": [...9 numbers...], "alpha": [...9 numbers...]},
        "AF4": {"theta": [...9 numbers...], "alpha": [...9 numbers...]},
    },
    # FCz / CPz are not here

    window_sec = 2.0,
    hop_sec    = 0.5,
)
```

How those 9 times happen:

```
signal: |-------------- 6 seconds --------------|
win 0:  |-- 2s --|                         t=1.0
win 1:     |-- 2s --|                      t=1.5
win 2:        |-- 2s --|                   t=2.0
...
win 8:                    |-- 2s --|       t=5.0
```

`powers["alpha"][0] == mean(AF3 alpha, AF4 alpha)` at `t=1.0`.
Same for every later index.

---

## `__init__.py`

Package facade. Callers can write `from features import
session_band_powers`. `ATTENTION_BANDS` is used inside
`multichannel` but is not re-exported here.

---

## End-to-end

```
session.data[:, AF3] ──┐
                       ├─► sliding_band_powers  (uses bands.py ranges)
session.data[:, AF4] ──┘         │
                                 ▼
                        average AF3 + AF4
                                 │
                                 ▼
         SessionBandPowers.t , .powers["theta"], .powers["alpha"]
                                 │
                                 ▼
                         score/attention.py
```
