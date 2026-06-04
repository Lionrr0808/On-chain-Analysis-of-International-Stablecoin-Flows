-- ============================================================
-- 完整特征提取 SQL（最终版）
-- 包含：24小时交易百分比 + 6个时段平均时间 + 所有其他特征
-- ============================================================

CREATE OR REPLACE TABLE `stablecoin-on-chain-analysis.wallets.wallet_features_complete` AS

WITH 
-- 1. 标准化钱包列表
all_wallets AS (
    SELECT DISTINCT LOWER(`wallet address`) as wallet
    FROM `stablecoin-on-chain-analysis.wallets.wallet_list`
    WHERE `wallet address` IS NOT NULL
),

-- 2. 标准化CEX地址（小写）
cex_normalized AS (
    SELECT 
        LOWER(address) as address,
        region
    FROM `stablecoin-on-chain-analysis.wallets.cex_addresses`
    WHERE address IS NOT NULL AND region IS NOT NULL
),

-- 3. 获取所有交易（只统计发起交易）
wallet_txs AS (
    SELECT 
        LOWER(t.from_address) as wallet,
        t.block_timestamp,
        EXTRACT(HOUR FROM t.block_timestamp) as tx_hour_utc,
        EXTRACT(MONTH FROM t.block_timestamp) as tx_month,
        EXTRACT(DAY FROM t.block_timestamp) as tx_day,
        EXTRACT(DAYOFWEEK FROM t.block_timestamp) as tx_dow,
        DATE(t.block_timestamp) as tx_date,
        t.gas_price,
        t.receipt_gas_used,
        (t.gas_price * t.receipt_gas_used) / 1e18 as tx_fee_eth,
        t.value / 1e18 as eth_amount,
        t.to_address
    FROM `bigquery-public-data.crypto_ethereum.transactions` t
    INNER JOIN all_wallets w ON LOWER(t.from_address) = w.wallet
    WHERE 
        t.block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
        AND t.receipt_status = 1
        AND t.gas_price > 0
        AND t.receipt_gas_used > 0
),

-- 4. 计算每个钱包的总交易数（用于百分比）
wallet_total AS (
    SELECT wallet, COUNT(*) as total_cnt
    FROM wallet_txs
    GROUP BY wallet
),

-- 5. 24小时交易百分比
hourly_percentages AS (
    SELECT 
        w.wallet,
        w.tx_hour_utc,
        COUNT(*) as hour_cnt,
        wt.total_cnt,
        SAFE_DIVIDE(COUNT(*), wt.total_cnt) as hour_pct
    FROM wallet_txs w
    JOIN wallet_total wt ON w.wallet = wt.wallet
    GROUP BY w.wallet, w.tx_hour_utc, wt.total_cnt
),

