# ML Layer TODO — Staged Checklist

This checklist governs what happens when the original codebase arrives.
Do not skip ahead to Phase C or D before completing Phase A.

## PHASE A — AUDIT

- [ ] Inspect existing dataset loaders
- [ ] Inspect preprocessing
- [ ] Inspect normalization
- [ ] Inspect labels
- [ ] Inspect patient IDs
- [ ] Inspect train/validation/test splitting
- [ ] Inspect PyTorch code
- [ ] Inspect existing models
- [ ] Inspect metrics
- [ ] Inspect checkpoints
- [ ] Inspect configuration
- [ ] Inspect dependencies

## PHASE B — REUSE

- [ ] Identify reusable components
- [ ] Map existing code to the new interfaces (`ml/interfaces.py`)
- [ ] Avoid duplicate implementations

## PHASE C — INTEGRATION

- [ ] Connect existing dataset pipeline
- [ ] Connect existing model/training pipeline
- [ ] Connect existing evaluation
- [ ] Add tests

## PHASE D — FUTURE GENERATION

- [ ] Determine suitable synthetic-data architecture
- [ ] Integrate generator
- [ ] Evaluate generated data
- [ ] Compare real vs. generated data
