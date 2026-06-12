# Wallet Region Prediction Model - Feature Description Document

## Overview

This document describes the feature set used to train a Gradient Boosted Decision Tree (GBDT) model for predicting the geographic region of cryptocurrency wallets. The features are divided into 11 categories, totaling approximately 65 features.

### Target Label
- `final_label`: Geographic region of the wallet
  - `North America`
  - `Europe`
  - `Asia and Pacific`
  - `Africa and Middle East`
  - `Latin America and Caribbean`

---

## Feature Categories

### 1. Time Distribution Features (Polynomial Coefficients)

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `pct_poly_c0` | float | Constant term of 3rd degree polynomial of 24-hour transaction distribution | Fill with 0 |
| `pct_poly_c1` | float | 1st degree coefficient of 3rd degree polynomial | Fill with 0 |
| `pct_poly_c2` | float | 2nd degree coefficient of 3rd degree polynomial | Fill with 0 |
| `pct_poly_c3` | float | 3rd degree coefficient of 3rd degree polynomial | Fill with 0 |

**Description**: Fits the 24-hour transaction percentage to a 3rd degree polynomial. The 4 coefficients compress the original 24-dimensional features while preserving the shape information of activity time.

---

### 2. Transaction Amount Features

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `avg_transaction_amount_eth` | float | Average transaction amount (ETH) | Fill with 0 |
| `large_tx_ratio` | float | Ratio of large transactions (>1 ETH) | Fill with 0 |
| `micro_tx_ratio` | float | Ratio of micro transactions (<0.01 ETH) | Fill with 0 |

**Description**: Reflects users' economic behavior and transaction habits. Users in developed regions may have a tendency for large transactions.

---

### 3. Time Ratio Features

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `night_ratio` | float | Ratio of transactions during night hours (UTC 0-5) | Fill with 0 |
| `early_morning_ratio` | float | Ratio of transactions during early morning (UTC 0-3) | Fill with 0 |
| `daytime_ratio` | float | Ratio of transactions during daytime (UTC 8-20) | Fill with 0 |
| `weekend_ratio` | float | Ratio of transactions on weekends | Fill with 0 |

**Description**: Captures users' active time preferences. Activity patterns differ across time zones.

---

### 4. Seasonal/DST Features

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `avg_tx_hour_period1` | float | Average transaction hour during Mar 14 - Nov 7 | Fill with -1 |
| `avg_tx_hour_period2` | float | Average transaction hour during Nov 8 - Mar 13 | Fill with -1 |
| `avg_tx_hour_period3` | float | Average transaction hour during Mar 21 - Oct 31 | Fill with -1 |
| `avg_tx_hour_period4` | float | Average transaction hour during Nov 1 - Mar 10 | Fill with -1 |
| `tx_hour_variance` | float | Variance of transaction hour distribution (regularity) | Fill with -1 |

**Description**: Different regions have different adoption of Daylight Saving Time (DST). Seasonal behavior changes help distinguish North America/Europe from Asia.

---

### 5. Gas Fee Features

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `avg_gas_price` | float | Average gas price (Gwei) | Fill with 0 |
| `avg_tx_fee_eth` | float | Average transaction fee (ETH) | Fill with 0 |

**Description**: Users in developed regions may be willing to pay higher gas fees and are less price-sensitive.

---

### 6. Wallet Activity Features

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `wallet_age_days` | int | Wallet age (days since first transaction) | Fill with 0 |
| `active_days` | int | Number of days with at least one transaction | Fill with 0 |
| `avg_tx_per_day` | float | Average number of transactions per day | Fill with 0 |

**Description**: Reflects wallet activity level and lifespan. Mature users have more stable behavior patterns.

---

### 7. Protocol Usage Features

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `dex_count` | int | Number of DEX protocols used | Fill with 0 |
| `lending_count` | int | Number of lending protocols used | Fill with 0 |
| `nft_count` | int | Number of NFT marketplaces used | Fill with 0 |
| `bridge_count` | int | Number of cross-chain bridges used | Fill with 0 |

**Description**: Different regions have different preferences for DeFi, NFT, and other protocols, reflecting users' on-chain behavior patterns.

---

