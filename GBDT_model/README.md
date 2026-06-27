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

### Key Model Characteristics

| Feature | Description |
|---------|-------------|
| **Model Architecture** | 3-level hierarchical GBDT |
| **Total Features** | 37 (35 numerical + 2 categorical) |
| **Target Classes** | 5 regions |
| **Training Samples** | 16,785 |
| **Test Samples** | 2,332 |
| **Validation Split** | 20% of training data |
| **Feature Penalty** | top1_cex_region: 0.5 (50% reduction) |
| | top2_cex_region: 0.4 (60% reduction) |

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
| Asia and Pacific | 9,995 | 42.9% |
| Europe | 5,769 | 24.7% |
| North America | 4,818 | 20.7% |
| Africa and Middle East | 1,465 | 6.3% |
| Latin America and Caribbean | 1,267 | 5.4% |

### Level-wise Class Distribution and Weights

#### Level 1 (Coarse Classification)

| Class | Training Samples | Percentage | Avg Weight |
|-------|-----------------|------------|------------|
| AME_Europe | 5,208 | 31.0% | 0.921 |
| Asia | 7,196 | 42.9% | 0.666 |
| NA_LAC | 4,381 | 26.1% | 1.642 |

> **Note**: NA_LAC weight was boosted by **50%** to address class imbalance.

#### Level 2 (NA vs LAC)

| Class | Training Samples | Percentage | Avg Weight |
|-------|-----------------|------------|------------|
| Latin America and Caribbean | 912 | 20.8% | 2.402 |
| North America | 3,469 | 79.2% | 0.631 |

#### Level 3 (AME vs Europe)

| Class | Training Samples | Percentage | Avg Weight |
|-------|-----------------|------------|------------|
| Africa and Middle East | 1,055 | 20.3% | **3.702** |
| Europe | 4,153 | 79.7% | 0.627 |

> **Note**: Africa weight was boosted by **50%** to improve recall for the underrepresented African region.

---

## 📈 Model Performance

### Level-wise Training Performance

| Level | Task | Training Accuracy | Validation Accuracy | Training Time |
|-------|------|------------------|---------------------|---------------|
| **Level 1** | 3-class coarse | **86.62%** | **78.53%** | 45.72s |
| **Level 2** | NA vs LAC | **82.01%** | **79.18%** | 1.27s |
| **Level 3** | AME vs Europe | **91.80%** | **76.44%** | 1.37s |

### Overall Test Metrics

| Metric | Value |
|--------|-------|
| **Accuracy** | **71.83%** |
| Macro F1 Score | 0.6182 |
| Weighted F1 Score | 0.7381 |

### Per-Class Performance (Test Set)

| Region | Precision | Recall | F1-Score | Support |
|--------|-----------|--------|----------|---------|
| Africa and Middle East | 0.33 | **0.48** | 0.39 | 146 |
| Asia and Pacific | 0.85 | 0.80 | 0.83 | 1,000 |
| Europe | 0.69 | 0.62 | 0.65 | 577 |
| Latin America and Caribbean | 0.26 | **0.57** | 0.35 | 127 |
| North America | 0.97 | 0.78 | 0.86 | 482 |

### Key Observations

| Region | Observation |
|--------|-------------|
| **Africa and Middle East** | Improved recall (48%) due to 50% weight boost; precision remains low (33%) |
| **Latin America and Caribbean** | Improved recall (57%) with weight boost; precision is low (26%) |
| **North America** | Excellent precision (97%), good recall (78%) |
| **Asia and Pacific** | Strong performance across all metrics |
| **Europe** | Moderate performance; main source of confusion |

---

## 📊 Confusion Matrix (Row-Normalized to 100%)

The confusion matrix below displays the true region in the rows and the predicted region in the columns. All rows sum to 100%.

| True Region | Africa and Middle East | Asia and Pacific | Europe | Latin America and Caribbean | North America |
|-------------|----------------------|------------------|--------|----------------------------|---------------|
| **Africa and Middle East** | **47.9** | 11.6 | 23.3 | 17.1 | 0.0 |
| **Asia and Pacific** | 4.6 | **79.9** | 7.7 | 7.0 | 0.8 |
| **Europe** | 11.8 | 13.3 | **62.2** | 12.1 | 0.5 |
| **Latin America and Caribbean** | 8.7 | 17.3 | 15.7 | **56.7** | 1.6 |
| **North America** | 2.9 | 4.4 | 6.2 | 8.7 | **77.8** |

### Confusion Matrix Analysis

