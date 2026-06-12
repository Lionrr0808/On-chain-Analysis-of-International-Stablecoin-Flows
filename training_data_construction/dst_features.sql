-- ============================================================
-- 完整DST特征提取（Classification数据使用）
-- 输出所有24个DST特征，缺失值填充-1或0
-- ============================================================

CREATE OR REPLACE TABLE `stablecoin-on-chain-analysis.wallets.classification_dst_features_complete` AS

WITH 
-- 1. 钱包列表
all_wallets AS (
    SELECT DISTINCT LOWER(`wallet address`) as wallet
    FROM `stablecoin-on-chain-analysis.wallets.wallet_list`
    WHERE `wallet address` IS NOT NULL
),

-- 2. 交易数据（10年）
wallet_txs AS (
    SELECT 
        LOWER(t.from_address) as wallet,
        t.block_timestamp,
        EXTRACT(HOUR FROM t.block_timestamp) as tx_hour_utc,
        EXTRACT(MONTH FROM t.block_timestamp) as tx_month,
        EXTRACT(DAY FROM t.block_timestamp) as tx_day,
        EXTRACT(DAYOFWEEK FROM t.block_timestamp) as tx_dow,
        DATE(t.block_timestamp) as tx_date
    FROM `bigquery-public-data.crypto_ethereum.transactions` t
    INNER JOIN all_wallets w ON LOWER(t.from_address) = w.wallet
    WHERE 
        t.block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3649 DAY)
        AND t.receipt_status = 1
        AND t.gas_price > 0
        AND t.receipt_gas_used > 0
),

-- 3. 标记DST期间（北半球标准：3月第2个周日 ~ 11月第1个周日）
wallet_txs_with_dst AS (
    SELECT 
        wallet,
        tx_hour_utc,
        tx_month,
        tx_day,
        -- 判断是否在DST期间
        CASE 
            WHEN tx_month IN (6, 7, 8) THEN TRUE
            WHEN tx_month = 5 THEN TRUE
            WHEN tx_month = 4 THEN TRUE
            WHEN tx_month = 9 THEN TRUE
            WHEN tx_month = 3 AND tx_day >= 14 THEN TRUE
            WHEN tx_month = 10 AND tx_day <= 7 THEN TRUE
            ELSE FALSE
        END as is_dst,
        -- 判断是否在非DST期间
        CASE 
            WHEN tx_month IN (1, 2) THEN TRUE
            WHEN tx_month = 12 THEN TRUE
            WHEN tx_month = 11 AND tx_day >= 8 THEN TRUE
            WHEN tx_month = 3 AND tx_day <= 13 THEN TRUE
            WHEN tx_month = 10 AND tx_day >= 8 THEN TRUE
            ELSE FALSE
        END as is_non_dst
    FROM wallet_txs
),

-- 4. DST期间分布
dst_distribution AS (
    SELECT 
        wallet,
        tx_hour_utc,
        COUNT(*) as tx_count,
        COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY wallet) as hour_ratio
    FROM wallet_txs_with_dst
    WHERE is_dst = TRUE
    GROUP BY wallet, tx_hour_utc
),

-- 5. 非DST期间分布
non_dst_distribution AS (
    SELECT 
        wallet,
        tx_hour_utc,
        COUNT(*) as tx_count,
        COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY wallet) as hour_ratio
    FROM wallet_txs_with_dst
    WHERE is_non_dst = TRUE
    GROUP BY wallet, tx_hour_utc
),

-- 6. DST和非DST统计特征
dst_stats AS (
    SELECT 
        wallet,
        -- DST期间特征
        MAX(CASE WHEN is_dst THEN tx_hour_utc END) as dst_peak_hour,
        AVG(CASE WHEN is_dst THEN tx_hour_utc END) as dst_mean_hour,
        STDDEV(CASE WHEN is_dst THEN tx_hour_utc END) as dst_std_hour,
        COUNT(DISTINCT CASE WHEN is_dst THEN tx_hour_utc END) as dst_active_hours,
        COUNT(CASE WHEN is_dst THEN 1 END) as dst_tx_count,
        
        -- 非DST期间特征
        MAX(CASE WHEN is_non_dst THEN tx_hour_utc END) as non_dst_peak_hour,
        AVG(CASE WHEN is_non_dst THEN tx_hour_utc END) as non_dst_mean_hour,
        STDDEV(CASE WHEN is_non_dst THEN tx_hour_utc END) as non_dst_std_hour,
        COUNT(DISTINCT CASE WHEN is_non_dst THEN tx_hour_utc END) as non_dst_active_hours,
        COUNT(CASE WHEN is_non_dst THEN 1 END) as non_dst_tx_count
    FROM wallet_txs_with_dst
    GROUP BY wallet
),

-- 7. 位移特征
dst_shift_features AS (
    SELECT 
        wallet,
        dst_mean_hour - non_dst_mean_hour as dst_shift_mean,
        dst_peak_hour - non_dst_peak_hour as dst_shift_peak,
        dst_std_hour - non_dst_std_hour as dst_shift_std,
        SAFE_DIVIDE(dst_tx_count, non_dst_tx_count) as dst_activity_ratio,
        CASE 
            WHEN ABS(dst_mean_hour - non_dst_mean_hour) > 0.5 THEN 1 
            ELSE 0 
        END as has_dst_behavior,
        ABS(dst_mean_hour - non_dst_mean_hour) as dst_behavior_strength
    FROM dst_stats
),

