# Wallet Region Prediction Features Description

## 1. Basic Statistics

| Feature Name | Type | Description |
|--------------|------|-------------|
| `wallet` | STRING | Wallet address (lowercase format) |
| `total_transactions` | INT | Total number of transactions initiated by the wallet in one year |
| `total_volume_eth` | FLOAT | Total transaction volume in ETH over one year |
| `active_days` | INT | Number of days with at least one transaction |
| `unique_contracts` | INT | Number of unique contract addresses interacted with |
| `data_quality` | STRING | Data quality level: very_high / high / medium / low |

---

## 2. Transaction Amount Features

| Feature Name | Type | Description |
|--------------|------|-------------|
| `avg_transaction_amount_eth` | FLOAT | Average transaction amount in ETH |
| `median_transaction_amount_eth` | FLOAT | Median transaction amount in ETH |
| `p90_transaction_amount_eth` | FLOAT | 90th percentile of transaction amount in ETH |
| `large_tx_ratio` | FLOAT | Ratio of large transactions (>1 ETH) |
| `micro_tx_ratio` | FLOAT | Ratio of micro transactions (<0.01 ETH) |
| `zero_value_tx_ratio` | FLOAT | Ratio of zero-value transactions (token transfers only) |

---

## 3. Time Period Ratio Features

| Feature Name | Type | Description |
|--------------|------|-------------|
| `night_ratio` | FLOAT | Ratio of transactions during night hours (UTC 0-5) |
| `early_morning_ratio` | FLOAT | Ratio of transactions during early morning (UTC 0-3) |
| `daytime_ratio` | FLOAT | Ratio of transactions during daytime (UTC 8-20) |
| `weekend_ratio` | FLOAT | Ratio of transactions on weekends (Saturday + Sunday) |

---

## 4. 24-Hour Transaction Percentage (24 features)

| Feature Name | Type | Description |
|--------------|------|-------------|
| `pct_hour_0` ~ `pct_hour_23` | FLOAT | Percentage of transactions occurring in each UTC hour |
| | | Example: `pct_hour_8 = 0.15` means 15% of transactions occur between UTC 8:00-9:00 |

**Regional relevance**: Reflects the user's primary active time zone (e.g., Asian users may be active during UTC 0-4, corresponding to Beijing time 8-12)

---

## 5. Daylight Saving Time (DST) Features

| Feature Name | Type | Description |
|--------------|------|-------------|
| `dst_mode_hour` | INT | Most active UTC hour during DST period (March-October) |
| `non_dst_mode_hour` | INT | Most active UTC hour during non-DST period (November-February) |
| `tx_hour_variance` | FLOAT | Variance of transaction hour distribution (regularity of activity) |

**Regional relevance**: North America and Europe observe DST, while Asia does not. Changes in active hours during DST can help distinguish regions

---

## 6. Seasonal Period Average Transaction Time (6 periods)

| Feature Name | Type | Description |
|--------------|------|-------------|
| `avg_tx_hour_period1` | FLOAT | Average transaction hour during Mar 14 - Nov 7 |
| `avg_tx_hour_period2` | FLOAT | Average transaction hour during Nov 8 - Mar 13 |
| `avg_tx_hour_period3` | FLOAT | Average transaction hour during Mar 21 - Oct 31 |
| `avg_tx_hour_period4` | FLOAT | Average transaction hour during Nov 1 - Mar 10 |
| `avg_tx_hour_period5` | FLOAT | Average transaction hour during Oct 7 - Apr 6 |
| `avg_tx_hour_period6` | FLOAT | Average transaction hour during Apr 7 - Oct 6 |

**Regional relevance**: Different regions respond differently to DST and standard time; these periods capture seasonal behavioral changes

---

## 7. Gas Fee Features

| Feature Name | Type | Description |
|--------------|------|-------------|
| `avg_gas_price` | FLOAT | Average gas price (Gwei) |
| `median_gas_price` | FLOAT | Median gas price (Gwei) |
| `p90_gas_price` | FLOAT | 90th percentile of gas price (Gwei) |
| `gas_price_stddev` | FLOAT | Standard deviation of gas price (volatility) |
| `avg_tx_fee_eth` | FLOAT | Average transaction fee in ETH |

**Regional relevance**: Users in developed countries may be willing to pay higher gas fees and are less price-sensitive

---

## 8. Activity Features

| Feature Name | Type | Description |
|--------------|------|-------------|
| `avg_tx_per_day` | FLOAT | Average number of transactions per day |
| `days_since_last_tx` | INT | Days since the most recent transaction |
| `wallet_life_days` | INT | Wallet lifespan (days between first and last transaction) |
| `wallet_age_days` | INT | Wallet age (days since first transaction) |
| `unique_contracts_ratio` | FLOAT | Unique contracts / Total transactions (interaction diversity) |

---

## 9. Stablecoin Preference Features

| Feature Name | Type | Description |
|--------------|------|-------------|
| `usdt_count` | INT | Number of USDT contract interactions |
| `usdc_count` | INT | Number of USDC contract interactions |
| `dai_count` | INT | Number of DAI contract interactions |
| `stablecoin_diversity` | INT | Number of stablecoin types used (USDT/USDC/DAI) |
| `usdt_vs_usdc_ratio` | FLOAT | USDT interactions / USDC interactions |

