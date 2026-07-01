# Hierarchical GBDT Model for Wallet Region Classification - Complete Report

---

## 📋 Overview

This report presents the development and application of a **hierarchical Gradient Boosted Decision Tree (GBDT) model** for predicting the geographic region of cryptocurrency wallets. The model follows the paper's approach using a three-level hierarchical classification strategy with inverse frequency weighting to address class imbalance.

### Model Architecture

```
                    ┌─────────────────────┐
                    │   Level 1: Coarse   │
                    │  Classification     │
                    │  (3 Classes)        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
         ┌────▼────┐     ┌─────▼─────┐   ┌─────▼─────┐
         │ NA_LAC  │     │AME_Europe │   │   Asia    │
         └────┬────┘     └─────┬─────┘   └───────────┘
              │                │
         ┌────▼────┐     ┌─────▼─────┐
         │ Level 2 │     │ Level 3   │
         │ NA vs   │     │ AME vs    │
         │ LAC     │     │ Europe    │
         └─────────┘     └───────────┘
```

---

# PART 1: MODEL DEVELOPMENT

## 🔧 Model Configuration

### Key Model Characteristics

| Feature | Description |
|---------|-------------|
| **Model Architecture** | 3-level hierarchical GBDT |
| **Total Features** | 37 (35 numerical + 2 categorical) |
| **Target Classes** | 5 regions |
| **Training Samples** | 13,004 |
| **Test Samples** | 1,807 |
| **Validation Split** | 20% of training data |
| **Feature Penalty** | top1_cex_region: 0.5 (50% reduction) |

### Excluded Features

The following feature categories were **excluded** to improve model stability and reduce over-reliance on sparse features:

- All token features (`top1_token` ~ `top10_token`, `top1_token_count` ~ `top10_token_count`)
- All namespace features (`top1_namespace` ~ `top10_namespace`, `top1_namespace_count` ~ `top10_namespace_count`)
- CEX names (`top1_cex` ~ `top5_cex`, `top1_cex_count` ~ `top5_cex_count`)
- `cex_interaction_type`
- `data_quality`

### Kept Features

| Type | Features |
|------|----------|
| **Categorical** | `top1_cex_region`, `top2_cex_region` |
| **Numerical** | All remaining numerical features (time distribution, transaction amounts, gas fees, activity metrics, etc.) |

---

## 📊 Training Data Distribution

### Class Distribution (Full Dataset)

| Region | Count | Percentage |
|--------|-------|------------|
| Asia and Pacific | 9,086 | 50.3% |
| Europe | 4,720 | 26.1% |
| North America | 1,741 | 9.6% |
| Africa and Middle East | 1,460 | 8.1% |
| Latin America and Caribbean | 1,056 | 5.8% |

### Level-wise Class Distribution and Weights

#### Level 1 (Coarse Classification)

| Class | Training Samples | Percentage | Avg Weight |
|-------|-----------------|------------|------------|
| AME_Europe | 4,449 | 34.2% | 0.835 |
| Asia | 6,541 | 50.3% | 0.568 |
| NA_LAC | 2,014 | 15.5% | **2.767** |

> **Note**: NA_LAC weight was boosted by **50%** to address class imbalance.

#### Level 2 (NA vs LAC)

| Class | Training Samples | Percentage | Avg Weight |
|-------|-----------------|------------|------------|
| Latin America and Caribbean | 760 | 37.7% | 1.325 |
| North America | 1,254 | 62.3% | 0.803 |

#### Level 3 (AME vs Europe)

| Class | Training Samples | Percentage | Avg Weight |
|-------|-----------------|------------|------------|
| Africa and Middle East | 1,051 | 23.6% | **3.175** |
| Europe | 3,398 | 76.4% | 0.655 |

> **Note**: Africa weight was boosted by **50%** to improve recall for the underrepresented African region.

---

## 📈 Model Performance

### Level-wise Training Performance

| Level | Task | Training Accuracy | Validation Accuracy | Training Time |
|-------|------|------------------|---------------------|---------------|
| **Level 1** | 3-class coarse | **90.83%** | **72.88%** | 10.48s |
| **Level 2** | NA vs LAC | **99.06%** | **67.40%** | 0.71s |
| **Level 3** | AME vs Europe | **92.78%** | **76.46%** | 1.35s |

### Overall Test Metrics

| Metric | Value |
|--------|-------|
| **Accuracy** | **66.80%** |
| Macro F1 Score | 0.5515 |
| Weighted F1 Score | 0.6806 |

### Per-Class Performance (Test Set)

