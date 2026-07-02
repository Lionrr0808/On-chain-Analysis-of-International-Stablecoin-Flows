-- ============================================================
-- 从交易哈希列表中筛选 Simple Transfer
-- 使用 DECODE_ERC20_TRANSFER 函数（你的成功方案）
-- ============================================================

-- 第一步：创建解码函数（直接从你的代码复制）
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

-- 第二步：从你的哈希表筛选 Simple Transfer
WITH 
target_transactions AS (
  SELECT LOWER(transaction_hash) AS transaction_hash
  FROM `wallets.transaction_hashes`  -- 请替换
),

-- 提取所有 Transfer 事件并使用函数解码
decoded_logs AS (
  SELECT 
    logs.transaction_hash,
    logs.block_timestamp,
    logs.block_number,
    logs.address AS token_contract,
    -- 使用你的解码函数
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).from AS transfer_from,
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).to AS transfer_to,
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).value AS raw_value_str,
    -- 保存原始 topics 供后续调试
    logs.topics
  FROM `bigquery-public-data.crypto_ethereum.logs` AS logs
  INNER JOIN target_transactions AS tgt
    ON logs.transaction_hash = tgt.transaction_hash
  WHERE 
    logs.topics[SAFE_OFFSET(0)] = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
),

-- 按交易分组，统计 Transfer 数量
tx_stats AS (
  SELECT 
    transaction_hash,
    ANY_VALUE(block_timestamp) AS block_timestamp,
    ANY_VALUE(block_number) AS block_number,
    ANY_VALUE(token_contract) AS token_contract,
    ANY_VALUE(transfer_from) AS transfer_from,
    ANY_VALUE(transfer_to) AS transfer_to,
    ANY_VALUE(raw_value_str) AS raw_value_str,
    COUNT(*) AS transfer_count,
    -- 统计有多少条 Transfer 解析成功
    COUNTIF(raw_value_str IS NOT NULL) AS parsed_count
  FROM decoded_logs
  GROUP BY transaction_hash
  -- ✅ 关键：只保留包含 1 个 Transfer 事件的交易（Simple Transfer）
  HAVING COUNT(*) = 1
),

-- 关联代币元数据（从你的代码中复用）
token_metadata AS (
  SELECT 
    address,
    symbol,
    SAFE_CAST(decimals AS INT64) AS decimals
  FROM `bigquery-public-data.crypto_ethereum.tokens`
  WHERE symbol IN ('USDT', 'USDC', 'DAI', 'PYUSD')  -- 根据需要扩展
),

-- 计算金额并关联交易详情
transaction_details AS (
  SELECT 
    s.transaction_hash,
    s.block_timestamp,
    s.transfer_from AS from_address,
    s.transfer_to AS to_address,
    s.token_contract,
    tm.symbol,
    -- 使用你的方法计算金额：raw_value_str / 10^decimals
    SAFE_CAST(s.raw_value_str AS NUMERIC) / POW(10, IFNULL(tm.decimals, 18)) AS token_amount,
    s.raw_value_str,
    s.block_number,
    t.receipt_gas_used AS gas_used,
    t.receipt_effective_gas_price AS effective_gas_price,
    t.receipt_status,
    (CAST(t.receipt_gas_used AS NUMERIC) * CAST(t.receipt_effective_gas_price AS NUMERIC)) / 1e18 AS gas_fee_eth
  FROM tx_stats AS s
  LEFT JOIN token_metadata AS tm
    ON s.token_contract = tm.address
  INNER JOIN `bigquery-public-data.crypto_ethereum.transactions` AS t
    ON s.transaction_hash = t.hash
  WHERE 
    s.raw_value_str IS NOT NULL
    AND SAFE_CAST(s.raw_value_str AS NUMERIC) > 0
    AND t.receipt_status = 1  -- 可选，如果你需要包含失败交易则注释掉
)

-- 最终输出
SELECT 
  transaction_hash,
  block_timestamp,
  from_address,
  to_address,
  token_contract,
  symbol,
  token_amount,
  raw_value_str,
  block_number,
  gas_used,
  effective_gas_price,
  gas_fee_eth,
  receipt_status
FROM transaction_details
ORDER BY block_timestamp DESC;