**Regional relevance**: Asian users tend to prefer USDT, while North American/European users prefer USDC

---

## 10. Protocol Preference Features

| Feature Name | Type | Description |
|--------------|------|-------------|
| `dex_count` | INT | Number of DEX (Decentralized Exchange) interactions |
| `lending_count` | INT | Number of lending protocol interactions |
| `nft_count` | INT | Number of NFT marketplace interactions |
| `bridge_count` | INT | Number of cross-chain bridge interactions |
| `dex_ratio` | FLOAT | DEX interactions / Total protocol interactions |

**Regional relevance**: Different regions have different DeFi/NFT preferences; regions with stricter regulations may use more DEX

---

## 11. Top 10 ERC-20 Tokens (20 features)

| Feature Name | Type | Description |
|--------------|------|-------------|
| `top1_token` ~ `top10_token` | STRING | Token names ranked by transaction count (top 10) |
| `top1_token_count` ~ `top10_token_count` | INT | Corresponding transaction counts |

---

## 12. Top 10 Namespaces (20 features)

| Feature Name | Type | Description |
|--------------|------|-------------|
| `top1_namespace` ~ `top10_namespace` | STRING | Contract namespaces ranked by interaction count (top 10) |
| `top1_namespace_count` ~ `top10_namespace_count` | INT | Corresponding interaction counts |

**Namespace types**: dex (DEX), lending, nft (NFT marketplace), bridge (cross-chain bridge), yield (yield aggregator), oracle, etc.

---

## 13. Top 5 CEX (Centralized Exchanges) (16 features)

| Feature Name | Type | Description |
|--------------|------|-------------|
| `top1_cex` ~ `top5_cex` | STRING | Centralized exchange names ranked by interaction count (top 5) |
| `top1_cex_region` ~ `top5_cex_region` | STRING | Corresponding regions of those exchanges |
| `top1_cex_count` ~ `top5_cex_count` | INT | Corresponding interaction counts |
| `cex_interaction_type` | STRING | Type: `cex_address` (wallet is a CEX address) / `has_cex_interaction` / `no_cex_interaction` |

**Region options**:
- `Africa and Middle East`
- `Asia and Pacific`
- `Europe`
- `Latin America and Caribbean`
- `North America`

**Special handling**: If the wallet address itself is a CEX address, all Top 5 fields are filled with that CEX's information, and the count is set to 999999

---

## Feature Summary Table

| Category | Count | Features |
|----------|-------|----------|
| Basic Statistics | 6 | wallet, total_transactions, total_volume_eth, active_days, unique_contracts, data_quality |
| Transaction Amount | 6 | avg_transaction_amount_eth, median_transaction_amount_eth, p90_transaction_amount_eth, large_tx_ratio, micro_tx_ratio, zero_value_tx_ratio |
| Time Period Ratio | 4 | night_ratio, early_morning_ratio, daytime_ratio, weekend_ratio |
| 24-Hour Percentage | 24 | pct_hour_0 ~ pct_hour_23 |
| DST Features | 3 | dst_mode_hour, non_dst_mode_hour, tx_hour_variance |
| Seasonal Period | 6 | avg_tx_hour_period1 ~ avg_tx_hour_period6 |
| Gas Features | 5 | avg_gas_price, median_gas_price, p90_gas_price, gas_price_stddev, avg_tx_fee_eth |
| Activity Features | 5 | avg_tx_per_day, days_since_last_tx, wallet_life_days, wallet_age_days, unique_contracts_ratio |
| Stablecoin Preference | 5 | usdt_count, usdc_count, dai_count, stablecoin_diversity, usdt_vs_usdc_ratio |
| Protocol Preference | 5 | dex_count, lending_count, nft_count, bridge_count, dex_ratio |
| Top 10 Tokens | 20 | top1_token ~ top10_token, top1_token_count ~ top10_token_count |
| Top 10 Namespaces | 20 | top1_namespace ~ top10_namespace, top1_namespace_count ~ top10_namespace_count |
| Top 5 CEX | 16 | top1_cex ~ top5_cex, top1_cex_region ~ top5_cex_region, top1_cex_count ~ top5_cex_count, cex_interaction_type |
| **Total** | **~125** | |

---

## Usage Recommendations

### Core Features for Model Training

1. **Time features**: 24-hour percentages, `weekend_ratio`, difference between `dst_mode_hour` and `non_dst_mode_hour`
2. **Amount features**: `avg_transaction_amount_eth`, `large_tx_ratio`
3. **Stablecoin features**: `usdt_vs_usdc_ratio`
4. **CEX features**: `top1_cex_region` (strong predictor)
5. **Protocol features**: `dex_ratio`, `top1_namespace`
6. **Activity features**: `avg_tx_per_day`, `wallet_age_days`

### Data Preprocessing Notes

- Numerical features should be normalized/standardized before training
- Categorical features (`top1_token`, `top1_namespace`, `top1_cex`, etc.) require one-hot encoding or label encoding
- Missing data is filled with `0` (numerical) or `'N/A'` (string)

### Region Label Mapping

| Label | Meaning |
|-------|---------|
| `Asia and Pacific` | Asia and Pacific region |
| `North America` | North America |
| `Europe` | Europe |
| `Africa and Middle East` | Africa and Middle East |
| `Latin America and Caribbean` | Latin America and Caribbean |
