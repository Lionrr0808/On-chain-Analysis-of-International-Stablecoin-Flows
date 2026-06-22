# Hierarchical GBDT Model for Wallet Region Classification

## 📋 Overview

This document describes the implementation and performance of a hierarchical Gradient Boosted Decision Tree (GBDT) model for predicting the geographic region of cryptocurrency wallets. The model follows the approach described in the paper, using a three-level hierarchical classification strategy with inverse frequency weighting to address class imbalance.

---

## 🏗️ Model Architecture

The hierarchical classification pipeline consists of three levels:

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

### Classification Levels

| Level | Task | Classes |
|-------|------|---------|
| **Level 1** | Coarse Classification | NA_LAC, AME_Europe, Asia |
| **Level 2** | Fine Classification | North America, Latin America and Caribbean |
| **Level 3** | Fine Classification | Africa and Middle East, Europe |

---

## 🔧 Implementation Details

### Key Features

#### 1. Inverse Frequency Weighting
Each observation is weighted inversely proportional to its class frequency, ensuring underrepresented classes contribute equally to the estimation process (as described in the paper).

```python
def _compute_inverse_frequency_weights(self, y):
    classes = np.unique(y)
    class_counts = np.array([np.sum(y == cls) for cls in classes])
    total_samples = len(y)
    n_classes = len(classes)
    
    # weight = total_samples / (n_classes * class_count)
    class_weights = total_samples / (n_classes * class_counts)
    
    sample_weights = np.zeros(len(y))
    for cls, weight in zip(classes, class_weights):
        sample_weights[y == cls] = weight
    
    # Normalize to sum to total_samples
    sample_weights = sample_weights * (total_samples / np.sum(sample_weights))
    return sample_weights
```

#### 2. Feature Penalty
A penalty factor of **0.1** is applied to `top1_cex_region` and `top2_cex_region` features to reduce over-reliance on centralized exchange regional information and encourage the model to learn from other behavioral features.

#### 3. Hierarchical Classification
The three-level approach maximizes the usefulness of time-of-day features by grouping regions that share similar time zones.

### Model Parameters

| Parameter | Level 1 | Level 2 | Level 3 |
|-----------|---------|---------|---------|
| `n_estimators` | 50 | 50 | 50 |
| `learning_rate` | 0.06 | 0.06 | 0.06 |
| `max_depth` | 8 | 6 | 6 |
| `min_samples_split` | 20 | 20 | 20 |
| `min_samples_leaf` | 10 | 10 | 10 |
| `subsample` | 0.8 | 0.8 | 0.8 |
| `max_features` | None | 'sqrt' | None |
| `random_state` | 42 | 42 | 42 |

### Dataset Statistics

| Metric | Value |
|--------|-------|
| Total samples | 23,314 |
| Training set | 20,982 samples (90%) |
| Test set | 2,332 samples (10%) |
| Validation set | 4,197 samples (20% of training) |
| Total features | 62 |
| Target classes | 5 |

### Class Distribution

| Region | Count | Percentage |
|--------|-------|------------|
| Asia and Pacific | 9,995 | 42.9% |
| Europe | 5,769 | 24.7% |
| North America | 4,818 | 20.7% |
| Africa and Middle East | 1,465 | 6.3% |
| Latin America and Caribbean | 1,267 | 5.4% |

### Feature Penalty Configuration

| Feature | Penalty Factor | Reduction |
|---------|---------------|-----------|
| `top1_cex_region` | 0.1 | 90% |
| `top2_cex_region` | 0.08 | 92% |

---

## 📊 Model Performance

### Level-wise Training Performance

| Level | Classes | Training Accuracy | Validation Accuracy | Training Time |
|-------|---------|------------------|---------------------|---------------|
| Level 1 | 3-class coarse | **84.97%** | **78.39%** | 35.14s |
| Level 2 | NA vs LAC | **81.94%** | **79.36%** | 0.41s |
| Level 3 | AME vs Europe | **84.79%** | **75.67%** | 2.51s |

### Level-wise Class Distribution and Weights

#### Level 1 (Coarse Classification)

| Class | Training Samples | Percentage | Avg Weight |
|-------|-----------------|------------|------------|
| AME_Europe | 5,208 | 31.0% | 1.074 |
| Asia | 7,196 | 42.9% | 0.778 |
| NA_LAC | 4,381 | 26.1% | 1.277 |

#### Level 2 (NA vs LAC)

| Class | Training Samples | Percentage | Avg Weight |
|-------|-----------------|------------|------------|
| Latin America and Caribbean | 912 | 20.8% | 2.402 |
| North America | 3,469 | 79.2% | 0.631 |

#### Level 3 (AME vs Europe)

| Class | Training Samples | Percentage | Avg Weight |
|-------|-----------------|------------|------------|
| Africa and Middle East | 1,055 | 20.3% | 2.468 |
| Europe | 4,153 | 79.7% | 0.627 |

---

## 📈 Test Set Performance

### Overall Metrics

| Metric | Value |
|--------|-------|
| **Accuracy** | **72.17%** |
| Macro F1 Score | 0.6222 |
| Weighted F1 Score | 0.7369 |

### Detailed Classification Report

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Africa and Middle East | 0.32 | 0.53 | 0.40 | 146 |
| Asia and Pacific | 0.85 | 0.80 | 0.83 | 1,000 |
| Europe | 0.64 | 0.64 | 0.64 | 577 |
| Latin America and Caribbean | 0.32 | 0.47 | 0.38 | 127 |
| North America | 0.97 | 0.78 | 0.86 | 482 |