-- 6. 基础特征（包含新特征）
base_features AS (
    SELECT 
        wallet,
        COUNT(*) as total_transactions,
        SUM(eth_amount) as total_volume_eth,
        COUNT(DISTINCT tx_date) as active_days,
        COUNT(DISTINCT to_address) as unique_contracts,
        
        -- 金额特征
        AVG(eth_amount) as avg_transaction_amount_eth,
        APPROX_QUANTILES(eth_amount, 100)[OFFSET(50)] as median_transaction_amount_eth,
        APPROX_QUANTILES(eth_amount, 100)[OFFSET(90)] as p90_transaction_amount_eth,
        SAFE_DIVIDE(COUNTIF(eth_amount > 1), COUNT(*)) as large_tx_ratio,
        SAFE_DIVIDE(COUNTIF(eth_amount < 0.01), COUNT(*)) as micro_tx_ratio,
        SAFE_DIVIDE(COUNTIF(eth_amount = 0), COUNT(*)) as zero_value_tx_ratio,
        
        -- 时段比例（原有时段）
        SAFE_DIVIDE(COUNTIF(tx_hour_utc BETWEEN 0 AND 5), COUNT(*)) as night_ratio,
        SAFE_DIVIDE(COUNTIF(tx_hour_utc BETWEEN 0 AND 3), COUNT(*)) as early_morning_ratio,
        SAFE_DIVIDE(COUNTIF(tx_hour_utc BETWEEN 8 AND 20), COUNT(*)) as daytime_ratio,
        SAFE_DIVIDE(COUNTIF(tx_dow IN (1,7)), COUNT(*)) as weekend_ratio,  -- 周末交易占比
        
        -- DST 特征（夏令时：3-10月）
        APPROX_TOP_COUNT(CASE WHEN tx_month BETWEEN 3 AND 10 THEN tx_hour_utc END, 1)[OFFSET(0)].value as dst_mode_hour,
        APPROX_TOP_COUNT(CASE WHEN tx_month NOT BETWEEN 3 AND 10 THEN tx_hour_utc END, 1)[OFFSET(0)].value as non_dst_mode_hour,
        
        -- 交易小时方差（规律性）
        STDDEV(tx_hour_utc) as tx_hour_variance,
        
        -- 特定区间平均交易时间（6个区间）
        AVG(CASE WHEN (tx_month = 3 AND tx_day >= 14) OR (tx_month BETWEEN 4 AND 10) OR (tx_month = 11 AND tx_day <= 7) 
                 THEN tx_hour_utc END) as avg_tx_hour_period1,
        AVG(CASE WHEN (tx_month = 11 AND tx_day >= 8) OR (tx_month = 12) OR (tx_month = 1) OR (tx_month = 2) OR (tx_month = 3 AND tx_day <= 13)
                 THEN tx_hour_utc END) as avg_tx_hour_period2,
        AVG(CASE WHEN (tx_month = 3 AND tx_day >= 21) OR (tx_month BETWEEN 4 AND 9) OR (tx_month = 10 AND tx_day <= 31)
                 THEN tx_hour_utc END) as avg_tx_hour_period3,
        AVG(CASE WHEN (tx_month = 11) OR (tx_month = 12) OR (tx_month = 1) OR (tx_month = 2) OR (tx_month = 3 AND tx_day <= 10)
                 THEN tx_hour_utc END) as avg_tx_hour_period4,
        AVG(CASE WHEN (tx_month = 10 AND tx_day >= 7) OR (tx_month = 11) OR (tx_month = 12) OR (tx_month = 1) OR (tx_month = 2) OR (tx_month = 3) OR (tx_month = 4 AND tx_day <= 6)
                 THEN tx_hour_utc END) as avg_tx_hour_period5,
        AVG(CASE WHEN (tx_month = 4 AND tx_day >= 7) OR (tx_month BETWEEN 5 AND 8) OR (tx_month = 9) OR (tx_month = 10 AND tx_day <= 6)
                 THEN tx_hour_utc END) as avg_tx_hour_period6,
        
        -- Gas 特征
        AVG(gas_price) as avg_gas_price,
        APPROX_QUANTILES(gas_price, 100)[OFFSET(50)] as median_gas_price,
        APPROX_QUANTILES(gas_price, 100)[OFFSET(90)] as p90_gas_price,
        STDDEV(gas_price) as gas_price_stddev,
        AVG(tx_fee_eth) as avg_tx_fee_eth,
        
        -- 活跃度特征
        SAFE_DIVIDE(COUNT(*), COUNT(DISTINCT tx_date)) as avg_tx_per_day,
        DATE_DIFF(CURRENT_DATE(), MAX(DATE(tx_date)), DAY) as days_since_last_tx,
        DATE_DIFF(MAX(DATE(tx_date)), MIN(DATE(tx_date)), DAY) as wallet_life_days,
        DATE_DIFF(CURRENT_DATE(), MIN(DATE(tx_date)), DAY) as wallet_age_days,
        
        -- 交互多样性
        SAFE_DIVIDE(COUNT(DISTINCT to_address), COUNT(*)) as unique_contracts_ratio,
        
        -- 数据质量
        CASE 
            WHEN COUNT(*) >= 50 THEN 'very_high'
            WHEN COUNT(*) >= 20 THEN 'high'
            WHEN COUNT(*) >= 5 THEN 'medium'
            WHEN COUNT(*) >= 1 THEN 'low'
        END as data_quality
    FROM wallet_txs
    GROUP BY wallet
),

