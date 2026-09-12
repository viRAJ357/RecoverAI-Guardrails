# RecoverAI training data - synthetic demo dataset

This folder contains **360,000 synthetic failed-payment events** for the RecoverAI hackathon demo. It contains no actual Razorpay, merchant, or customer data.

| File | Rows | Use |
| --- | ---: | --- |
| `recovery_train_synthetic.csv` | 300,000 | Fit models |
| `recovery_validation_synthetic.csv` | 60,000 | Keep untouched for evaluation |
| `dataset_manifest.json` | - | Schema and generation metadata |
| `error_codes.json` | 12 entries | RAG / safe action explanation reference |
| `guardrail_test_cases.csv` | 16 cases | Deterministic policy-engine tests |

## Modelling contract

- **Outcome:** `recovered_within_72h`
- **Action/treatment:** `treatment_action`
- **Treatment propensity:** `treatment_propensity`
- **Propensity model:** exclude `treatment_action` and `treatment_propensity` along with identifiers and post-action fields.
- **Uplift model:** use the pre-action features, `treatment_action`, `treatment_propensity`, and `recovered_within_72h`.

Never use `recovery_delay_minutes` as a feature: it only exists after recovery and would leak the target.

## Safety / presentation statement

> Demo dataset generated from a documented simulation. Results are not Razorpay production performance.

The recovery actions are intentionally safe: fresh payment links, customer notification, smart delay, or human review. This dataset does not imply that a failed payment ID can be retried or that risk decisions can be overridden.

`error_codes.json` paraphrases official Razorpay payment-error guidance and links every entry to its source. `guardrail_test_cases.csv` is synthetic test data, not model-training data.

## Quality checks completed

- 31 fields in both files
- 0 duplicate training transaction IDs
- 0 notification actions assigned to opted-out customers
- All five actions represented in training and validation splits
