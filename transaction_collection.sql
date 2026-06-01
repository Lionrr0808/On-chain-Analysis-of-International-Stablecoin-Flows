-- 第一步：创建解码函数
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

-- 第二步：获取完整数据（使用概率抽样避免内存溢出）
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
    logs.log_index,
    logs.transaction_hash,
    logs.transaction_index,
    logs.address AS token_contract_address,
    logs.data AS raw_amount_hex,
    logs.topics[SAFE_OFFSET(0)] AS event_signature,
    logs.block_timestamp,
    logs.block_number,
    
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).from AS transfer_from,
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).to AS transfer_to,
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).value AS raw_value_str,
    
    tokens.symbol,
    SAFE_CAST(tokens.decimals AS INT64) AS decimals,
    
    transactions.nonce,
    transactions.gas AS gas_limit,
    transactions.gas_price,
    transactions.receipt_gas_used,
    transactions.receipt_effective_gas_price,
    transactions.max_fee_per_gas,
    transactions.max_priority_fee_per_gas,
    transactions.transaction_type,
    transactions.value AS eth_value_wei,
    transactions.receipt_status,
    transactions.receipt_contract_address,
    transactions.input,
    transactions.block_hash,
    transactions.from_address AS tx_from_address,
    transactions.to_address AS tx_to_address
    
  FROM `bigquery-public-data.crypto_ethereum.logs` AS logs
  INNER JOIN stablecoin_tokens AS tokens
    ON logs.address = tokens.address
  LEFT JOIN `bigquery-public-data.crypto_ethereum.transactions` AS transactions
    ON logs.transaction_hash = transactions.hash
  WHERE DATE(logs.block_timestamp) BETWEEN '2025-05-01' AND '2026-05-01'
    AND logs.topics[SAFE_OFFSET(0)] = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
),

safe_amounts AS (
  SELECT 
    *,
    SAFE_CAST(raw_value_str AS NUMERIC) / POW(10, decimals) AS token_amount,
    SAFE_CAST(eth_value_wei AS NUMERIC) / 1e18 AS eth_amount,
    (SAFE_CAST(receipt_gas_used AS NUMERIC) * SAFE_CAST(receipt_effective_gas_price AS NUMERIC)) / 1e18 AS transaction_fee_eth
  FROM decoded_logs
),

filtered_amounts AS (
  SELECT 
    block_timestamp,
    DATE(block_timestamp) AS tx_date,
    EXTRACT(HOUR FROM block_timestamp) AS tx_hour,
    
    transaction_hash,
    block_number,
    transaction_index,
    log_index,
    
    transfer_from AS from_address,
    transfer_to AS to_address,
    tx_from_address AS transaction_sender,
    token_contract_address,
    
    token_amount,
    eth_amount,
    
    gas_limit,
    gas_price,
    receipt_gas_used,
    receipt_effective_gas_price,
    max_fee_per_gas,
    max_priority_fee_per_gas,
    transaction_type,
    
    transaction_fee_eth,
    
    receipt_status,
    receipt_contract_address,
    
    symbol,
    decimals,
    
    raw_amount_hex,
    input,
    
    -- 【关键】添加随机数用于抽样
    RAND() AS random_key
    
  FROM safe_amounts
  WHERE token_amount IS NOT NULL
    AND token_amount > 10
    AND token_amount < 1e12
    AND receipt_status = 1
    AND SAFE_CAST(receipt_gas_used AS NUMERIC) < 1e7
    AND SAFE_CAST(receipt_effective_gas_price AS NUMERIC) < 1e12
)

-- 【关键修改】使用 WHERE 概率抽样 + LIMIT，避免 ORDER BY
SELECT 
  block_timestamp,
  tx_date,
  tx_hour,
  transaction_hash,
  block_number,
  transaction_index,
  log_index,
  from_address,
  to_address,
  transaction_sender,
  token_contract_address,
  token_amount,
  eth_amount,
  gas_limit,
  gas_price,
  receipt_gas_used,
  receipt_effective_gas_price,
  max_fee_per_gas,
  max_priority_fee_per_gas,
  transaction_type,
  transaction_fee_eth,
  receipt_status,
  receipt_contract_address,
  symbol,
  decimals,
  raw_amount_hex,
  input
FROM filtered_amounts
WHERE random_key < 0.03  -- 抽取 3%（根据总量调整比例）
LIMIT 1000000;  -- 最终限制输出数量