-- 7. 24小时交易百分比（透视表）
hourly_pivot AS (
    SELECT 
        wallet,
        MAX(CASE WHEN tx_hour_utc = 0 THEN hour_pct END) as pct_hour_0,
        MAX(CASE WHEN tx_hour_utc = 1 THEN hour_pct END) as pct_hour_1,
        MAX(CASE WHEN tx_hour_utc = 2 THEN hour_pct END) as pct_hour_2,
        MAX(CASE WHEN tx_hour_utc = 3 THEN hour_pct END) as pct_hour_3,
        MAX(CASE WHEN tx_hour_utc = 4 THEN hour_pct END) as pct_hour_4,
        MAX(CASE WHEN tx_hour_utc = 5 THEN hour_pct END) as pct_hour_5,
        MAX(CASE WHEN tx_hour_utc = 6 THEN hour_pct END) as pct_hour_6,
        MAX(CASE WHEN tx_hour_utc = 7 THEN hour_pct END) as pct_hour_7,
        MAX(CASE WHEN tx_hour_utc = 8 THEN hour_pct END) as pct_hour_8,
        MAX(CASE WHEN tx_hour_utc = 9 THEN hour_pct END) as pct_hour_9,
        MAX(CASE WHEN tx_hour_utc = 10 THEN hour_pct END) as pct_hour_10,
        MAX(CASE WHEN tx_hour_utc = 11 THEN hour_pct END) as pct_hour_11,
        MAX(CASE WHEN tx_hour_utc = 12 THEN hour_pct END) as pct_hour_12,
        MAX(CASE WHEN tx_hour_utc = 13 THEN hour_pct END) as pct_hour_13,
        MAX(CASE WHEN tx_hour_utc = 14 THEN hour_pct END) as pct_hour_14,
        MAX(CASE WHEN tx_hour_utc = 15 THEN hour_pct END) as pct_hour_15,
        MAX(CASE WHEN tx_hour_utc = 16 THEN hour_pct END) as pct_hour_16,
        MAX(CASE WHEN tx_hour_utc = 17 THEN hour_pct END) as pct_hour_17,
        MAX(CASE WHEN tx_hour_utc = 18 THEN hour_pct END) as pct_hour_18,
        MAX(CASE WHEN tx_hour_utc = 19 THEN hour_pct END) as pct_hour_19,
        MAX(CASE WHEN tx_hour_utc = 20 THEN hour_pct END) as pct_hour_20,
        MAX(CASE WHEN tx_hour_utc = 21 THEN hour_pct END) as pct_hour_21,
        MAX(CASE WHEN tx_hour_utc = 22 THEN hour_pct END) as pct_hour_22,
        MAX(CASE WHEN tx_hour_utc = 23 THEN hour_pct END) as pct_hour_23
    FROM hourly_percentages
    GROUP BY wallet
),

