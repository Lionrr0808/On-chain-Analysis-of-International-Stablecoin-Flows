CREATE OR REPLACE TABLE `stablecoin-on-chain-analysis.wallets.token_addresses_full` AS

-- 从 crypto_ethereum.tokens 获取已验证的代币
SELECT 
    LOWER(address) as token_address,
    symbol,
    name,
    SAFE_CAST(decimals AS INT64) as decimals
FROM `bigquery-public-data.crypto_ethereum.tokens`
WHERE 
    address IS NOT NULL
    AND symbol IS NOT NULL
    -- 过滤掉明显无效的
    AND LENGTH(symbol) <= 15
    AND LENGTH(symbol) >= 1
    AND SAFE_CAST(decimals AS INT64) IS NOT NULL
    AND SAFE_CAST(decimals AS INT64) <= 18
