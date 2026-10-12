# Evaluation report

Corpus: 248 sections. Refusal threshold chosen on dev questions: coverage < 0.418.

## Finding the right section (answerable questions)

| Split | Questions | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---:|---:|---:|---:|---:|
| dev | 23 | 70% | 96% | 96% | 0.818 |
| test | 22 | 82% | 100% | 100% | 0.909 |
| all | 45 | 76% | 98% | 98% | 0.862 |

## Refusing what the regulations do not answer (test split only)

- Answerable questions answered: 22 of 22
- Unanswerable questions refused: 8 of 8

## Quote check against tampered quotes

- Genuine quotes accepted: 1410 of 1410
- Quotes with one number changed, rejected: 829 of 830
- Quotes with 'not' removed, rejected: 139 of 139

## Misses: gold section not in the top 5

- **a19** (dev) "Is it allowed to load a ship so that its load line marks are submerged?" gold ['42.07-10'], rank 7. Top 3: 42.07-5 (Marks placed on vessel to indicate load lines.); 42.01-10 (Purpose of regulations.); 42.07-60 (Control.)

## Every question

| id | split | gold | rank | coverage | top result |
|---|---|---|---:|---:|---|
| a01 | dev | 42.20-70 | 1 | 0.73 | 42.20-70 |
| a02 | test | 42.20-25 | 1 | 0.67 | 42.20-25 |
| a03 | dev | 42.20-30 | 1 | 0.43 | 42.20-30 |
| a04 | test | 42.20-20 | 1 | 0.43 | 42.20-20 |
| a05 | dev | 42.15-50 | 1 | 0.87 | 42.15-50 |
| a06 | test | 42.15-45 | 1 | 1.00 | 42.15-45 |
| a07 | dev | 42.15-70 | 1 | 0.73 | 42.15-70 |
| a08 | test | 42.15-75 | 1 | 0.50 | 42.15-75 |
| a09 | dev | 42.15-65 | 1 | 0.91 | 42.15-65 |
| a10 | test | 42.15-1 | 2 | 0.71 | 157.47 |
| a11 | dev | 42.20-11, 42.20-6 | 1 | 1.00 | 42.20-11 |
| a12 | test | 42.20-12 | 1 | 0.84 | 42.20-12 |
| a13 | dev | 42.13-25, 42.13-40 | 1 | 0.78 | 42.13-25 |
| a14 | test | 42.13-30 | 1 | 0.74 | 42.13-30 |
| a15 | dev | 42.13-20 | 1 | 1.00 | 42.13-20 |
| a16 | test | 42.09-5, 42.20-3, 42.13-15 | 1 | 0.53 | 42.09-5 |
| a17 | dev | 42.15-80 | 1 | 0.65 | 42.15-80 |
| a18 | test | 42.09-40, 42.11-20 | 2 | 1.00 | 42.09-15 |
| a19 | dev | 42.07-10 | 7 | 0.68 | 42.07-5 |
| a20 | test | 42.07-20 | 1 | 0.57 | 42.07-20 |
| a21 | dev | 42.07-50 | 1 | 0.57 | 42.07-50 |
| a22 | test | 42.30-35, 42.30-5 | 1 | 0.55 | 42.30-35 |
| a23 | dev | 42.25-15 | 1 | 0.92 | 42.25-15 |
| a24 | test | 42.07-35, 42.07-40, 42.05-60, 42.05-10 | 1 | 1.00 | 42.05-10 |
| a25 | dev | 42.15-30 | 1 | 0.82 | 42.15-30 |
| a26 | test | 42.20-5, 42.20-7, 42.20-8 | 2 | 0.58 | 42.20-3 |
| a27 | dev | 42.20-40 | 3 | 1.00 | 42.20-50 |
| a28 | test | 42.20-65 | 1 | 1.00 | 42.20-65 |
| a29 | dev | 157.10d | 1 | 1.00 | 157.10d |
| a30 | test | 157.09, 157.10, 157.10a | 1 | 0.80 | 157.10a |
| a31 | dev | 157.29, 157.37 | 3 | 0.75 | 157.43 |
| a32 | test | 157.12, 157.12a, 157.12b, 157.12c, 157.12d | 1 | 1.00 | 157.12b |
| a33 | dev | 157.15 | 2 | 0.97 | 157.12d |
| a34 | test | 157.19 | 1 | 0.74 | 157.19 |
| a35 | dev | 157.20 | 1 | 0.83 | 157.20 |
| a36 | test | 157.22 | 2 | 0.43 | 157.47 |
| a37 | dev | 157.21 | 2 | 1.00 | 42.09-10 |
| a38 | test | 157.152 | 1 | 0.92 | 157.152 |
| a39 | dev | 157.164 | 2 | 1.00 | 157.138 |
| a40 | test | 157.14 | 1 | 1.00 | 157.14 |
| a41 | dev | 157.17 | 1 | 1.00 | 157.17 |
| a42 | test | 157.455 | 1 | 0.53 | 157.455 |
| a43 | dev | 157.23, 157.47 | 1 | 0.76 | 157.23 |
| a44 | test | 157.33 | 1 | 0.76 | 157.33 |
| a45 | dev | 157.410 | 2 | 0.57 | 157.10d |
| u01 | dev | (none) | - | 0.32 | 157.22 |
| u02 | test | (none) | - | 0.24 | 157.12d |
| u03 | dev | (none) | - | 0.28 | 157.132 |
| u04 | test | (none) | - | 0.31 | 157.37 |
| u05 | dev | (none) | - | 0.27 | 157.430 |
| u06 | test | (none) | - | 0.26 | 42.20-6 |
| u07 | dev | (none) | - | 0.25 | 157.455 |
| u08 | test | (none) | - | 0.42 | 157.22 |
| u09 | dev | (none) | - | 0.28 | 42.15-80 |
| u10 | test | (none) | - | 0.17 | 157.138 |
| u11 | dev | (none) | - | 0.38 | 42.07-15 |
| u12 | test | (none) | - | 0.40 | 42.20-9 |
| u13 | dev | (none) | - | 0.32 | 42.09-10 |
| u14 | test | (none) | - | 0.26 | 157.29 |
| u15 | dev | (none) | - | 0.41 | 42.07-60 |
| u16 | test | (none) | - | 0.36 | 157.03 |