-- 8. Top 10 代币（含次数）
token_txs AS (
    SELECT 
        LOWER(t.from_address) as wallet,
        tk.symbol as token_name
    FROM `bigquery-public-data.crypto_ethereum.transactions` t
    INNER JOIN all_wallets w ON LOWER(t.from_address) = w.wallet
    INNER JOIN `stablecoin-on-chain-analysis.wallets.token_addresses_full` tk 
        ON LOWER(t.to_address) = tk.token_address
    WHERE t.block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
      AND t.receipt_status = 1
),
ranked_tokens AS (
    SELECT wallet, token_name, COUNT(*) as cnt,
           ROW_NUMBER() OVER (PARTITION BY wallet ORDER BY COUNT(*) DESC) as rn
    FROM token_txs GROUP BY wallet, token_name
),
top_tokens AS (
    SELECT 
        wallet,
        MAX(CASE WHEN rn=1 THEN token_name END) as top1_token,
        MAX(CASE WHEN rn=1 THEN cnt END) as top1_token_count,
        MAX(CASE WHEN rn=2 THEN token_name END) as top2_token,
        MAX(CASE WHEN rn=2 THEN cnt END) as top2_token_count,
        MAX(CASE WHEN rn=3 THEN token_name END) as top3_token,
        MAX(CASE WHEN rn=3 THEN cnt END) as top3_token_count,
        MAX(CASE WHEN rn=4 THEN token_name END) as top4_token,
        MAX(CASE WHEN rn=4 THEN cnt END) as top4_token_count,
        MAX(CASE WHEN rn=5 THEN token_name END) as top5_token,
        MAX(CASE WHEN rn=5 THEN cnt END) as top5_token_count,
        MAX(CASE WHEN rn=6 THEN token_name END) as top6_token,
        MAX(CASE WHEN rn=6 THEN cnt END) as top6_token_count,
        MAX(CASE WHEN rn=7 THEN token_name END) as top7_token,
        MAX(CASE WHEN rn=7 THEN cnt END) as top7_token_count,
        MAX(CASE WHEN rn=8 THEN token_name END) as top8_token,
        MAX(CASE WHEN rn=8 THEN cnt END) as top8_token_count,
        MAX(CASE WHEN rn=9 THEN token_name END) as top9_token,
        MAX(CASE WHEN rn=9 THEN cnt END) as top9_token_count,
        MAX(CASE WHEN rn=10 THEN token_name END) as top10_token,
        MAX(CASE WHEN rn=10 THEN cnt END) as top10_token_count
    FROM ranked_tokens WHERE rn <= 10 GROUP BY wallet
),

-- 9. 稳定币偏好（从token统计中单独计算）
stablecoin_prefs AS (
    SELECT 
        wallet,
        COUNTIF(token_name = 'USDT') as usdt_count,
        COUNTIF(token_name = 'USDC') as usdc_count,
        COUNTIF(token_name = 'DAI') as dai_count,
        COUNT(DISTINCT token_name) as stablecoin_diversity
    FROM token_txs
    WHERE token_name IN ('USDT', 'USDC', 'DAI')
    GROUP BY wallet
),

-- 10. Top 10 命名空间（含次数）
namespace_txs AS (
    SELECT 
        LOWER(t.from_address) as wallet,
        ns.namespace
    FROM `bigquery-public-data.crypto_ethereum.transactions` t
    INNER JOIN all_wallets w ON LOWER(t.from_address) = w.wallet
    INNER JOIN `stablecoin-on-chain-analysis.wallets.namespace_addresses_full` ns 
        ON LOWER(t.to_address) = ns.contract_address
    WHERE t.block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
      AND t.receipt_status = 1
),
ranked_namespaces AS (
    SELECT wallet, namespace, COUNT(*) as cnt,
           ROW_NUMBER() OVER (PARTITION BY wallet ORDER BY COUNT(*) DESC) as rn
    FROM namespace_txs GROUP BY wallet, namespace
),
top_namespaces AS (
    SELECT 
        wallet,
        MAX(CASE WHEN rn=1 THEN namespace END) as top1_namespace,
        MAX(CASE WHEN rn=1 THEN cnt END) as top1_namespace_count,
        MAX(CASE WHEN rn=2 THEN namespace END) as top2_namespace,
        MAX(CASE WHEN rn=2 THEN cnt END) as top2_namespace_count,
        MAX(CASE WHEN rn=3 THEN namespace END) as top3_namespace,
        MAX(CASE WHEN rn=3 THEN cnt END) as top3_namespace_count,
        MAX(CASE WHEN rn=4 THEN namespace END) as top4_namespace,
        MAX(CASE WHEN rn=4 THEN cnt END) as top4_namespace_count,
        MAX(CASE WHEN rn=5 THEN namespace END) as top5_namespace,
        MAX(CASE WHEN rn=5 THEN cnt END) as top5_namespace_count,
        MAX(CASE WHEN rn=6 THEN namespace END) as top6_namespace,
        MAX(CASE WHEN rn=6 THEN cnt END) as top6_namespace_count,
        MAX(CASE WHEN rn=7 THEN namespace END) as top7_namespace,
        MAX(CASE WHEN rn=7 THEN cnt END) as top7_namespace_count,
        MAX(CASE WHEN rn=8 THEN namespace END) as top8_namespace,
        MAX(CASE WHEN rn=8 THEN cnt END) as top8_namespace_count,
        MAX(CASE WHEN rn=9 THEN namespace END) as top9_namespace,
        MAX(CASE WHEN rn=9 THEN cnt END) as top9_namespace_count,
        MAX(CASE WHEN rn=10 THEN namespace END) as top10_namespace,
        MAX(CASE WHEN rn=10 THEN cnt END) as top10_namespace_count
    FROM ranked_namespaces WHERE rn <= 10 GROUP BY wallet
),