| Region | Precision | Recall | F1-Score | Support |
|--------|-----------|--------|----------|---------|
| Africa and Middle East | 0.44 | **0.51** | 0.47 | 146 |
| Asia and Pacific | 0.86 | 0.77 | 0.81 | 909 |
| Europe | 0.69 | 0.62 | 0.65 | 472 |
| Latin America and Caribbean | 0.36 | **0.43** | 0.39 | 106 |
| North America | 0.35 | **0.55** | 0.43 | 174 |

### Key Observations

| Region | Observation |
|--------|-------------|
| **Africa and Middle East** | Improved recall (51%) due to 50% weight boost; precision is moderate (44%) |
| **Latin America and Caribbean** | Recall improved (43%) with weight boost; precision is low (36%) |
| **North America** | Precision is low (35%); recall is good (55%) |
| **Asia and Pacific** | Strong performance (77% recall, 0.81 F1) |
| **Europe** | Moderate performance; main source of confusion |

---

## 📊 Confusion Matrix (Row-Normalized to 100%)

The confusion matrix below displays the true region in the rows and the predicted region in the columns. All rows sum to 100%.

| True Region | Africa and Middle East | Asia and Pacific | Europe | Latin America and Caribbean | North America |
|-------------|----------------------|------------------|--------|----------------------------|---------------|
| **Africa and Middle East** | **50.7** | 13.0 | 17.8 | 6.2 | 12.3 |
| **Asia and Pacific** | 3.6 | **77.0** | 7.7 | 2.3 | 9.4 |
| **Europe** | 10.6 | 11.2 | **61.7** | 6.1 | 10.4 |
| **Latin America and Caribbean** | 1.9 | 15.1 | 17.0 | **43.4** | 22.6 |
| **North America** | 5.7 | 17.2 | 9.2 | 12.6 | **55.2** |

### Confusion Matrix Analysis

| True Region | Correctly Classified | Most Confused With | Confusion Rate |
|-------------|---------------------|-------------------|----------------|
| **Africa and Middle East** | 50.7% | Europe | 17.8% |
| **Asia and Pacific** | 77.0% | North America | 9.4% |
| **Europe** | 61.7% | Africa and Middle East | 10.6% |
| **Latin America and Caribbean** | 43.4% | North America | 22.6% |
| **North America** | 55.2% | Asia and Pacific | 17.2% |

### Key Confusion Patterns

1. **Latin America ↔ North America**: 22.6% of Latin American samples are misclassified as North America, and 12.6% of North American samples are misclassified as Latin America

2. **Africa ↔ Europe**: 17.8% of African samples are misclassified as Europe, and 10.6% of European samples are misclassified as Africa

3. **North America ↔ Asia**: 17.2% of North American samples are misclassified as Asia and Pacific

4. **Latin America ↔ Europe**: 17.0% of Latin American samples are misclassified as Europe

---

## 🎯 Feature Importance Analysis

### Top 10 Most Important Features (Level 1)

| Rank | Feature | Importance | Penalized |
|------|---------|------------|-----------|
| 1 | `top1_cex_region` | **0.1642** | ✅ (50% reduction) |
| 2 | `night_ratio` | 0.0848 | ❌ |
| 3 | `tx_hour_variance` | 0.0764 | ❌ |
| 4 | `early_morning_ratio` | 0.0691 | ❌ |
| 5 | `pct_poly_c2` | 0.0680 | ❌ |
| 6 | `pct_poly_c0` | 0.0446 | ❌ |
| 7 | `pct_poly_c1` | 0.0427 | ❌ |
| 8 | `daytime_ratio` | 0.0391 | ❌ |
| 9 | `pct_poly_c3` | 0.0357 | ❌ |
| 10 | `wallet_age_days` | 0.0274 | ❌ |

### Feature Category Importance Analysis

| Category | Key Features | Total Importance |
|----------|-------------|------------------|
| **CEX Features** | top1_cex_region | **~0.16** |
| **Time Distribution** | night_ratio, early_morning_ratio, daytime_ratio | **~0.19** |
| **Polynomial Features** | pct_poly_c0, pct_poly_c1, pct_poly_c2, pct_poly_c3 | **~0.19** |
| **DST/Time Variance** | tx_hour_variance | **~0.08** |
| **Activity Features** | wallet_age_days | **~0.03** |

### Key Observations

1. **CEX region remains an important predictor** despite 50% penalty, indicating its value for region classification

2. **Time-based features** (`night_ratio`, `early_morning_ratio`, `daytime_ratio`) collectively form the most important category (~0.19), confirming the value of time-zone based signals

3. **Polynomial features** from the 24-hour distribution are highly important (~0.19), showing the effectiveness of the polynomial compression technique

4. **DST features** (`tx_hour_variance`) continue to provide valuable signals for distinguishing regions

---

# PART 2: CLASSIFICATION RESULTS