### Per-Class Performance (Row-Normalized)

| True Region | Accuracy | Most Confused With | Confusion Rate |
|-------------|----------|-------------------|----------------|
| Africa and Middle East | **53.42%** (78/146) | Europe | 27.4% |
| Asia and Pacific | **80.40%** (804/1000) | Europe | 10.2% |
| Europe | **63.60%** (367/577) | Africa and Middle East | 14.0% |
| Latin America and Caribbean | **47.24%** (60/127) | Europe | 20.5% |
| North America | **77.59%** (374/482) | Europe | 7.5% |

---

## 📊 Confusion Matrix

The confusion matrix displays the true region in the rows and the predicted region in the columns. The data has been normalized such that **all rows add up to 100%**.

| True Region | Africa and Middle East | Asia and Pacific | Europe | Latin America and Caribbean | North America |
|-------------|----------------------|------------------|--------|----------------------------|---------------|
| **Africa and Middle East** | **53.4** | 11.6 | 27.4 | 7.5 | 0.0 |
| **Asia and Pacific** | 4.8 | **80.4** | 10.2 | 3.8 | 0.8 |
| **Europe** | 14.0 | 13.7 | **63.6** | 8.5 | 0.2 |
| **Latin America and Caribbean** | 11.8 | 18.9 | 20.5 | **47.2** | 1.6 |
| **North America** | 4.8 | 4.4 | 7.5 | 5.8 | **77.8** |

---

## 🎯 Feature Importance Analysis

### Top 10 Most Important Features (Level 1)

| Rank | Feature | Importance | Penalized |
|------|---------|------------|-----------|
| 1 | `top1_cex_region` | 0.4503 | ✅ (90% reduction) |
| 2 | `night_ratio` | 0.1358 | ❌ |
| 3 | `tx_hour_variance` | 0.0693 | ❌ |
| 4 | `pct_poly_c1` | 0.0466 | ❌ |
| 5 | `top1_5_cex_region_diversity` | 0.0383 | ❌ |
| 6 | `early_morning_ratio` | 0.0315 | ❌ |
| 7 | `top1_cex_count` | 0.0194 | ❌ |
| 8 | `wallet_age_days` | 0.0120 | ❌ |
| 9 | `pct_poly_c2` | 0.0113 | ❌ |
| 10 | `top1_5_cex_total_count` | 0.0112 | ❌ |

### Feature Category Importance

| Category | Key Features | Total Importance |
|----------|-------------|------------------|
| **CEX Features** | top1_cex_region, top1_5_cex_region_diversity, top1_cex_count | ~0.52 |
| **Time Distribution** | pct_poly_c1, pct_poly_c2, pct_poly_c3 | ~0.06 |
| **Time Ratio** | night_ratio, early_morning_ratio | ~0.17 |
| **DST Features** | tx_hour_variance | ~0.07 |

---

## 🔍 Key Observations

### Strengths

1. **Effective Coarse Classification**: Level 1 achieves 78.39% validation accuracy with only 50 trees
2. **Strong Asia Recognition**: 80.40% accuracy with low misclassification rate
3. **Excellent North America Precision**: 0.97 precision score
4. **Balanced Handling of Minority Classes**: Inverse frequency weighting successfully improved recall for underrepresented regions (Africa and Middle East: 0.53, Latin America: 0.47)

### Challenges

1. **Africa and Middle East vs Europe Confusion**: 27.4% of African/Middle Eastern wallets misclassified as Europe
2. **Latin America Challenges**: Only 47.24% accuracy with significant confusion with Europe (20.5%)
3. **Europe Classification**: Moderate performance (63.6%) with confusion across multiple regions

### Effect of Feature Penalty

- `top1_cex_region` still ranks #1 in importance despite 90% reduction
- This indicates CEX region is a very strong predictor, but the model is now forced to use other features as well
- Time-based features (`night_ratio`, `tx_hour_variance`) have gained relative importance

---

## 📁 Files Generated

| File | Description |
|------|-------------|
| `confusion_matrix_normalized.png` | Row-normalized confusion matrix visualization |
| `feature_importance_with_penalties.png` | Feature importance plot with penalized features highlighted in orange |

---

## 💻 Usage

### Training the Model

```python
# Train with default parameters
model, X_train, X_test, y_train, y_test = train_model(
    'training_data_final_kept.csv',
    test_size=0.1,
    val_size=0.2,
    cex_penalty=0.1  # 90% reduction for CEX features
)
```

### Adjusting CEX Penalty

| `cex_penalty` | Effect | Use Case |
|---------------|--------|----------|
| 0.1 | 90% reduction | Strong CEX influence (recommended) |
| 0.3 | 70% reduction | Moderate CEX influence |
| 0.5 | 50% reduction | Mild CEX influence |
| 1.0 | No reduction | Baseline model |

---

## 📝 Summary

The hierarchical GBDT model achieves **72.17% overall accuracy** on the test set, with particularly strong performance on **Asia and Pacific** (80.40%) and **North America** (77.59%). The inverse frequency weighting mechanism effectively improves recall for underrepresented regions. The feature penalty on CEX region features helps the model rely more on behavioral and time-based features, while still leveraging CEX information when valuable. The model shows room for improvement in distinguishing between Europe and other regions, particularly Africa and Middle East.