| True Region | Correctly Classified | Most Confused With | Confusion Rate |
|-------------|---------------------|-------------------|----------------|
| **Africa and Middle East** | 47.9% | Europe | 23.3% |
| **Asia and Pacific** | 79.9% | Europe | 7.7% |
| **Europe** | 62.2% | Africa and Middle East | 11.8% |
| **Latin America and Caribbean** | 56.7% | Asia and Pacific | 17.3% |
| **North America** | 77.8% | Latin America and Caribbean | 8.7% |

### Key Confusion Patterns

1. **Africa ↔ Europe**: 23.3% of African samples are misclassified as Europe, and 11.8% of European samples are misclassified as Africa

2. **Latin America ↔ Asia**: 17.3% of Latin American samples are misclassified as Asia and Pacific

3. **Latin America ↔ Europe**: 15.7% of Latin American samples are misclassified as Europe

4. **North America ↔ Latin America**: 8.7% of North American samples are misclassified as Latin America

---

## 🎯 Feature Importance Analysis

### Top 10 Most Important Features (Level 1)

| Rank | Feature | Importance | Penalized |
|------|---------|------------|-----------|
| 1 | `top1_cex_region` | **0.4852** | ✅ (50% reduction) |
| 2 | `night_ratio` | 0.1200 | ❌ |
| 3 | `tx_hour_variance` | 0.0759 | ❌ |
| 4 | `pct_poly_c1` | 0.0475 | ❌ |
| 5 | `early_morning_ratio` | 0.0376 | ❌ |
| 6 | `wallet_age_days` | 0.0165 | ❌ |
| 7 | `pct_poly_c3` | 0.0138 | ❌ |
| 8 | `weekend_ratio` | 0.0138 | ❌ |
| 9 | `avg_gas_price` | 0.0137 | ❌ |
| 10 | `avg_tx_per_day` | 0.0132 | ❌ |

### Feature Category Importance Analysis

| Category | Key Features | Total Importance |
|----------|-------------|------------------|
| **CEX Features** | top1_cex_region | **~0.49** |
| **Time Distribution** | night_ratio, early_morning_ratio, weekend_ratio | **~0.17** |
| **DST/Time Variance** | tx_hour_variance | **~0.08** |
| **Polynomial Features** | pct_poly_c1, pct_poly_c3 | **~0.06** |
| **Activity Features** | wallet_age_days, avg_tx_per_day | **~0.03** |
| **Gas Features** | avg_gas_price | **~0.01** |

### Key Observations

1. **CEX region remains the strongest predictor** despite 50% penalty, indicating its importance for region classification

2. **Time-based features** (`night_ratio`, `tx_hour_variance`) are the second most important category, confirming the value of time-zone based signals

3. **Activity and gas features** have relatively low importance, suggesting they provide limited discriminatory power

---

## 📊 Classification Results (602,840 Wallets)

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
| **Europe** | 424,848 | **70.5%** |
| **Asia and Pacific** | 98,895 | **16.4%** |
| **North America** | 35,318 | **5.9%** |
| **Africa and Middle East** | 22,437 | **3.7%** |
| **Latin America and Caribbean** | 21,342 | **3.5%** |
| **TOTAL** | **602,840** | **100.0%** |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Most common | Europe (70.5%) |
| Least common | Latin America and Caribbean (3.5%) |
| Range | 66.9% |
| Diversity Index (Simpson) | 0.4704 |

### By CEX Interaction Type

#### `has_cex_interaction` (17,459 wallets)

| Region | Count | Percentage |
|--------|-------|------------|
| Asia and Pacific | 5,588 | 32.0% |
| Europe | 3,547 | 20.3% |
| Latin America and Caribbean | 3,518 | 20.2% |
| Other | 4,806 | 27.5% |

#### `no_cex_interaction` (585,345 wallets)

| Region | Count | Percentage |
|--------|-------|------------|
| Europe | 421,291 | **72.0%** |
| Asia and Pacific | 93,295 | 15.9% |
| North America | 31,961 | 5.5% |
| Other | 38,798 | 6.6% |

#### `cex_address` (36 wallets - Direct Assignment)

| Region | Count | Percentage |
|--------|-------|------------|
| Asia and Pacific | 12 | 33.3% |
| Europe | 10 | 27.8% |
| Latin America and Caribbean | 8 | 22.2% |
| Other | 6 | 16.7% |

---

## 📊 Probability Aggregation Results

### Overall Distribution (All Wallets)