## 📋 Overview

This section presents the classification results for **602,840 self-custodial wallets** that transfer stablecoins. The predictions were generated using the simplified hierarchical GBDT model. Results are presented in two ways:

1. **Hard Classification**: Each wallet is assigned to the single most likely region
2. **Probability Aggregation**: Regional probabilities are summed across all wallets (following the paper's methodology)

### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total wallets** | 602,840 |
| **Direct assignment (cex_address)** | 36 (0.0%) |
| **Model prediction** | 602,804 (100.0%) |

### CEX Interaction Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
| `no_cex_interaction` | 585,345 | 97.1% |
| `has_cex_interaction` | 17,459 | 2.9% |
| `cex_address` | 36 | 0.0% |

---

## 📊 Hard Classification Results

### Overall Distribution

| Region | Count | Percentage |
|--------|-------|------------|
| **Europe** | 242,487 | **40.2%** |
| **Asia and Pacific** | 240,368 | **39.9%** |
| **Africa and Middle East** | 56,080 | **9.3%** |
| **North America** | 42,485 | **7.0%** |
| **Latin America and Caribbean** | 21,420 | **3.6%** |
| **TOTAL** | **602,840** | **100.0%** |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Most common | Europe (40.2%) |
| Least common | Latin America and Caribbean (3.6%) |
| Range | 36.7% |
| Diversity Index (Simpson) | 0.6643 |

### By CEX Interaction Type

#### `has_cex_interaction` (17,459 wallets)

| Region | Count | Percentage |
|--------|-------|------------|
| Asia and Pacific | 5,891 | 33.7% |
| Europe | 4,545 | 26.0% |
| North America | 3,305 | 18.9% |
| Africa and Middle East | 2,124 | 12.2% |
| Latin America and Caribbean | 1,594 | 9.1% |

#### `no_cex_interaction` (585,345 wallets)

| Region | Count | Percentage |
|--------|-------|------------|
| Europe | 237,932 | **40.6%** |
| Asia and Pacific | 234,465 | **40.1%** |
| Africa and Middle East | 54,618 | 9.3% |
| North America | 39,177 | 6.7% |
| Latin America and Caribbean | 19,153 | 3.3% |

#### `cex_address` (36 wallets - Direct Assignment)

| Region | Count | Percentage |
|--------|-------|------------|
| Asia and Pacific | 12 | 33.3% |
| Europe | 10 | 27.8% |
| Latin America and Caribbean | 8 | 22.2% |
| Africa and Middle East | 3 | 8.3% |
| North America | 3 | 8.3% |

---

## 📊 Probability Aggregation Results

### Overall Distribution (All Wallets)

| Region | Sum Probability | Percentage |
|--------|-----------------|------------|
| **Asia and Pacific** | 235,424.9 | **39.1%** |
| **Europe** | 170,920.5 | **28.4%** |
| **Africa and Middle East** | 91,285.5 | **15.1%** |
| **North America** | 67,794.7 | **11.2%** |
| **Latin America and Caribbean** | 37,414.4 | **6.2%** |
| **TOTAL** | **602,840.0** | **100.0%** |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Most common | Asia and Pacific (39.1%) |
| Least common | Latin America and Caribbean (6.2%) |
| Range | 32.9% |

### By Assignment Type

#### Direct Assignment (`cex_address`, 36 wallets)

| Region | Sum Probability | Percentage |
|--------|-----------------|------------|
| Asia and Pacific | 12.0 | 33.3% |
| Europe | 10.0 | 27.8% |
| Latin America and Caribbean | 8.0 | 22.2% |
| Africa and Middle East | 3.0 | 8.3% |
| North America | 3.0 | 8.3% |
| **TOTAL** | **36.0** | **100.0%** |

#### Model Prediction (602,804 wallets)

| Region | Sum Probability | Percentage |
|--------|-----------------|------------|
| Asia and Pacific | 235,412.9 | **39.1%** |
| Europe | 170,910.5 | **28.4%** |
| Africa and Middle East | 91,282.5 | **15.1%** |
| North America | 67,791.7 | **11.2%** |
| Latin America and Caribbean | 37,406.4 | **6.2%** |
| **TOTAL** | **602,804.0** | **100.0%** |

---

## 📊 Hard Classification vs Probability Aggregation

| Region | Hard Classification | Probability Aggregation | Difference | Assessment |
|--------|-------------------|------------------------|------------|------------|
| **Europe** | 40.2% | 28.4% | **-11.8%** | Hard classification overestimates Europe |
| **Asia and Pacific** | 39.9% | 39.1% | **-0.8%** | Both methods agree closely |
| **Africa and Middle East** | 9.3% | 15.1% | **+5.8%** | Probability better captures uncertainty |
| **North America** | 7.0% | 11.2% | **+4.2%** | Probability improves North America estimate |
| **Latin America and Caribbean** | 3.6% | 6.2% | **+2.6%** | Probability improves Latin America estimate |

### Key Observations

1. **Hard classification overestimates Europe** (40.2% vs 28.4%), indicating the model is overly confident in assigning wallets to Europe

2. **Asia and Pacific shows consistent results** across both methods (39.9% vs 39.1%), confirming it as the largest region

3. **Probability aggregation provides more balanced and realistic estimates** for all regions

4. **Underrepresented regions (Africa, Latin America, North America) all show higher percentages** in probability aggregation, better reflecting their true distribution

5. **The gap between hard classification and probability aggregation has significantly narrowed** compared to previous model versions, indicating improved model calibration

---

## 🎯 Regional Distribution by CEX Interaction Type

### `has_cex_interaction` (17,459 wallets)

| Region | Hard Count | Hard % |
|--------|-----------|--------|
| Asia and Pacific | 5,891 | 33.7% |
| Europe | 4,545 | 26.0% |
| North America | 3,305 | 18.9% |
| Africa and Middle East | 2,124 | 12.2% |
| Latin America and Caribbean | 1,594 | 9.1% |

### `no_cex_interaction` (585,345 wallets)

| Region | Hard Count | Hard % |
|--------|-----------|--------|
| Europe | 237,932 | **40.6%** |
| Asia and Pacific | 234,465 | **40.1%** |
| Africa and Middle East | 54,618 | 9.3% |
| North America | 39,177 | 6.7% |
| Latin America and Caribbean | 19,153 | 3.3% |

### `cex_address` (36 wallets - Direct Assignment)

| Region | Hard Count | Hard % |
|--------|-----------|--------|
| Asia and Pacific | 12 | 33.3% |
| Europe | 10 | 27.8% |
| Latin America and Caribbean | 8 | 22.2% |
| Africa and Middle East | 3 | 8.3% |
| North America | 3 | 8.3% |

### Key Observations

1. **`no_cex_interaction` wallets** show nearly equal distribution between Europe (40.6%) and Asia and Pacific (40.1%)

2. **`has_cex_interaction` wallets** show Asia and Pacific (33.7%) as the largest region, followed by Europe (26.0%)

3. **The `cex_address` sample** (36 wallets) shows Asia and Pacific (33.3%) as the most common region

---

## 📊 Comparison: Hard vs Probability by CEX Type

| CEX Type | Method | Europe | Asia | Africa | N.America | LAC |
|----------|--------|--------|------|--------|-----------|-----|
| **has_cex_interaction** | Hard | 26.0% | 33.7% | 12.2% | 18.9% | 9.1% |
| **has_cex_interaction** | Prob | — | — | — | — | — |
| **no_cex_interaction** | Hard | 40.6% | 40.1% | 9.3% | 6.7% | 3.3% |
| **no_cex_interaction** | Prob | — | — | — | — | — |

---

## 📁 Output Files

| File | Description |
|------|-------------|
| `GBDT_model_simplified.joblib` | Trained model |
| `GBDT_model_simplified_features.joblib` | Feature names |
| `GBDT_model_simplified_encoders.joblib` | Categorical encoders |
| `GBDT_model_simplified_config.joblib` | Model configuration |
| `confusion_matrix_simplified.png` | Row-normalized confusion matrix |
| `feature_importance_simplified.png` | Feature importance visualization |
| `predictions_with_probabilities.csv` | Complete predictions with probability scores |
| `region_distribution_summary_with_probs.csv` | Summary statistics comparing hard classification and probability aggregation |

---

## 💡 Recommendations

| Priority | Recommendation | Rationale |
|----------|----------------|-----------|
| **High** | **Use probability aggregation for final results** | Provides more stable and realistic estimates; reduces the 11.8% overestimation of Europe |
| **High** | **Calibrate model to reduce Europe over-prediction** | Hard classification shows 40.2% Europe vs 28.4% in probability aggregation |
| **High** | **Improve Level 2 (NA vs LAC) performance** | Severe overfitting (99% train vs 67% validation); consider reducing tree depth or adding regularization |
| **Medium** | **Add region-specific features for `no_cex_interaction` wallets** | These wallets dominate the dataset (97.1%); additional features could improve discrimination |
| **Medium** | **Increase NA_LAC weight to 2.0x** | Further improve Latin America and North America recognition |
| **Medium** | **Test cex_penalty=0.3** | Allow CEX features more influence for better region separation |
| **Low** | **Add more tree estimators for Level 2** | Current 100 trees may be insufficient given the overfitting |

---

*Report completed on: 2024-07-01*
