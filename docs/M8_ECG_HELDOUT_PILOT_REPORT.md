# M8 — ECG Controlled Pilot: Held-Out Re-Evaluation of the Inherited GAN

**Status:** engineering remediation complete (Category 2 fix); **model
selection remains the open human checkpoint already established in M6/
M7 — this pilot does not decide it, and nothing here authorizes
large-scale waveform generation.**

**Scope boundary respected:** this pilot evaluates the **inherited**
per-superclass GAN (`syngen/SynGen/SynGen`) only. It does not download,
evaluate, or select SSSD-ECG or any other external model — that
candidate's pretrained-weight license is still unconfirmed
(`docs/PROJECT_STATE.md` M6/M7-0), a credential/approval gate this
pilot does not cross.

---

## 1. What this pilot found already documented, and verified rather than re-derived

`docs/syngen-codebase-analysis.md` §12.1 (HIGH) had already identified
that the existing `eval_<CLASS>/metrics.json` numbers compare generated
samples against the GAN's own **training** data (`real_<CLASS>.npy` was
built from folds 1-8 — the exact folds `train_gan()` trained each
generator on). That makes the previously-reported KS/KL/MSE numbers a
measure of memorization fidelity, not generalization — not evidence
that the model is suitable for synthetic-data use.

This pilot (`integration/ecg_pilot_heldout_evaluation.py`) fixes exactly
that methodology gap:

- Reuses `build_label_map`/`PTBXLDataset` from the inherited
  `gan_pytorch.py` **unchanged**, with `folds=[9]` — PTB-XL's validation
  fold, never in this project's own `training_folds: [1-8]`
  (`configs/base.yaml`).
- Reuses `compute_metrics`/`kl_divergence_1d` from the inherited
  `evaluate_class.py` **unchanged** — identical metric math, identical
  thresholds.
- Compares against the **already-generated**
  `synthetic_data/<CLASS>_synthetic.npy` files — no retraining, no new
  generation, no new dependency.
- Writes to new `eval_<CLASS>_heldout/` directories; the original
  (leaky) `eval_<CLASS>/` directories are untouched, so both numbers
  stay inspectable side by side.

## 2. Result: the held-out numbers barely move

| Class | n (held-out / train) | KS held-out | KS train-fold (leaky) | Delta | KL held-out | Variance |
|---|---|---|---|---|---|---|
| NORM | 944 / 7,553 | 0.0982 | 0.0982 | +0.0000 | 0.0844 | 0.3100 |
| MI | 413 / 3,315 | 0.0840 | 0.0855 | −0.0015 | 0.0676 | 0.2857 |
| STTC | 516 / 4,069 | 0.0727 | 0.0777 | −0.0050 | 0.0817 | 0.2627 |
| CD | 497 / 3,905 | 0.0898 | 0.0920 | −0.0023 | 0.0661 | 0.3090 |
| HYP | 219 / 1,822 | 0.0772 | 0.0769 | +0.0003 | 0.0573 | 0.2525 |

Full per-lead breakdown: `docs/M8_ECG_HELDOUT_PILOT_REPORT.json`.

**Reading this honestly:** the generalization gap is within ±0.008 KS
across all five classes — essentially noise at these sample sizes
(219-944 held-out records). The original concern (§12.1) was that the
leaky numbers *overstated* quality; the corrected numbers say the model
is **not** overfit to the point of memorizing its training set, which is
a genuinely more reassuring finding than "the number was wrong." It does
**not** mean the absolute quality is excellent — KS ≈ 0.07-0.10 sits at
the boundary of the scripts' own inline "excellent" threshold (<0.1),
not comfortably inside it, and variance (0.25-0.31) is well above the
mode-collapse warning bands (<0.01 severe, <0.05 partial) the inherited
`check_mode_collapse()` defines, so there is no sign of mode collapse
either.

## 3. Checks from the task's own pilot checklist — status

| Check | Status |
|---|---|
| Successful generation and reproducibility | **Confirmed** — `synthetic_data/*.npy` already exist, 500 samples/class, loaded without error |
| Duplicate outputs / mode collapse | **No evidence of mode collapse** — variance 0.25-0.31, far above both warning thresholds (0.01/0.05) the inherited code defines |
| Signal shape, sampling rate | **Matches schema** — (1000, 12) at 100 Hz, consistent with this project's `ecg.signal_shape`/`ecg.sampling_hz` (D003) |
| Physical amplitude calibration | **NOT CALIBRATED — pre-existing, documented gap (§12.5).** Normalization is per-record, per-lead z-score discarded after use; a generated `[-1,1]` value cannot be mapped back to physical mV. Not fixed here — doing so changes the normalization scheme, which is a model/architecture decision, not an engineering fix |
| Morphological / signal-quality checks | Partially covered by KS/KL/MSE above; no beat-level morphology (QRS detection, interval measurement) has been run — out of scope for this pass |
| Label and superclass validity | Carried over from `docs/syngen-codebase-analysis.md` §5/§16.2 — an open ~20% vs ~40% multi-label discrepancy question, not re-litigated here |
| Patient characteristics genuinely used for conditioning? | **No.** Confirmed from the architecture, not assumed: 5 independent `Generator`/`Discriminator` pairs, one per diagnostic superclass, **no shared weights, no class-conditioning vector** (`docs/syngen-codebase-analysis.md` §7). Conditioning is "pick which of 5 checkpoint files to sample from" — nothing in this GAN reads age, sex, state, risk factors, or any other field from the synthetic patient records this project generates. A waveform attached from this model would carry no model-conditioned relationship to the patient it's attached to; any apparent correlation would be coincidental |
| Suitable for the intended synthetic-data use? | **Not yet** — generalization is now confirmed adequate, but amplitude calibration is unresolved and conditioning is class-only. Both are architecture-level, not this pilot's to decide |

## 4. What this pilot did not do, and why

- **Did not retrain, fine-tune, or regenerate waveforms.** Only
  re-evaluated already-existing checkpoints and already-existing
  synthetic samples against corrected real data.
- **Did not fix the amplitude-calibration gap (§12.5).** That requires
  changing the normalization scheme (per-record z-score → a persisted
  global/per-lead statistic), which changes what the model's output
  *means* — an architecture decision, not a measurement fix.
- **Did not resolve the 20% vs 40% multi-label discrepancy (§16.2)** or
  the single-class-vs-multi-label architecture question (§16.3) —
  carried over as still-open from the prior audit.
- **Did not evaluate, download, or compare SSSD-ECG.** Model selection
  between the inherited GAN and any alternative remains the open human
  checkpoint `docs/PROJECT_STATE.md` already established across M6/M7 —
  repeatedly reaffirmed there, most recently blocked on confirming the
  SSSD-ECG pretrained-weight license (Figshare access, a credential
  requirement this pilot does not have and should not route around).
- **Did not attach any waveform to any of the 100,000 patient
  records.** `ecg.signal_available` remains `false` throughout, per
  D003, unchanged by this pilot.

## 5. Recommendation

The engineering defect in §12.1 is fixed and the corrected numbers are
now on record. This does **not** change the ECG milestone's status from
"blocked at an open human checkpoint" — it answers one of the questions
a human will need when that checkpoint is actually cleared (is the
inherited GAN's reported quality trustworthy — yes, now that it's
measured correctly), without pre-empting the checkpoint itself. The
next action on this track is still exactly what `docs/PROJECT_STATE.md`
already recorded: a human confirms the SSSD-ECG pretrained-weight
license, or explicitly decides to proceed with the inherited GAN despite
its two remaining open items (amplitude calibration, class-only
conditioning).
