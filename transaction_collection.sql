-- 第一步：创建解码函数（解析ERC-20金额的标准方法）
CREATE TEMP FUNCTION
  DECODE_ERC20_TRANSFER(data STRING, topics ARRAY<STRING>)
  RETURNS STRUCT<`from` STRING, `to` STRING, value STRING>
  LANGUAGE js AS """
    var transferEvent = {
      "anonymous": false,
      "inputs": [
        {"indexed": true, "name": "from", "type": "address"},
        {"indexed": true, "name": "to", "type": "address"},
        {"indexed": false, "name": "value", "type": "uint256"}
      ],
      "name": "Transfer",
      "type": "event"
    };
    try {
      var iface = new ethers.utils.Interface([transferEvent]);
      var parsedLog = iface.parseLog({topics: topics, data: data});
      return parsedLog.values;
    } catch(e) {
      return {from: null, to: null, value: null};
    }
"""
OPTIONS (library="gs://blockchain-etl-bigquery/ethers.js");

-- 第二步：获取稳定币转账数据（1年 + 金额阈值 >10 + 随机抽取100万条）
WITH stablecoin_tokens AS (
  SELECT 
    address,
    symbol,
    decimals
  FROM `bigquery-public-data.crypto_ethereum.tokens`
  WHERE symbol IN ('USDT', 'USDC', 'DAI')
),

decoded_logs AS (
  SELECT 
    logs.block_timestamp,
    logs.transaction_hash,
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).from AS from_address,
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).to AS to_address,
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).value AS raw_value_str,
    tokens.symbol,
    SAFE_CAST(tokens.decimals AS INT64) AS decimals
  FROM `bigquery-public-data.crypto_ethereum.logs` AS logs
  INNER JOIN stablecoin_tokens AS tokens
    ON logs.address = tokens.address
  WHERE DATE(logs.block_timestamp) BETWEEN '2025-05-01' AND '2026-05-01'
    AND logs.topics[SAFE_OFFSET(0)] = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
),

safe_amounts AS (
  SELECT 
    block_timestamp,
    transaction_hash,
    from_address,
    to_address,
    symbol,
    decimals,
    SAFE_CAST(raw_value_str AS NUMERIC) / POW(10, decimals) AS amount
  FROM decoded_logs
),

filtered_amounts AS (
  SELECT 
    block_timestamp,
    transaction_hash,
    from_address,
    to_address,
    symbol,
    amount
  FROM safe_amounts
  WHERE amount IS NOT NULL
    AND amount > 10
    AND amount < 1e12  -- 单笔不超过1万亿美元
)

-- 随机抽取 1,000,000 条数据
SELECT 
  block_timestamp,
  transaction_hash,
  from_address,
  to_address,
  amount,
  symbol
FROM filtered_amounts
ORDER BY RAND()  -- 随机排序
LIMIT 1000000;