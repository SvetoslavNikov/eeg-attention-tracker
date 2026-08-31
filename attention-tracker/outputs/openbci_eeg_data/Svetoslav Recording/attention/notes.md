# Attention score — Svetoslav / 2026-08-28_15-51-10

- source: `/Users/svetoslavnikov/lys/eeg-attention-tracker/data/openbci_eeg_data/Svetoslav Recording/OpenBCI-RAW-2026-08-28_15-51-10.txt`
- fs: 500.000 Hz
- duration: 992.9 s
- channels used: Ch01, Ch02, Ch03, Ch04, Ch06, Ch07, Ch08, Ch10, Ch11, Ch12, Ch13, Ch14
- dropped channels: Ch00, Ch05, Ch09, Ch15
- phases: blink=[0.0,28.9], rest_1=[28.9,38.9], jaw=[38.9,69.0], rest_2=[69.0,79.0], nod=[79.0,109.0], rest_3=[109.0,119.0], eyes=[119.0,149.0], rest_4=[149.0,159.1], baseline=[159.1,279.1], rest_5=[279.1,289.1], listen=[289.1,649.1], rest_6=[649.1,659.2], wander=[659.2,992.9]
- mean attention (z): 0.000
- baseline alpha: 1264
- baseline theta: 1481
- plot: `attention_score.html`

## Phase means

- **blink** [0.0, 28.9]s  attention_z=2.524  alpha=3795  theta=1.626e+04  alpha/theta=0.233
- **rest_1** [28.9, 38.9]s  attention_z=-0.066  alpha=2520  theta=3582  alpha/theta=0.703
- **jaw** [38.9, 69.0]s  attention_z=1.249  alpha=2383  theta=9099  alpha/theta=0.262
- **rest_2** [69.0, 79.0]s  attention_z=-0.181  alpha=1859  theta=2311  alpha/theta=0.804
- **nod** [79.0, 109.0]s  attention_z=-0.150  alpha=2139  theta=2770  alpha/theta=0.772
- **rest_3** [109.0, 119.0]s  attention_z=0.049  alpha=1170  theta=2498  alpha/theta=0.469
- **eyes** [119.0, 149.0]s  attention_z=0.713  alpha=1999  theta=6336  alpha/theta=0.316
- **rest_4** [149.0, 159.1]s  attention_z=-0.075  alpha=1400  theta=2232  alpha/theta=0.627
- **baseline** [159.1, 279.1]s  attention_z=-0.199  alpha=1391  theta=1682  alpha/theta=0.827
- **rest_5** [279.1, 289.1]s  attention_z=-0.129  alpha=1185  theta=1744  alpha/theta=0.679
- **listen** [289.1, 649.1]s  attention_z=0.076  alpha=1094  theta=2521  alpha/theta=0.434
- **rest_6** [649.1, 659.2]s  attention_z=-0.578  alpha=4627  theta=3839  alpha/theta=1.205
- **wander** [659.2, 992.9]s  attention_z=-0.356  alpha=2550  theta=2363  alpha/theta=1.079

## Listen vs wander

- alpha wander/listen: 2.331
- theta wander/listen: 0.937
- attention_z listen=0.076, wander=-0.356

Descriptive index only (n=1, listen-then-wander order). Not a validated classifier.