-- 11. 协议比率特征（从namespace统计）
protocol_ratios AS (
    SELECT 
        wallet,
        COUNTIF(namespace = 'dex') as dex_count,
        COUNTIF(namespace = 'lending') as lending_count,
        COUNTIF(namespace = 'nft') as nft_count,
        COUNTIF(namespace = 'bridge') as bridge_count
    FROM namespace_txs
    GROUP BY wallet
),

-- 12. CEX 交互（发起+接收）
cex_interactions AS (
    SELECT LOWER(t.from_address) as wallet, c.region
    FROM `bigquery-public-data.crypto_ethereum.transactions` t
    INNER JOIN all_wallets w ON LOWER(t.from_address) = w.wallet
    INNER JOIN cex_normalized c ON LOWER(t.to_address) = c.address
    WHERE t.block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
      AND t.receipt_status = 1
    UNION ALL
    SELECT LOWER(t.to_address) as wallet, c.region
    FROM `bigquery-public-data.crypto_ethereum.transactions` t
    INNER JOIN all_wallets w ON LOWER(t.to_address) = w.wallet
    INNER JOIN cex_normalized c ON LOWER(t.from_address) = c.address
    WHERE t.block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
      AND t.receipt_status = 1
),
cex_counts AS (
    SELECT wallet, region, COUNT(*) as cnt,
           ROW_NUMBER() OVER (PARTITION BY wallet ORDER BY COUNT(*) DESC) as rn
    FROM cex_interactions GROUP BY wallet, region
),
top_cex AS (
    SELECT 
        wallet,
        MAX(CASE WHEN rn=1 THEN region END) as top1_cex_region,
        MAX(CASE WHEN rn=1 THEN cnt END) as top1_cex_region_count,
        MAX(CASE WHEN rn=2 THEN region END) as top2_cex_region,
        MAX(CASE WHEN rn=2 THEN cnt END) as top2_cex_region_count,
        MAX(CASE WHEN rn=3 THEN region END) as top3_cex_region,
        MAX(CASE WHEN rn=3 THEN cnt END) as top3_cex_region_count,
        MAX(CASE WHEN rn=4 THEN region END) as top4_cex_region,
        MAX(CASE WHEN rn=4 THEN cnt END) as top4_cex_region_count,
        MAX(CASE WHEN rn=5 THEN region END) as top5_cex_region,
        MAX(CASE WHEN rn=5 THEN cnt END) as top5_cex_region_count
    FROM cex_counts WHERE rn <= 5 GROUP BY wallet
),

-- 13. 钱包本身就是CEX地址
wallet_is_cex AS (
    SELECT w.wallet, c.region as self_cex_region
    FROM all_wallets w
    INNER JOIN cex_normalized c ON w.wallet = c.address
),

