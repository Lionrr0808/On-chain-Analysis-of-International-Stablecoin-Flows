-- 简化版：查询56个指定CEX的核心钱包地址
WITH custom_cex_list AS (
    -- North America (6)
    SELECT 'Binance US' AS cex_name, 'North America' AS region
    UNION ALL SELECT 'Bitbuy', 'North America'
    UNION ALL SELECT 'Coinsquare', 'North America'
    UNION ALL SELECT 'Netcoins', 'North America'
    UNION ALL SELECT 'Quadrigacx', 'North America'
    UNION ALL SELECT 'Shakepay', 'North America'
    -- Europe (13)
    UNION ALL SELECT 'Bitpanda', 'Europe'
    UNION ALL SELECT 'Bitvavo', 'Europe'
    UNION ALL SELECT 'Btcturk', 'Europe'
    UNION ALL SELECT 'Coinmetro', 'Europe'
    UNION ALL SELECT 'Exmo', 'Europe'
    UNION ALL SELECT 'Firi', 'Europe'
    UNION ALL SELECT 'Norwegian Block Exchange', 'Europe'
    UNION ALL SELECT 'Paribu', 'Europe'
    UNION ALL SELECT 'Swissborg', 'Europe'
    UNION ALL SELECT 'Anycoin Direct', 'Europe'
    -- Asia and Pacific (18)
    UNION ALL SELECT 'Bitbank', 'Asia and Pacific'
    UNION ALL SELECT 'Bitkub', 'Asia and Pacific'
    UNION ALL SELECT 'Bithumb', 'Asia and Pacific'
    UNION ALL SELECT 'Coindcx', 'Asia and Pacific'
    UNION ALL SELECT 'Coincheck', 'Asia and Pacific'
    UNION ALL SELECT 'Coinhako', 'Asia and Pacific'
    UNION ALL SELECT 'Coinone', 'Asia and Pacific'
    UNION ALL SELECT 'Coins.ph', 'Asia and Pacific'
    UNION ALL SELECT 'Gdac', 'Asia and Pacific'
    UNION ALL SELECT 'GMO Coin', 'Asia and Pacific'
    UNION ALL SELECT 'Gopax', 'Asia and Pacific'
    UNION ALL SELECT 'Indodax', 'Asia and Pacific'
    UNION ALL SELECT 'Korbit', 'Asia and Pacific'
    UNION ALL SELECT 'Maicoin', 'Asia and Pacific'
    UNION ALL SELECT 'Tokocrypto', 'Asia and Pacific'
    UNION ALL SELECT 'Upbit', 'Asia and Pacific'
    UNION ALL SELECT 'Wazirx', 'Asia and Pacific'
    -- Africa and Middle East (8)
    UNION ALL SELECT 'Altcointrader', 'Africa and Middle East'
    UNION ALL SELECT 'Arzpaya.com', 'Africa and Middle East'
    UNION ALL SELECT 'Artis Turba Exchange', 'Africa and Middle East'
    UNION ALL SELECT 'Bit2c', 'Africa and Middle East'
    UNION ALL SELECT 'Bitoasis', 'Africa and Middle East'
    UNION ALL SELECT 'Luno', 'Africa and Middle East'
    UNION ALL SELECT 'Nobitex', 'Africa and Middle East'
    UNION ALL SELECT 'Valr', 'Africa and Middle East'
    -- Latin America and Caribbean (8)
    UNION ALL SELECT 'Bitso', 'Latin America and Caribbean'
    UNION ALL SELECT 'Brasil Bitcoin', 'Latin America and Caribbean'
    UNION ALL SELECT 'C-Patex', 'Latin America and Caribbean'
    UNION ALL SELECT 'Lemon Cash', 'Latin America and Caribbean'
    UNION ALL SELECT 'Mercado Bitcoin', 'Latin America and Caribbean'
    UNION ALL SELECT 'Orionx', 'Latin America and Caribbean'
    UNION ALL SELECT 'Panda Exchange', 'Latin America and Caribbean'
)

-- 查询地址
SELECT 
    a.address,
    a.cex_name,
    c.region,
    a.distinct_name AS label,
    a.blockchain,
    a.added_date
FROM cex.addresses a
INNER JOIN custom_cex_list c ON LOWER(a.cex_name) = LOWER(c.cex_name)
WHERE a.blockchain = 'ethereum'  -- 只查询以太坊链，可修改
ORDER BY c.region, a.cex_name, a.address