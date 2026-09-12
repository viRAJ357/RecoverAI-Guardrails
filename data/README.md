# RecoverAI Financial Transaction Dataset

This directory contains **360,000 payment failure records** (derived from the Kaggle PaySim Mobile Money Benchmark) used for training and evaluating the RecoverAI ML policy engine.

| File | Rows | Description |
| --- | ---: | --- |
| `recovery_train.csv` | 300,000 | Primary training dataset for CatBoost & ML models |
| `recovery_val.csv` | 60,000 | Evaluation and validation dataset |
| `dataset_manifest.json` | - | Schema and dataset metadata |
| `real_paysim_dataset_manifest.json` | - | PaySim mapping specification & academic citation manifest |
| `error_codes.json` | 12 entries | Payment failure error codes and recovery strategy mappings |
| `guardrail_test_cases.csv` | 16 cases | Deterministic policy-engine safety test scenarios |

## Modelling Contract

- **Outcome Variable:** `recovered_within_72h` (Binary: 0 or 1)
- **Treatment Action:** `treatment_action` (`smart_retry`, `smart_delay`, `payment_link`, `notify_payment_link`, `human_review`)
- **Key Features:** 26 engineered attributes covering payment method, bank routing, error reason, customer segment, risk score, and transaction history.

## Data Integrity & Quality Checks

- Exactly 31 feature columns in training and validation splits
- 0 missing or null values
- 0 duplicate transaction IDs
- Full balance across error categories and recovery strategies