final_cex AS (
    SELECT 
        w.wallet,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN ic.self_cex_region ELSE t.top1_cex_region END as top1_cex_region,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN 999999 ELSE t.top1_cex_region_count END as top1_cex_region_count,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN ic.self_cex_region ELSE t.top2_cex_region END as top2_cex_region,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN 999999 ELSE t.top2_cex_region_count END as top2_cex_region_count,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN ic.self_cex_region ELSE t.top3_cex_region END as top3_cex_region,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN 999999 ELSE t.top3_cex_region_count END as top3_cex_region_count,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN ic.self_cex_region ELSE t.top4_cex_region END as top4_cex_region,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN 999999 ELSE t.top4_cex_region_count END as top4_cex_region_count,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN ic.self_cex_region ELSE t.top5_cex_region END as top5_cex_region,
        CASE WHEN ic.self_cex_region IS NOT NULL THEN 999999 ELSE t.top5_cex_region_count END as top5_cex_region_count,
        CASE 
            WHEN ic.self_cex_region IS NOT NULL THEN 'cex_address'
            WHEN t.top1_cex_region IS NULL THEN 'no_cex_interaction'
            ELSE 'has_cex_interaction'
        END as cex_interaction_type
    FROM all_wallets w
    LEFT JOIN top_cex t ON w.wallet = t.wallet
    LEFT JOIN wallet_is_cex ic ON w.wallet = ic.wallet
)

