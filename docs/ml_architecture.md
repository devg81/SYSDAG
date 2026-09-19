# ML Architecture (High-Level)

This document describes the intended shape of the ML pipeline, not its
implementation. It is deliberately abstract: the original codebase has not
been audited yet, so no dataset, preprocessing, model, or metric choices
are made here. See `ml/README.md` and `ml/TODO.md` for how this connects
to the audit.

## Core pipeline

```
Raw Data
   |
   v
Existing Data/Preprocessing Pipeline   (original codebase; to be audited)
   |
   v
Canonical ML Dataset Interface         (ml/interfaces.py: DatasetInterface)
   |
   v
Model                                  (ml/interfaces.py: ModelInterface)
   |
   v
Training                               (ml/interfaces.py: TrainerInterface)
   |
   v
Evaluation                             (ml/interfaces.py: EvaluatorInterface)
   |
   v
Experiment Results
```

Everything above "Canonical ML Dataset Interface" belongs to the original
codebase and must be audited, not rebuilt. Everything from that interface
downward is where this repository's `ml/` contracts apply.

## Future: synthetic data generation (NOT decided)

The generator's architecture (GAN, VAE, diffusion, or otherwise) is
explicitly undecided and out of scope until Phase D of `ml/TODO.md`. The
conceptual flow, once real data and a canonical dataset interface exist:

```
Real Data
   |
   v
Preprocessing
   |
   v
Generator                              (FUTURE — architecture undecided)
   |
   v
Synthetic Data
   |
   v
Validation / Evaluation
   |
   v
Real vs. Synthetic Comparison
```

Per `Claude.md`, this generation layer must remain isolated from ingestion,
validation, schema, and export code, and must not leak generator-specific
assumptions into the canonical dataset/model/trainer/evaluator contracts.
