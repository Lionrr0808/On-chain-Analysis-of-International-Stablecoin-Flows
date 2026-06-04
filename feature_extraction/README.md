# 钱包地区预测特征说明文档

## 一、基础统计特征

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `wallet` | STRING | 钱包地址（小写格式） |
| `total_transactions` | INT | 钱包在一年内发起的交易总数 |
| `total_volume_eth` | FLOAT | 钱包一年内交易总金额（ETH） |
| `active_days` | INT | 钱包有交易活动的总天数 |
| `unique_contracts` | INT | 交互过的唯一合约地址数量 |
| `data_quality` | STRING | 数据质量等级：very_high / high / medium / low |

---

## 二、交易金额特征

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `avg_transaction_amount_eth` | FLOAT | 平均每笔交易金额（ETH） |
| `median_transaction_amount_eth` | FLOAT | 交易金额中位数（ETH） |
| `p90_transaction_amount_eth` | FLOAT | 交易金额90分位数（ETH） |
| `large_tx_ratio` | FLOAT | 大额交易占比（>1 ETH） |
| `micro_tx_ratio` | FLOAT | 小额交易占比（<0.01 ETH） |
| `zero_value_tx_ratio` | FLOAT | 零值交易占比（ETH金额为0，通常是代币交易） |

---

## 三、时段比例特征

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `night_ratio` | FLOAT | 夜间交易占比（UTC 0-5点） |
| `early_morning_ratio` | FLOAT | 凌晨交易占比（UTC 0-3点） |
| `daytime_ratio` | FLOAT | 白天交易占比（UTC 8-20点） |
| `weekend_ratio` | FLOAT | 周末交易占比（周六+周日） |

---

## 四、24小时交易百分比（共24个特征）

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `pct_hour_0` ~ `pct_hour_23` | FLOAT | 每个UTC小时内的交易数占总交易数的比例 |
| | | 例如：`pct_hour_8 = 0.15` 表示15%的交易发生在UTC 8:00-9:00 |

**地区相关性**：反映用户主要活跃时区（如亚洲用户可能在UTC 0-4点活跃，对应北京时间8-12点）

---

## 五、夏令时(DST)特征

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `dst_mode_hour` | INT | 夏令时期间（3-10月）最活跃的UTC小时 |
| `non_dst_mode_hour` | INT | 非夏令时期间（11-2月）最活跃的UTC小时 |
| `tx_hour_variance` | FLOAT | 交易小时分布方差（反映活跃规律性） |

**地区相关性**：北美和欧洲实行DST，亚洲不实行，DST期间活跃小时变化可作为地区判别依据

---

## 六、特定时段平均交易时间（6个区间）

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `avg_tx_hour_period1` | FLOAT | 3月14日-11月7日期间的平均交易小时 |
| `avg_tx_hour_period2` | FLOAT | 11月8日-3月13日期间的平均交易小时 |
| `avg_tx_hour_period3` | FLOAT | 3月21日-10月31日期间的平均交易小时 |
| `avg_tx_hour_period4` | FLOAT | 11月1日-3月10日期间的平均交易小时 |
| `avg_tx_hour_period5` | FLOAT | 10月7日-4月6日期间的平均交易小时 |
| `avg_tx_hour_period6` | FLOAT | 4月7日-10月6日期间的平均交易小时 |

**地区相关性**：不同地区对夏令时和冬令时的响应不同，这些区间可捕捉季节性的时间行为变化

---

## 七、Gas费用特征

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `avg_gas_price` | FLOAT | 平均Gas价格（Gwei） |
| `median_gas_price` | FLOAT | Gas价格中位数（Gwei） |
| `p90_gas_price` | FLOAT | Gas价格90分位数（Gwei） |
| `gas_price_stddev` | FLOAT | Gas价格标准差（反映波动性） |
| `avg_tx_fee_eth` | FLOAT | 平均每笔交易手续费（ETH） |

**地区相关性**：发达国家用户可能愿意支付更高Gas费用，对价格敏感度较低

---

## 八、活跃度特征

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `avg_tx_per_day` | FLOAT | 平均每日交易数 |
| `days_since_last_tx` | INT | 距离最近一次交易的天数 |
| `wallet_life_days` | INT | 钱包生命周期（首次交易到最后一次交易的天数） |
| `wallet_age_days` | INT | 钱包年龄（首次交易距今天数） |
| `unique_contracts_ratio` | FLOAT | 唯一合约数 / 总交易数（交互多样性） |

---

## 九、稳定币偏好特征

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `usdt_count` | INT | 与USDT合约交互的次数 |
| `usdc_count` | INT | 与USDC合约交互的次数 |
| `dai_count` | INT | 与DAI合约交互的次数 |
| `stablecoin_diversity` | INT | 使用的稳定币种类数（USDT/USDC/DAI） |
| `usdt_vs_usdc_ratio` | FLOAT | USDT交互次数 / USDC交互次数 |

**地区相关性**：亚洲用户更倾向USDT，北美/欧洲用户更倾向USDC

---