-- 14. 最终输出
SELECT 
    w.wallet,
    
    -- 基础特征
    b.total_transactions,
    b.total_volume_eth,
    b.active_days,
    b.unique_contracts,
    
    -- 金额特征
    b.avg_transaction_amount_eth,
    b.median_transaction_amount_eth,
    b.p90_transaction_amount_eth,
    b.large_tx_ratio,
    b.micro_tx_ratio,
    b.zero_value_tx_ratio,
    
    -- 时段比例
    b.night_ratio,
    b.early_morning_ratio,
    b.daytime_ratio,
    b.weekend_ratio,
    
    -- 24小时交易百分比
    h.pct_hour_0,
    h.pct_hour_1,
    h.pct_hour_2,
    h.pct_hour_3,
    h.pct_hour_4,
    h.pct_hour_5,
    h.pct_hour_6,
    h.pct_hour_7,
    h.pct_hour_8,
    h.pct_hour_9,
    h.pct_hour_10,
    h.pct_hour_11,
    h.pct_hour_12,
    h.pct_hour_13,
    h.pct_hour_14,
    h.pct_hour_15,
    h.pct_hour_16,
    h.pct_hour_17,
    h.pct_hour_18,
    h.pct_hour_19,
    h.pct_hour_20,
    h.pct_hour_21,
    h.pct_hour_22,
    h.pct_hour_23,
    
    -- DST特征
    b.dst_mode_hour,
    b.non_dst_mode_hour,
    
    -- 交易小时方差
    b.tx_hour_variance,
    
    -- 6个特定区间平均交易时间
    b.avg_tx_hour_period1,
    b.avg_tx_hour_period2,
    b.avg_tx_hour_period3,
    b.avg_tx_hour_period4,
    b.avg_tx_hour_period5,
    b.avg_tx_hour_period6,
    
    -- Gas特征
    b.avg_gas_price,
    b.median_gas_price,
    b.p90_gas_price,
    b.gas_price_stddev,
    b.avg_tx_fee_eth,
    
    -- 活跃度特征
    b.avg_tx_per_day,
    b.days_since_last_tx,
    b.wallet_life_days,
    b.wallet_age_days,
    
    -- 交互多样性
    b.unique_contracts_ratio,
    
    -- 稳定币偏好
    s.usdt_count,
    s.usdc_count,
    s.dai_count,
    s.stablecoin_diversity,
    SAFE_DIVIDE(s.usdt_count, s.usdc_count) as usdt_vs_usdc_ratio,
    
    -- 协议比率
    p.dex_count,
    p.lending_count,
    p.nft_count,
    p.bridge_count,
    SAFE_DIVIDE(p.dex_count, NULLIF(p.dex_count + p.lending_count + p.nft_count + p.bridge_count, 0)) as dex_ratio,
    
    -- Top 10 Tokens（含次数）
    IFNULL(t.top1_token, 'N/A') as top1_token,
    IFNULL(t.top1_token_count, 0) as top1_token_count,
    IFNULL(t.top2_token, 'N/A') as top2_token,
    IFNULL(t.top2_token_count, 0) as top2_token_count,
    IFNULL(t.top3_token, 'N/A') as top3_token,
    IFNULL(t.top3_token_count, 0) as top3_token_count,
    IFNULL(t.top4_token, 'N/A') as top4_token,
    IFNULL(t.top4_token_count, 0) as top4_token_count,
    IFNULL(t.top5_token, 'N/A') as top5_token,
    IFNULL(t.top5_token_count, 0) as top5_token_count,
    IFNULL(t.top6_token, 'N/A') as top6_token,
    IFNULL(t.top6_token_count, 0) as top6_token_count,
    IFNULL(t.top7_token, 'N/A') as top7_token,
    IFNULL(t.top7_token_count, 0) as top7_token_count,
    IFNULL(t.top8_token, 'N/A') as top8_token,
    IFNULL(t.top8_token_count, 0) as top8_token_count,
    IFNULL(t.top9_token, 'N/A') as top9_token,
    IFNULL(t.top9_token_count, 0) as top9_token_count,
    IFNULL(t.top10_token, 'N/A') as top10_token,
    IFNULL(t.top10_token_count, 0) as top10_token_count,
    
    -- Top 10 Namespaces（含次数）
    IFNULL(n.top1_namespace, 'N/A') as top1_namespace,
    IFNULL(n.top1_namespace_count, 0) as top1_namespace_count,
    IFNULL(n.top2_namespace, 'N/A') as top2_namespace,
    IFNULL(n.top2_namespace_count, 0) as top2_namespace_count,
    IFNULL(n.top3_namespace, 'N/A') as top3_namespace,
    IFNULL(n.top3_namespace_count, 0) as top3_namespace_count,
    IFNULL(n.top4_namespace, 'N/A') as top4_namespace,
    IFNULL(n.top4_namespace_count, 0) as top4_namespace_count,
    IFNULL(n.top5_namespace, 'N/A') as top5_namespace,
    IFNULL(n.top5_namespace_count, 0) as top5_namespace_count,
    IFNULL(n.top6_namespace, 'N/A') as top6_namespace,
    IFNULL(n.top6_namespace_count, 0) as top6_namespace_count,
    IFNULL(n.top7_namespace, 'N/A') as top7_namespace,
    IFNULL(n.top7_namespace_count, 0) as top7_namespace_count,
    IFNULL(n.top8_namespace, 'N/A') as top8_namespace,
    IFNULL(n.top8_namespace_count, 0) as top8_namespace_count,
    IFNULL(n.top9_namespace, 'N/A') as top9_namespace,
    IFNULL(n.top9_namespace_count, 0) as top9_namespace_count,
    IFNULL(n.top10_namespace, 'N/A') as top10_namespace,
    IFNULL(n.top10_namespace_count, 0) as top10_namespace_count,
    
    -- Top 5 CEX Region（含次数）
    IFNULL(c.top1_cex_region, 'N/A') as top1_cex_region,
    IFNULL(c.top1_cex_region_count, 0) as top1_cex_region_count,
    IFNULL(c.top2_cex_region, 'N/A') as top2_cex_region,
    IFNULL(c.top2_cex_region_count, 0) as top2_cex_region_count,
    IFNULL(c.top3_cex_region, 'N/A') as top3_cex_region,
    IFNULL(c.top3_cex_region_count, 0) as top3_cex_region_count,
    IFNULL(c.top4_cex_region, 'N/A') as top4_cex_region,
    IFNULL(c.top4_cex_region_count, 0) as top4_cex_region_count,
    IFNULL(c.top5_cex_region, 'N/A') as top5_cex_region,
    IFNULL(c.top5_cex_region_count, 0) as top5_cex_region_count,
    c.cex_interaction_type,
    
    -- 数据质量
    b.data_quality

FROM all_wallets w
LEFT JOIN base_features b ON w.wallet = b.wallet
LEFT JOIN hourly_pivot h ON w.wallet = h.wallet
LEFT JOIN top_tokens t ON w.wallet = t.wallet
LEFT JOIN stablecoin_prefs s ON w.wallet = s.wallet
LEFT JOIN top_namespaces n ON w.wallet = n.wallet
LEFT JOIN protocol_ratios p ON w.wallet = p.wallet
LEFT JOIN final_cex c ON w.wallet = c.wallet;