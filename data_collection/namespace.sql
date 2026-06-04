-- ============================================================
-- 创建完整的智能合约命名空间表
-- 按功能分类：DEX、Lending、Bridge、NFT、Yield、Oracle 等
-- ============================================================
CREATE OR REPLACE TABLE `stablecoin-on-chain-analysis.wallets.namespace_addresses_full` AS

-- DEX（去中心化交易所）
SELECT 'dex' as namespace, LOWER('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D') as contract_address, 'Uniswap V2 Router' as description UNION ALL
SELECT 'dex', LOWER('0xE592427A0AEce92De3Edee1F18E0157C05861564'), 'Uniswap V3 Router' UNION ALL
SELECT 'dex', LOWER('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'), 'SushiSwap Router' UNION ALL
SELECT 'dex', LOWER('0xDef1C0ded9bec7F1a1670819833240f027b25EfF'), '0x Exchange Proxy' UNION ALL
SELECT 'dex', LOWER('0x1111111254fb6c44bAC0beD2854e76F90643097d'), '1inch Router' UNION ALL
SELECT 'dex', LOWER('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'), 'Curve.fi' UNION ALL
SELECT 'dex', LOWER('0x33128a8fC17869897dcE68Ed026d694621f6FDfD'), 'Balancer V2' UNION ALL
SELECT 'dex', LOWER('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'), 'Uniswap V3 Positions NFT' UNION ALL

-- Lending（借贷协议）
SELECT 'lending' as namespace, LOWER('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'), 'Aave V2' UNION ALL
SELECT 'lending', LOWER('0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf'), 'Aave V3' UNION ALL
SELECT 'lending', LOWER('0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B'), 'Compound V2' UNION ALL
SELECT 'lending', LOWER('0x68776a9278b43FAf0b6ea0562AF128ABf9A11c73'), 'Compound III' UNION ALL
SELECT 'lending', LOWER('0xBA12222222228d8Ba445958a75a0704d566BF2C8'), 'Balancer Vault' UNION ALL

-- Bridge（跨链桥）
SELECT 'bridge' as namespace, LOWER('0x3ee18B2214AFF97000D974cf647E7C347E8fa585'), 'Arbitrum Bridge' UNION ALL
SELECT 'bridge', LOWER('0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1'), 'Optimism Bridge' UNION ALL
SELECT 'bridge', LOWER('0x10E6593CDda8c110a252d6CbD6b61f6A7E5a0F6f'), 'Polygon Bridge (PoS)' UNION ALL
SELECT 'bridge', LOWER('0x87959Ad6bE9E85Ed6F717e0FcC2F6f9069C8E92e'), 'Multichain Router' UNION ALL
SELECT 'bridge', LOWER('0xa5DA9B691FcEFE2d6b5eA334270DE979B940bA18'), 'Hop Protocol' UNION ALL

-- NFT Marketplace
SELECT 'nft' as namespace, LOWER('0x00000000006c3852cbEf3e08E8dF289169EdE581'), 'OpenSea (Seaport)' UNION ALL
SELECT 'nft', LOWER('0x000000000000AD05Ccc4F10045630aF830A5F3E4'), 'LooksRare' UNION ALL
SELECT 'nft', LOWER('0x59728544B08AB483533076417FbBB2fD0B17CE3a'), 'X2Y2' UNION ALL
SELECT 'nft', LOWER('0xA9e5F5eB63cB00378550C555673b33260C6E617C'), 'Rarible' UNION ALL

-- Yield / Staking（收益聚合器）
SELECT 'yield' as namespace, LOWER('0x7fC77b5c7614E1533320Ea6DDc2Eb61fa00A9714'), 'Convex Finance' UNION ALL
SELECT 'yield', LOWER('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'), 'Yearn Finance' UNION ALL
SELECT 'yield', LOWER('0xd8b8A62E0E0E1aCcbCDb31F947A49cC75E4E119b'), 'Stake DAO' UNION ALL

-- Oracle（预言机）
SELECT 'oracle' as namespace, LOWER('0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419'), 'Chainlink ETH/USD' UNION ALL
SELECT 'oracle', LOWER('0xCdF702e8DA5bEe28B7b571A83C725f8BeA2A68c5'), 'Chainlink LINK/ETH' UNION ALL

-- Social（社交/域名）
SELECT 'social' as namespace, LOWER('0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85'), 'ENS (Ethereum Name Service)' UNION ALL
SELECT 'social', LOWER('0x4b1488B7a6B320d2D721406204aBc3eeAa9AD329'), 'Lens Protocol' UNION ALL

-- Gaming（游戏）
SELECT 'gaming' as namespace, LOWER('0x28828f2CC9c708ad6B75D8adcC60525Fe25b673a'), 'Gala Games' UNION ALL
SELECT 'gaming', LOWER('0x4C32Cb97bEC27C5dA2FcFa6E1A4F211fC12CD868'), 'Sandbox' UNION ALL

-- Privacy / Mixer（隐私/混币器 - 可选，谨慎使用）
SELECT 'privacy' as namespace, LOWER('0x8589427373D6D84E98730D7795D8f6f8731FDA16'), 'Tornado Cash' UNION ALL

-- Liquid Staking（流动性质押）
SELECT 'liquid_staking' as namespace, LOWER('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'), 'Lido stETH' UNION ALL
SELECT 'liquid_staking', LOWER('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'), 'Rocket Pool' UNION ALL

-- Perpetuals DEX（永续合约）
SELECT 'perpetuals' as namespace, LOWER('0x7Fc9D0E2b7638e4AF95ea9D4ABcFACF09F327293'), 'GMX V2' UNION ALL
SELECT 'perpetuals', LOWER('0xF1DCF9cCca7fB4FddcEdAD4C42C34B0C09433080'), 'dYdX' UNION ALL

-- Launchpad（代币发射平台）
SELECT 'launchpad' as namespace, LOWER('0x5B8C6B2B863d0a269cE2675AeE17E02C524eBf69'), 'CoinList' UNION ALL
SELECT 'launchpad', LOWER('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'), 'Uniswap Factory';

-- 查看统计
SELECT 
    namespace, 
    COUNT(*) as contract_count
FROM `stablecoin-on-chain-analysis.wallets.namespace_addresses_full`
GROUP BY namespace
ORDER BY contract_count DESC;