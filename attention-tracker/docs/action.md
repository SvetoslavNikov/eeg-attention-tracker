# Action plan

**First deliverable:** a continuous attention score from **EEG alone** (no audio, words, or game events). Protocol only cuts phases when present. Same algo must run on LYS Flow sessions and external datasets.

## Steps


```commandline
1. Load   → open the brain file
2. Clean  → wipe big mess (cough spikes, noise)
3. Features → measure “alpha” and “theta” waves over time
4. Score  → turn those into one attention number over time
5. Plot   → draw the picture
```

1. **Load** — Common object is **LYS-native**: 4 channels `AF4, AF3, FCz, CPz`, array `(n × 4)`, `fs`, optional `time` + phase marks. LYS `.npz` loads 1:1. Other datasets use adapters that **map into this shape** (pick nearest homologs; drop or ignore extra channels). Clean/score never see foreign formats.

2. **Clean** — Band-pass; reject big artifacts (MAD/percentile) on the common 4-ch object only.

3. **Features** — Sliding alpha / theta (and maybe beta) power; relative or baseline-normalized within the recording.

4. **Score** — Map features → one time series `attention(t)` (e.g. alpha↓ + theta↑ vs baseline).

5. **Sanity check** — On known segments (rest, tapping, EO/EC, driving labels if any), confirm the score moves as expected.

6. **Cross-dataset** — Run the same scorer on speech, Zork, SPIS, driving; plots + brief summaries.

7. **Later** — Word/TRF, speech tracking, Zork locking, supervised labels.

## Done when

`score(eeg) → t, attention(t)` works on every dataset under `data/` via one path.
