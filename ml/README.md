# ML Layer

## Purpose

This directory establishes model-agnostic contracts (`interfaces.py`) for
the dataset, model, trainer, and evaluator components SysDaG will need once
it moves into ML/deep-learning stages. It exists so that infrastructure and
downstream/model-independent work can proceed in parallel with the audit of
the original codebase, without blocking on it.

## What is intentionally NOT implemented yet

- No dataset loader (no PTB-XL/WFDB reading, parsing, or preprocessing).
- No model architecture (no CNN/Transformer/RNN/etc.).
- No training loop, optimizer, or loss function.
- No evaluation metrics.
- No configuration schema beyond a placeholder (`configs/README.md`).

All of the above depend on the original codebase, which is not yet
available. Building any of them now would risk duplicating or conflicting
with existing, working implementations.

## How the original codebase will eventually connect

The original codebase must be audited first (see `ml/TODO.md`, Phase A).
After the audit:

1. Existing dataset/preprocessing code is wrapped or adapted to satisfy
   `DatasetInterface`, preserving its existing patient-level split logic
   and label encoding rather than reimplementing them.
2. Existing model code is wrapped or adapted to satisfy `ModelInterface`.
3. Existing training code is wrapped or adapted to satisfy
   `TrainerInterface`.
4. Existing evaluation/metrics code is wrapped or adapted to satisfy
   `EvaluatorInterface`.

Adapters live alongside the original code's natural location; the
interfaces here should not need to change to accommodate them.

## Expected responsibilities of each layer

- **Dataset** — turns raw/preprocessed source data into model-ready
  samples, and exposes named splits without leaking patients across them.
- **Model** — accepts standardized input and produces output; agnostic to
  how it is trained or evaluated.
- **Trainer** — consumes a `Model` and a `Dataset` and performs training;
  agnostic to the specific architecture or dataset implementation.
- **Evaluator** — consumes predictions/results and produces metrics;
  agnostic to how the model was trained.

## Architectural principles

- **Audit before implementation.** The original codebase must be inspected
  (loaders, preprocessing, normalization, labels, patient IDs, splits,
  existing PyTorch code, models, metrics, checkpoints, configuration,
  dependencies) before any concrete ML component is written here. See
  `ml/TODO.md` Phase A.
- **Reuse before rebuild.** Per `Claude.md`, prefer adapting existing,
  working code over reimplementing it.
- **Model-independence.** This layer's interfaces must not assume a
  specific architecture, framework detail, or dataset format.
- **Generator isolation.** Synthetic-data generation is a future concern
  (`ml/TODO.md` Phase D) and must stay isolated from dataset/model/trainer/
  evaluator contracts, consistent with `Claude.md`'s `generation/`
  isolation rule.
- **No invented requirements.** Nothing in this layer should encode
  assumptions about the missing repository. Where a decision depends on the
  original codebase, it is left as a TODO, not guessed.