### 8. Top ERC-20 Token Features

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `top1_token` ~ `top5_token` | category | Token names ranked 1-5 by transaction count | Keep NaN (handled by GBDT) |
| `top1_token_count` ~ `top5_token_count` | int | Corresponding transaction counts | Fill with 0 |
| `top6_10_token_total_count` | int | Total transaction count of top6-10 tokens | Fill with 0 |
| `top6_10_token_diversity` | int | Number of unique tokens in top6-10 | Fill with 0 |
| `top6_10_token_ratio` | float | Ratio of top6-10 to total transactions | Fill with 0 |

**Description**: Token preference is an important signal for regional differences (e.g., Asia prefers USDT, Europe/America prefers USDC).

---

### 9. Top Namespace Features

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `top1_namespace` ~ `top5_namespace` | category | Namespace names ranked 1-5 by interaction count | Keep NaN (handled by GBDT) |
| `top1_namespace_count` ~ `top5_namespace_count` | int | Corresponding interaction counts | Fill with 0 |
| `top6_10_namespace_total_count` | int | Total interaction count of top6-10 namespaces | Fill with 0 |
| `top6_10_namespace_diversity` | int | Number of unique namespaces in top6-10 | Fill with 0 |
| `top6_10_namespace_ratio` | float | Ratio of top6-10 to total interactions | Fill with 0 |

**Namespace Types**: dex, lending, nft, bridge, yield, oracle, etc.

**Description**: Different regions have different preferences for DeFi, NFT, and other protocol categories.

---

### 10. CEX (Centralized Exchange) Features

| Feature Name | Type | Description | Missing Value Handling |
|--------------|------|-------------|------------------------|
| `top1_cex_region` | category | Region of the most frequently used CEX | Keep NaN (handled by GBDT) |
| `top1_cex_count` | int | Number of interactions with top1 CEX | Fill with 0 |
| `top2_cex_region` | category | Region of the second most frequently used CEX | Keep NaN (handled by GBDT) |
| `top2_cex_count` | int | Number of interactions with top2 CEX | Fill with 0 |
| `cex_interaction_type` | category | Type of CEX interaction | Fill with 'no_cex_interaction' |
| `top1_2_cex_total_count` | int | Total interactions with top1-2 CEXs | Fill with 0 |
| `top1_2_cex_region_diversity` | int | Number of unique CEX regions in top1-2 | Fill with 0 |
| `has_multiple_cex_regions` | int | Whether using CEXs from multiple regions (0/1) | Fill with 0 |
| `top3_5_cex_total_count` | int | Total interactions with top3-5 CEXs (aggregated) | Fill with 0 |
| `top3_5_cex_region_diversity` | int | Number of unique CEX regions in top3-5 (aggregated) | Fill with 0 |

**cex_interaction_type Values**:
- `cex_address`: The wallet itself is a CEX address
- `has_cex_interaction`: Has interactions with CEXs
- `no_cex_interaction`: No CEX interactions

**Description**: CEX regional preference is one of the strongest predictive signals. Users tend to use local or region-friendly exchanges.

---

## Feature Summary Statistics

| Category | Number of Features |
|----------|-------------------|
| Time Distribution Features | 4 |
| Transaction Amount Features | 3 |
| Time Ratio Features | 4 |
| Seasonal/DST Features | 5 |
| Gas Fee Features | 2 |
| Wallet Activity Features | 3 |
| Protocol Usage Features | 4 |
| Top Token Features | 15 |
| Top Namespace Features | 15 |
| CEX Features | 10 |
| **Total** | **65** |

---

## Missing Value Handling Strategy Summary

| Feature Type | Handling Method | Explanation |
|--------------|-----------------|-------------|
| Numerical features (with business meaning of zero) | Fill with `0` | e.g., transaction counts, count-based features |
| Numerical features (without business meaning of zero) | Fill with `-1` | e.g., hour-based, period-based features |
| Categorical features (CEX type) | Fill with `'no_cex_interaction'` | Clear business category |
| Other categorical features | Keep `NaN` | GBDT automatically handles missing values |

---

## Model Training Recommendations

```python
import lightgbm as lgb

# Categorical features list
categorical_features = [
    'top1_token', 'top2_token', 'top3_token', 'top4_token', 'top5_token',
    'top1_namespace', 'top2_namespace', 'top3_namespace', 'top4_namespace', 'top5_namespace',
    'top1_cex_region', 'top2_cex_region',
    'cex_interaction_type'
]

# Train the model
model = lgb.LGBMClassifier(
    categorical_feature=categorical_features,
    class_weight='balanced',  # Handle class imbalance
    verbose=-1
)
model.fit(X, y)