-- 8. 分布差异特征
distribution_diff AS (
    SELECT 
        COALESCE(d.wallet, n.wallet) as wallet,
        COALESCE(d.tx_hour_utc, n.tx_hour_utc) as hour,
        COALESCE(d.hour_ratio, 0) as dst_ratio,
        COALESCE(n.hour_ratio, 0) as non_dst_ratio
    FROM dst_distribution d
    FULL OUTER JOIN non_dst_distribution n 
        ON d.wallet = n.wallet AND d.tx_hour_utc = n.tx_hour_utc
),

distribution_stats AS (
    SELECT 
        wallet,
        -- L1距离（总差异）
        SUM(ABS(dst_ratio - non_dst_ratio)) as dst_distribution_shift_l1,
        -- 欧氏距离
        SQRT(SUM(POW(dst_ratio - non_dst_ratio, 2))) as dst_distribution_shift_euclidean,
        -- 最大差异
        MAX(ABS(dst_ratio - non_dst_ratio)) as dst_max_hour_shift,
        -- 差异最大的小时
        ARRAY_AGG(
            STRUCT(hour, ABS(dst_ratio - non_dst_ratio) as diff)
            ORDER BY ABS(dst_ratio - non_dst_ratio) DESC
            LIMIT 1
        )[OFFSET(0)].hour as dst_max_shift_hour,
        -- 加权平均位移小时
        SUM(ABS(dst_ratio - non_dst_ratio) * hour) / NULLIF(SUM(ABS(dst_ratio - non_dst_ratio)), 0) as dst_weighted_shift_hour
    FROM distribution_diff
    GROUP BY wallet
),

-- 9. 季节性模式
seasonal_pattern AS (
    SELECT 
        wallet,
        -- 夏季（6-8月）平均小时
        AVG(CASE WHEN tx_month IN (6,7,8) THEN tx_hour_utc END) as summer_mean_hour,
        -- 冬季（12-2月）平均小时
        AVG(CASE WHEN tx_month IN (12,1,2) THEN tx_hour_utc END) as winter_mean_hour,
        -- 季节差异
        AVG(CASE WHEN tx_month IN (6,7,8) THEN tx_hour_utc END) - 
        AVG(CASE WHEN tx_month IN (12,1,2) THEN tx_hour_utc END) as seasonal_shift
    FROM wallet_txs_with_dst
    GROUP BY wallet
)

-- 10. 最终输出（所有特征，NULL填充-1或0）
SELECT 
    w.wallet,
    
    -- ========== DST位移特征 ==========
    IFNULL(ROUND(ds.dst_shift_mean, 4), -1) as dst_shift_mean,
    IFNULL(ROUND(ds.dst_shift_peak, 4), -1) as dst_shift_peak,
    IFNULL(ROUND(ds.dst_shift_std, 4), -1) as dst_shift_std,
    IFNULL(ROUND(ds.dst_activity_ratio, 4), -1) as dst_activity_ratio,
    IFNULL(ds.has_dst_behavior, 0) as has_dst_behavior,
    IFNULL(ROUND(ds.dst_behavior_strength, 4), 0) as dst_behavior_strength,
    
    -- ========== DST期间统计 ==========
    IFNULL(ROUND(dst.dst_mean_hour, 4), -1) as dst_mean_hour,
    IFNULL(dst.dst_peak_hour, -1) as dst_peak_hour,
    IFNULL(ROUND(dst.dst_std_hour, 4), -1) as dst_std_hour,
    IFNULL(dst.dst_active_hours, -1) as dst_active_hours,
    IFNULL(dst.dst_tx_count, -1) as dst_tx_count,
    
    -- ========== 非DST期间统计 ==========
    IFNULL(ROUND(dst.non_dst_mean_hour, 4), -1) as non_dst_mean_hour,
    IFNULL(dst.non_dst_peak_hour, -1) as non_dst_peak_hour,
    IFNULL(ROUND(dst.non_dst_std_hour, 4), -1) as non_dst_std_hour,
    IFNULL(dst.non_dst_active_hours, -1) as non_dst_active_hours,
    IFNULL(dst.non_dst_tx_count, -1) as non_dst_tx_count,
    
    -- ========== 分布差异特征 ==========
    IFNULL(ROUND(dd.dst_distribution_shift_l1, 4), -1) as dst_distribution_shift_l1,
    IFNULL(ROUND(dd.dst_distribution_shift_euclidean, 4), -1) as dst_distribution_shift_euclidean,
    IFNULL(ROUND(dd.dst_max_hour_shift, 6), -1) as dst_max_hour_shift,
    IFNULL(dd.dst_max_shift_hour, -1) as dst_max_shift_hour,
    IFNULL(ROUND(dd.dst_weighted_shift_hour, 4), -1) as dst_weighted_shift_hour,
    
    -- ========== 季节性模式 ==========
    IFNULL(ROUND(sp.summer_mean_hour, 4), -1) as summer_mean_hour,
    IFNULL(ROUND(sp.winter_mean_hour, 4), -1) as winter_mean_hour,
    IFNULL(ROUND(sp.seasonal_shift, 4), -1) as seasonal_shift

FROM all_wallets w
LEFT JOIN dst_stats dst ON w.wallet = dst.wallet
LEFT JOIN dst_shift_features ds ON w.wallet = ds.wallet
LEFT JOIN distribution_stats dd ON w.wallet = dd.wallet
LEFT JOIN seasonal_pattern sp ON w.wallet = sp.wallet;