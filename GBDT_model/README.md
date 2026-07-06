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
| **Test Samples** | 965 |
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
| **Accuracy** | **62.38%** |
| Macro F1 Score | 0.5830 |
| Weighted F1 Score | 0.6259 |

### Per-Class Performance (Test Set)

| Region | Precision | Recall | F1-Score | Support |
|--------|-----------|--------|----------|---------|
| Africa and Middle East | 0.52 | 0.52 | 0.52 | 146 |
| Asia and Pacific | 0.77 | 0.78 | 0.77 | 303 |
| Europe | 0.68 | 0.61 | 0.64 | 236 |
| Latin America and Caribbean | 0.39 | 0.44 | 0.41 | 106 |
| North America | 0.55 | 0.58 | 0.56 | 174 |

### Key Observations

| Region | Observation |
|--------|-------------|
| **Africa and Middle East** | Balanced precision and recall (0.52/0.52) |
| **Latin America and Caribbean** | Lower precision (0.39) and recall (0.44) |
| **North America** | Improved performance (0.55 precision, 0.58 recall) |
| **Asia and Pacific** | Strongest performance (0.77 F1) |
| **Europe** | Moderate performance (0.64 F1) |

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

1. **Latin America ↔ North America**: 22.6% of Latin American samples misclassified as North America

2. **Africa ↔ Europe**: 17.8% of African samples misclassified as Europe

3. **North America ↔ Asia**: 17.2% of North American samples misclassified as Asia

4. **Latin America ↔ Europe**: 17.0% of Latin American samples misclassified as Europe

---

## 🎯 Feature Importance Analysis

### Top 10 Most Important Features (Level 1)

| Rank | Feature | Importance | Penalized |
|------|---------|------------|-----------|
| 1 | `top1_cex_region` | **0.2498** | ✅ (50% reduction) |
| 2 | `tx_hour_variance` | 0.1286 | ❌ |
| 3 | `night_ratio` | 0.1104 | ❌ |
| 4 | `pct_poly_c1` | 0.0621 | ❌ |
| 5 | `early_morning_ratio` | 0.0500 | ❌ |
| 6 | `wallet_age_days` | 0.0240 | ❌ |
| 7 | `weekend_ratio` | 0.0240 | ❌ |
| 8 | `pct_poly_c3` | 0.0237 | ❌ |
| 9 | `micro_tx_ratio` | 0.0229 | ❌ |
| 10 | `avg_tx_per_day` | 0.0223 | ❌ |

### Feature Category Importance Analysis

| Category | Key Features | Total Importance |
|----------|-------------|------------------|
| **CEX Features** | top1_cex_region | **~0.25** |
| **DST/Time Variance** | tx_hour_variance | **~0.13** |
| **Time Distribution** | night_ratio, early_morning_ratio, weekend_ratio | **~0.18** |
| **Polynomial Features** | pct_poly_c1, pct_poly_c3 | **~0.09** |
| **Activity Features** | wallet_age_days, avg_tx_per_day | **~0.05** |

### Key Observations

1. **CEX region importance increased** (0.2498 vs 0.1642 in previous model) despite penalty

2. **DST features** (`tx_hour_variance`) are now the second most important feature

3. **Time-based features** remain crucial for region classification

4. **Activity features** have relatively low importance

---

# PART 2: CLASSIFICATION RESULTS

## 📋 Overview

This section presents the classification results for **934,792 self-custodial wallets** that transfer stablecoins. The predictions were generated using the simplified hierarchical GBDT model. Results are presented in two ways:

1. **Hard Classification**: Each wallet is assigned to the single most likely region
2. **Probability Aggregation**: Regional probabilities are summed across all wallets (following the paper's methodology)

### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total wallets** | 934,792 |
| **Direct assignment (cex_address)** | 79 (0.0%) |
| **Model prediction** | 892,992 (95.5%) |

### CEX Interaction Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
| `no_cex_interaction` | 892,992 | 95.5% |
| `has_cex_interaction` | 41,721 | 4.5% |
| `cex_address` | 79 | 0.0% |

---

## 📊 Hard Classification Results

### Overall Distribution

| Region | Count | Percentage |
|--------|-------|------------|
| **Europe** | 352,198 | **37.7%** |
| **Asia and Pacific** | 208,251 | **22.3%** |
| **Africa and Middle East** | 167,603 | **17.9%** |
| **North America** | 146,800 | **15.7%** |
| **Latin America and Caribbean** | 59,940 | **6.4%** |
| **TOTAL** | **934,792** | **100.0%** |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Most common | Europe (37.7%) |
| Least common | Latin America and Caribbean (6.4%) |
| Range | 31.3% |
| Diversity Index (Simpson) | 0.7475 |

### By CEX Interaction Type

#### `has_cex_interaction` (41,721 wallets)

| Region | Count | Percentage |
|--------|-------|------------|
| Asia and Pacific | 14,242 | 34.1% |
| Europe | 11,727 | 28.1% |
| North America | 9,364 | 22.4% |
| Africa and Middle East | 3,947 | 9.5% |
| Latin America and Caribbean | 2,441 | 5.9% |

#### `no_cex_interaction` (892,992 wallets)

| Region | Count | Percentage |
|--------|-------|------------|
| Europe | 340,440 | **38.1%** |
| Asia and Pacific | 193,985 | **21.7%** |
| Africa and Middle East | 164,583 | 18.4% |
| North America | 137,432 | 15.4% |
| Latin America and Caribbean | 56,552 | 6.3% |

#### `cex_address` (79 wallets - Direct Assignment)

| Region | Count | Percentage |
|--------|-------|------------|
| Europe | 31 | 39.2% |
| Asia and Pacific | 24 | 30.4% |
| Africa and Middle East | 10 | 12.7% |
| Latin America and Caribbean | 10 | 12.7% |
| North America | 4 | 5.1% |

---

## 📊 Probability Aggregation Results

### Overall Distribution (All Wallets)

| Region | Sum Probability | Percentage |
|--------|-----------------|------------|
| **Europe** | 247,949.8 | **26.5%** |
| **Asia and Pacific** | 244,306.1 | **26.1%** |
| **North America** | 173,502.0 | **18.6%** |
| **Africa and Middle East** | 162,670.8 | **17.4%** |
| **Latin America and Caribbean** | 106,363.4 | **11.4%** |
| **TOTAL** | **934,792.0** | **100.0%** |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Most common | Europe (26.5%) |
| Least common | Latin America and Caribbean (11.4%) |
| Range | 15.1% |

### By Assignment Type

#### Direct Assignment (`cex_address`, 79 wallets)

| Region | Sum Probability | Percentage |
|--------|-----------------|------------|
| Europe | 31.0 | 39.2% |
| Asia and Pacific | 24.0 | 30.4% |
| Africa and Middle East | 10.0 | 12.7% |
| Latin America and Caribbean | 10.0 | 12.7% |
| North America | 4.0 | 5.1% |
| **TOTAL** | **79.0** | **100.0%** |

#### Model Prediction (892,992 wallets)

| Region | Sum Probability | Percentage |
|--------|-----------------|------------|
| Europe | 236,191.8 | **26.4%** |
| Asia and Pacific | 230,040.1 | **25.8%** |
| North America | 164,134.0 | **18.4%** |
| Africa and Middle East | 159,650.8 | **17.9%** |
| Latin America and Caribbean | 102,975.4 | **11.5%** |
| **TOTAL** | **892,992.0** | **100.0%** |

---

## 📊 Before vs After Comparison

The following table shows the improvements between the previous model and the current model:

| Region | Before Hard % | After Hard % | Δ Hard | Before Prob % | After Prob % | Δ Prob |
|--------|--------------|--------------|--------|---------------|--------------|--------|
| **Africa and Middle East** | 9.30% | 17.93% | **+8.63pp** | 15.14% | 17.40% | **+2.26pp** |
| **Asia and Pacific** | 39.87% | 22.28% | **-17.59pp** | 39.05% | 26.13% | **-12.92pp** |
| **Europe** | 40.22% | 37.68% | **-2.54pp** | 28.35% | 26.52% | **-1.83pp** |
| **Latin America and Caribbean** | 3.55% | 6.41% | **+2.86pp** | 6.21% | 11.38% | **+5.17pp** |
| **North America** | 7.05% | 15.70% | **+8.65pp** | 11.25% | 18.56% | **+7.31pp** |

### Key Observations

1. **Significant improvement in North America**: +8.65pp in hard classification, +7.31pp in probability aggregation

2. **More balanced distribution**: The gap between largest and smallest regions decreased from 36.7% to 31.3%

3. **Africa improved substantially**: +8.63pp in hard classification

4. **Asia and Pacific decreased**: From 39.87% to 22.28%, resulting in a more realistic distribution

5. **Latin America improved**: +2.86pp in hard classification, +5.17pp in probability aggregation

---

## 📊 Hard Classification vs Probability Aggregation

| Region | Hard Classification | Probability Aggregation | Difference | Assessment |
|--------|-------------------|------------------------|------------|------------|
| **Europe** | 37.7% | 26.5% | **-11.2pp** | Hard overestimates Europe |
| **Asia and Pacific** | 22.3% | 26.1% | **+3.8pp** | Prob better captures uncertainty |
| **North America** | 15.7% | 18.6% | **+2.9pp** | Prob improves North America |
| **Africa and Middle East** | 17.9% | 17.4% | **-0.5pp** | Both methods agree closely |
| **Latin America and Caribbean** | 6.4% | 11.4% | **+5.0pp** | Prob significantly improves LAC |

---

## 📊 Regional Distribution by CEX Interaction Type

### `has_cex_interaction` (41,721 wallets)

| Region | Hard Count | Hard % |
|--------|-----------|--------|
| Asia and Pacific | 14,242 | 34.1% |
| Europe | 11,727 | 28.1% |
| North America | 9,364 | 22.4% |
| Africa and Middle East | 3,947 | 9.5% |
| Latin America and Caribbean | 2,441 | 5.9% |

### `no_cex_interaction` (892,992 wallets)

| Region | Hard Count | Hard % |
|--------|-----------|--------|
| Europe | 340,440 | **38.1%** |
| Asia and Pacific | 193,985 | **21.7%** |
| Africa and Middle East | 164,583 | 18.4% |
| North America | 137,432 | 15.4% |
| Latin America and Caribbean | 56,552 | 6.3% |

### `cex_address` (79 wallets - Direct Assignment)

| Region | Hard Count | Hard % |
|--------|-----------|--------|
| Europe | 31 | 39.2% |
| Asia and Pacific | 24 | 30.4% |
| Africa and Middle East | 10 | 12.7% |
| Latin America and Caribbean | 10 | 12.7% |
| North America | 4 | 5.1% |

### Key Observations

1. **`no_cex_interaction` wallets** show Europe (38.1%) as the largest region

2. **`has_cex_interaction` wallets** show Asia and Pacific (34.1%) as the largest region

3. **North America is more prominent in `has_cex_interaction`** (22.4%) compared to `no_cex_interaction` (15.4%)

4. **Africa and Middle East is more prominent in `no_cex_interaction`** (18.4%) compared to `has_cex_interaction` (9.5%)

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
| **High** | **Use probability aggregation for final results** | More stable and realistic estimates |
| **High** | **Continue improving North America recognition** | Still underestimated compared to expected |
| **Medium** | **Address Level 2 overfitting** | 99% train vs 67% validation |
| **Medium** | **Add region-specific features for `no_cex_interaction`** | These wallets dominate the dataset |
| **Medium** | **Test cex_penalty=0.3** | Allow CEX features more influence |
| **Low** | **Add more tree estimators for Level 2** | Current 100 trees may be insufficient |

---

*Report completed on: 2024-07-06*