## 十、协议偏好特征

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `dex_count` | INT | 与DEX（去中心化交易所）交互的次数 |
| `lending_count` | INT | 与借贷协议交互的次数 |
| `nft_count` | INT | 与NFT市场交互的次数 |
| `bridge_count` | INT | 与跨链桥交互的次数 |
| `dex_ratio` | FLOAT | DEX交互次数占协议总交互的比例 |

**地区相关性**：不同地区对DeFi/NFT的偏好不同，监管严格地区可能更多使用DEX

---

## 十一、Top 10 ERC-20 代币（20个特征）

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `top1_token` ~ `top10_token` | STRING | 交易次数排名前10的代币名称 |
| `top1_token_count` ~ `top10_token_count` | INT | 对应的交易次数 |

---

## 十二、Top 10 命名空间（20个特征）

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `top1_namespace` ~ `top10_namespace` | STRING | 交互次数排名前10的合约命名空间 |
| `top1_namespace_count` ~ `top10_namespace_count` | INT | 对应的交互次数 |

**命名空间类型**：dex（去中心化交易所）、lending（借贷）、nft（NFT市场）、bridge（跨链桥）、yield（收益聚合器）、oracle（预言机）等

---

## 十三、Top 5 CEX（中心化交易所）（15个特征）

| 特征名 | 类型 | 说明 |
|--------|------|------|
| `top1_cex` ~ `top5_cex` | STRING | 交互次数排名前5的中心化交易所名称 |
| `top1_cex_region` ~ `top5_cex_region` | STRING | 对应交易所所在的地区 |
| `top1_cex_count` ~ `top5_cex_count` | INT | 对应的交互次数 |
| `cex_interaction_type` | STRING | CEX交互类型：`cex_address`（钱包本身是CEX地址）/ `has_cex_interaction` / `no_cex_interaction` |

**地区可选值**：
- `Africa and Middle East`（非洲和中东）
- `Asia and Pacific`（亚洲及太平洋地区）
- `Europe`（欧洲）
- `Latin America and Caribbean`（拉丁美洲和加勒比地区）
- `North America`（北美）

**特殊处理**：如果钱包地址本身就在CEX地址列表中，则Top 5全部为该CEX的信息，次数设为999999

---

## 特征汇总表

| 类别 | 特征数量 | 特征名称 |
|------|---------|----------|
| 基础统计 | 6 | wallet, total_transactions, total_volume_eth, active_days, unique_contracts, data_quality |
| 交易金额 | 6 | avg_transaction_amount_eth, median_transaction_amount_eth, p90_transaction_amount_eth, large_tx_ratio, micro_tx_ratio, zero_value_tx_ratio |
| 时段比例 | 4 | night_ratio, early_morning_ratio, daytime_ratio, weekend_ratio |
| 24小时百分比 | 24 | pct_hour_0 ~ pct_hour_23 |
| DST特征 | 3 | dst_mode_hour, non_dst_mode_hour, tx_hour_variance |
| 时段平均时间 | 6 | avg_tx_hour_period1 ~ avg_tx_hour_period6 |
| Gas特征 | 5 | avg_gas_price, median_gas_price, p90_gas_price, gas_price_stddev, avg_tx_fee_eth |
| 活跃度 | 5 | avg_tx_per_day, days_since_last_tx, wallet_life_days, wallet_age_days, unique_contracts_ratio |
| 稳定币偏好 | 5 | usdt_count, usdc_count, dai_count, stablecoin_diversity, usdt_vs_usdc_ratio |
| 协议偏好 | 5 | dex_count, lending_count, nft_count, bridge_count, dex_ratio |
| Top 10 代币 | 20 | top1_token ~ top10_token, top1_token_count ~ top10_token_count |
| Top 10 命名空间 | 20 | top1_namespace ~ top10_namespace, top1_namespace_count ~ top10_namespace_count |
| Top 5 CEX | 16 | top1_cex ~ top5_cex, top1_cex_region ~ top5_cex_region, top1_cex_count ~ top5_cex_count, cex_interaction_type |
| **总计** | **约 125** | |

---

## 使用建议

### 训练模型时推荐使用的核心特征

1. **时间类**：24小时百分比、`weekend_ratio`、`dst_mode_hour`与`non_dst_mode_hour`的差异
2. **金额类**：`avg_transaction_amount_eth`、`large_tx_ratio`
3. **稳定币类**：`usdt_vs_usdc_ratio`
4. **CEX类**：`top1_cex_region`（强特征）
5. **协议类**：`dex_ratio`、`top1_namespace`
6. **活跃度类**：`avg_tx_per_day`、`wallet_age_days`

### 数据预处理注意事项

- 数值特征建议标准化/归一化后再训练
- 类别特征（`top1_token`、`top1_namespace`、`top1_cex`等）需要进行独热编码或标签编码
- 无数据的特征已填充为 `0`（数值）或 `'N/A'`（字符串）

### 地区标签对应关系

| 标签 | 含义 |
|------|------|
| `Asia and Pacific` | 亚洲及太平洋地区 |
| `North America` | 北美 |
| `Europe` | 欧洲 |
| `Africa and Middle East` | 非洲和中东 |
| `Latin America and Caribbean` | 拉丁美洲和加勒比地区 |