| Region | Sum Probability | Percentage |
|--------|-----------------|------------|
| **Europe** | 249,567.3 | **41.4%** |
| **Asia and Pacific** | 155,476.5 | **25.8%** |
| **Africa and Middle East** | 77,700.9 | **12.9%** |
| **North America** | 70,382.2 | **11.7%** |
| **Latin America and Caribbean** | 49,713.0 | **8.2%** |
| **TOTAL** | **602,840.0** | **100.0%** |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Most common | Europe (41.4%) |
| Least common | Latin America and Caribbean (8.2%) |
| Range | 33.2% |

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
| Europe | 249,557.3 | **41.4%** |
| Asia and Pacific | 155,464.5 | **25.8%** |
| Africa and Middle East | 77,697.9 | **12.9%** |
| North America | 70,379.2 | **11.7%** |
| Latin America and Caribbean | 49,705.0 | **8.2%** |
| **TOTAL** | **602,804.0** | **100.0%** |

---

## 📊 Hard Classification vs Probability Aggregation

| Region | Hard Classification | Probability Aggregation | Difference | Assessment |
|--------|-------------------|------------------------|------------|------------|
| **Europe** | 70.5% | 41.4% | **-29.1%** | Hard classification overestimates Europe |
| **Asia and Pacific** | 16.4% | 25.8% | **+9.4%** | Probability gives more realistic estimate |
| **Africa and Middle East** | 3.7% | 12.9% | **+9.2%** | Probability better captures uncertainty |
| **North America** | 5.9% | 11.7% | **+5.8%** | Probability improves North America estimate |
| **Latin America and Caribbean** | 3.5% | 8.2% | **+4.7%** | Probability improves Latin America estimate |

### Key Observations

1. **Hard classification significantly overestimates Europe** (70.5% vs 41.4%), indicating the model is overly confident in assigning wallets to Europe

2. **Probability aggregation provides more balanced and realistic estimates** for all regions

3. **Asia and Pacific emerges as the second largest region** (25.8%) when using probability aggregation, which aligns with stablecoin usage patterns

4. **Underrepresented regions (Africa, Latin America, North America) all show higher percentages** in probability aggregation, better reflecting their true distribution

---

## 🎯 Regional Distribution by CEX Interaction Type

### `has_cex_interaction` (17,459 wallets)

| Region | Hard Count | Hard % |
|--------|-----------|--------|
| Asia and Pacific | 5,588 | 32.0% |
| Europe | 3,547 | 20.3% |
| Latin America and Caribbean | 3,518 | 20.2% |
| Other | 4,806 | 27.5% |

### `no_cex_interaction` (585,345 wallets)

| Region | Hard Count | Hard % |
|--------|-----------|--------|
| Europe | 421,291 | **72.0%** |
| Asia and Pacific | 93,295 | 15.9% |
| North America | 31,961 | 5.5% |
| Other | 38,798 | 6.6% |

### Key Observations

1. **`no_cex_interaction` wallets** are overwhelmingly predicted as Europe (72.0%), suggesting that wallets without CEX interactions are defaulting to Europe

2. **`has_cex_interaction` wallets** show more balanced distribution, with Asia and Pacific (32.0%) as the largest region

3. **The small `cex_address` sample** (36 wallets) shows a more diverse distribution, with Asia and Pacific (33.3%) being the most common

---

## 📁 Output Files

| File | Description |
|------|-------------|
| `GBDT_model_simplified.joblib` | Trained model |
| `GBDT_model_simplified_features.joblib` | Feature names |
| `GBDT_model_simplified_encoders.joblib` | Categorical encoders |
| `confusion_matrix_simplified.png` | Row-normalized confusion matrix |
| `feature_importance_simplified.png` | Feature importance visualization |
| `predictions_with_probabilities.csv` | Complete predictions with probability scores |
| `region_distribution_summary_with_probs.csv` | Summary statistics comparing hard classification and probability aggregation |

---

## 💡 Recommendations

| Priority | Recommendation | Rationale |
|----------|----------------|-----------|
| **High** | **Use probability aggregation for final results** | Provides more stable and realistic estimates; reduces the 29% overestimation of Europe |
| **High** | **Calibrate model to reduce Europe over-prediction** | Hard classification shows 70.5% Europe, which is likely unrealistic |
| **High** | **Add region-specific features for `no_cex_interaction` wallets** | These wallets default to Europe; additional features could improve discrimination |
| **Medium** | **Increase NA_LAC weight to 1.8x** | Improve Latin America precision |
| **Medium** | **Add stablecoin preference features** | Better distinguish Asia vs others |
| **Medium** | **Test cex_penalty=0.3** | Allow CEX features more influence |
| **Low** | **Add more tree estimators for Level 3** | Reduce overfitting |

---

*Report completed on: 2024-06-27*
