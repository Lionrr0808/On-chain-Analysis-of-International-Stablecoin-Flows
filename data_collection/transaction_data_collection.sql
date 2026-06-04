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

-- 第二步：获取完整数据（1年范围 + 金额>10 + 随机100万条）
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
    -- Logs表中的ERC-20转账信息
    logs.log_index,
    logs.transaction_hash,
    logs.transaction_index,
    logs.address AS token_contract_address,
    logs.data AS raw_amount_hex,
    logs.topics[SAFE_OFFSET(0)] AS event_signature,
    logs.block_timestamp,
    logs.block_number,
    
    -- 解码后的转账信息
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).from AS transfer_from,
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).to AS transfer_to,
    DECODE_ERC20_TRANSFER(logs.data, logs.topics).value AS raw_value_str,
    
    -- Token元数据
    tokens.symbol,
    SAFE_CAST(tokens.decimals AS INT64) AS decimals,
    
    -- 关联transactions表获取交易详细信息
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
    SAFE_CAST(eth_value_wei AS NUMERIC) / 1e18 AS eth_amount
  FROM decoded_logs
),

filtered_amounts AS (
  SELECT 
    -- 时间特征
    block_timestamp,
    DATE(block_timestamp) AS tx_date,
    EXTRACT(HOUR FROM block_timestamp) AS tx_hour,
    
    -- 交易标识
    transaction_hash,
    block_number,
    transaction_index,
    log_index,
    
    -- 地址信息（重要：用于后续标签匹配）
    transfer_from AS from_address,
    transfer_to AS to_address,
    tx_from_address AS transaction_sender,  -- 交易发起方（可能不同于transfer_from）
    token_contract_address,
    
    -- 金额特征
    token_amount,
    eth_amount,
    
    -- Gas相关特征（反映交易成本和复杂度）
    gas_limit,
    gas_price,
    receipt_gas_used,
    receipt_effective_gas_price,
    max_fee_per_gas,
    max_priority_fee_per_gas,
    transaction_type,
    
    -- 交易成本计算
    (receipt_gas_used * receipt_effective_gas_price) / 1e18 AS transaction_fee_eth,
    
    -- 交易状态和类型
    receipt_status,
    receipt_contract_address,  -- 如果这笔交易创建了新合约
    
    -- Token信息
    symbol,
    decimals,
    
    -- 原始数据（供后续Python解析）
    raw_amount_hex,
    input  -- 交易的input数据，可能包含额外信息
    
  FROM safe_amounts
  WHERE token_amount IS NOT NULL
    AND token_amount > 10
    AND token_amount < 1e12
    AND receipt_status = 1
)

-- 随机抽取 1,000,000 条数据
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
ORDER BY RAND()
LIMIT 1000000;
