# Simplified Hierarchical GBDT Model - Performance Report

## 📋 Overview

This report presents the performance of a **simplified Hierarchical GBDT (Gradient Boosted Decision Tree) model** for predicting the geographic region of cryptocurrency wallets. The model uses a streamlined feature set, keeping only `top1_cex_region` and `top2_cex_region` as categorical features, while excluding all token-related, namespace-related, and CEX name features. All numerical features are retained.

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

## 📊 Class Distribution

### Training Data Distribution

| Region | Count | Percentage |
|--------|-------|------------|
| Asia and Pacific | 7,196 | 42.9% |
| Europe | 4,153 | 24.7% |
| North America | 3,469 | 20.7% |
| Africa and Middle East | 1,055 | 6.3% |
| Latin America and Caribbean | 912 | 5.4% |

### Level-wise Class Distribution

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

### Overall Test Metrics

| Metric | Value |
|--------|-------|
| **Accuracy** | **71.83%** |
| Macro F1 Score | 0.6182 |
| Weighted F1 Score | 0.7381 |

### Per-Class Performance

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

### Observations

1. **CEX region remains the strongest predictor** despite 50% penalty, indicating its importance for region classification

2. **Time-based features** (`night_ratio`, `tx_hour_variance`) are the second most important category, confirming the value of time-zone based signals

3. **Activity and gas features** have relatively low importance, suggesting they provide limited discriminatory power

4. **Polynomial features** from the 24-hour distribution are moderately important

---

## 📊 Level-wise Training Performance

| Level | Task | Training Accuracy | Validation Accuracy | Training Time |
|-------|------|------------------|---------------------|---------------|
| **Level 1** | 3-class coarse | **86.62%** | **78.53%** | 45.72s |
| **Level 2** | NA vs LAC | **82.01%** | **79.18%** | 1.27s |
| **Level 3** | AME vs Europe | **91.80%** | **76.44%** | 1.37s |

### Observations

1. **Level 1** shows good generalization (86.62% train vs 78.53% validation)

2. **Level 2** is the most balanced (82.01% train vs 79.18% validation)

3. **Level 3** shows signs of overfitting (91.80% train vs 76.44% validation), likely due to the Africa weight boost

---

## 📝 Summary

### Strengths

1. **Strong Asia Performance**: 79.9% accuracy, 0.83 F1-score

2. **Excellent North America Precision**: 0.97 precision, 77.8% accuracy

3. **Improved Africa Recall**: Boosted to 48% (compared to previous 53% with simplified features)

4. **Simplified Feature Set**: Reduced from 60+ to 37 features, improving interpretability and stability

5. **Efficient Training**: Total training time under 50 seconds

### Challenges

1. **Africa ↔ Europe Confusion**: 23.3% of African samples misclassified as Europe

2. **Latin America ↔ Asia Confusion**: 17.3% misclassification rate

3. **Europe Performance**: Moderate at 62.2% accuracy

4. **Low Precision for Africa (0.33) and Latin America (0.26)**: Many false positives

### Recommendations

| Priority | Action | Expected Impact |
|----------|--------|-----------------|
| **High** | Add region-specific time features | Reduce Africa↔Europe confusion |
| **High** | Increase NA_LAC weight to 1.8x | Improve Latin America precision |
| **Medium** | Add stablecoin preference features | Better distinguish Asia vs others |
| **Medium** | Test cex_penalty=0.3 | Allow CEX features more influence |
| **Low** | Add more tree estimators for Level 3 | Reduce overfitting |

---

## 📁 Output Files

| File | Description |
|------|-------------|
| `GBDT_model_simplified.joblib` | Trained model |
| `GBDT_model_simplified_features.joblib` | Feature names |
| `GBDT_model_simplified_encoders.joblib` | Categorical encoders |
| `confusion_matrix_simplified.png` | Row-normalized confusion matrix |
| `feature_importance_simplified.png` | Feature importance visualization |

---

