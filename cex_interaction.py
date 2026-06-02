import pandas as pd
from collections import defaultdict, Counter

print("="*70)
print("全量处理：统计每个钱包的Top5交互CEX地区")
print("="*70)

# 1. 读取文件
print("\n1. 读取文件...")
cex_df = pd.read_csv('cex_addresses.csv', encoding='gbk')
domain_df = pd.read_csv('domain names.csv', encoding='latin1')

print(f"   CEX地址数: {len(cex_df):,}")
print(f"   钱包地址数: {len(domain_df):,}")

# 2. 统一的地址清洗函数
def clean_address(addr):
    if pd.isna(addr):
        return None
    return str(addr).strip().lower()

print("\n2. 清洗地址...")
cex_df['clean_addr'] = cex_df['address'].apply(clean_address)
domain_df['clean_addr'] = domain_df['address'].apply(clean_address)

# 3. 构建CEX映射
cex_dict = dict(zip(cex_df['clean_addr'], cex_df['region']))
cex_set = set(cex_dict.keys())
wallet_set = set(domain_df['clean_addr'])

# 4. 分类钱包
wallet_is_cex = wallet_set & cex_set           # 既是钱包又是CEX
normal_wallets = wallet_set - cex_set          # 普通钱包

print(f"   CEX地址集: {len(cex_set)}")
print(f"   钱包地址集: {len(wallet_set)}")
print(f"   既是钱包又是CEX: {len(wallet_is_cex)}")
print(f"   普通钱包: {len(normal_wallets)}")

# 5. 初始化计数器（只对普通钱包）
print("\n3. 处理交易记录...")
wallet_counter = {wallet: Counter() for wallet in normal_wallets}

# 分块处理交易文件
chunk_size = 100000
total_interactions = 0
chunk_count = 0
total_transactions_processed = 0

for chunk in pd.read_csv('2025.5.1-2026.5.1.csv', 
                         encoding='gbk',
                         usecols=['from_address', 'to_address'],
                         chunksize=chunk_size):
    
    chunk_count += 1
    chunk_transactions = len(chunk)
    total_transactions_processed += chunk_transactions
    
    # 清洗当前块的地址
    chunk['from_clean'] = chunk['from_address'].apply(clean_address)
    chunk['to_clean'] = chunk['to_address'].apply(clean_address)
    
    block_interactions = 0
    for _, row in chunk.iterrows():
        from_addr = row['from_clean']
        to_addr = row['to_clean']
        
        if from_addr is None or to_addr is None:
            continue
        
        # 情况1：普通钱包 -> CEX
        if from_addr in normal_wallets and to_addr in cex_set:
            wallet_counter[from_addr][cex_dict[to_addr]] += 1
            block_interactions += 1
        
        # 情况2：CEX -> 普通钱包
        elif to_addr in normal_wallets and from_addr in cex_set:
            wallet_counter[to_addr][cex_dict[from_addr]] += 1
            block_interactions += 1
    
    total_interactions += block_interactions
    
    # 进度显示：每10000笔交易输出一次（而不是每块）
    if total_transactions_processed % 10000 == 0 or chunk_count == 1:
        print(f"   已处理 {total_transactions_processed:,} 笔交易，"
              f"找到 {total_interactions:,} 次交互，"
              f"有交互的钱包: {sum(1 for c in wallet_counter.values() if c):,}")

print(f"\n   处理完成！")
print(f"   总交易数: {total_transactions_processed:,}")
print(f"   总交互次数: {total_interactions:,}")
print(f"   有交互的普通钱包数: {sum(1 for c in wallet_counter.values() if c):,}")

# 6. 生成结果
print("\n4. 生成结果...")

# 准备结果列表
address_list = []
domain_name_list = []
is_cex_list = []
top1_list = []
top2_list = []
top3_list = []
top4_list = []
top5_list = []

total_wallets = len(domain_df)
for idx, row in domain_df.iterrows():
    original_address = row['address']
    domain_name = row['domain_name']
    clean_wallet = row['clean_addr']
    
    address_list.append(original_address)
    domain_name_list.append(domain_name)
    
    # 情况1：这个地址本身就是CEX地址
    if clean_wallet in cex_set:
        region = cex_dict[clean_wallet]
        is_cex_list.append(True)
        top1_list.append(region)
        top2_list.append(region)
        top3_list.append(region)
        top4_list.append(region)
        top5_list.append(region)
    
    # 情况2：普通钱包
    else:
        is_cex_list.append(False)
        counter = wallet_counter.get(clean_wallet, Counter())
        
        if counter:
            top5_regions = [region for region, _ in counter.most_common(5)]
        else:
            top5_regions = []
        
        # 补齐到5个
        while len(top5_regions) < 5:
            top5_regions.append('')
        
        top1_list.append(top5_regions[0])
        top2_list.append(top5_regions[1])
        top3_list.append(top5_regions[2])
        top4_list.append(top5_regions[3])
        top5_list.append(top5_regions[4])
    
    # 进度显示：每10000个钱包输出一次
    if (idx + 1) % 10000 == 0:
        print(f"   已处理 {(idx + 1):,}/{total_wallets:,} 个钱包")

print(f"   已处理 {total_wallets:,}/{total_wallets:,} 个钱包")

# 7. 创建输出DataFrame
output_df = pd.DataFrame({
    'address': address_list,
    'domain_name': domain_name_list,
    'is_cex': is_cex_list,
    'top1_region': top1_list,
    'top2_region': top2_list,
    'top3_region': top3_list,
    'top4_region': top4_list,
    'top5_region': top5_list
})

# 8. 保存结果
output_file = 'domain_names_with_top5_regions.csv'
output_df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n✅ 结果已保存到: {output_file}")
print(f"   文件行数: {len(output_df):,}")
print(f"   文件列数: {len(output_df.columns)}")

# 9. 验证结果
print("\n5. 验证结果...")

# 统计各种类型的数量
cex_count = output_df['is_cex'].sum()
normal_count = len(output_df) - cex_count
has_interaction = output_df[~output_df['is_cex']]['top1_region'].ne('').sum()

print(f"\n   统计摘要:")
print(f"   总钱包数: {len(output_df):,}")
print(f"   CEX钱包数 (is_cex=True): {cex_count:,}")
print(f"   普通钱包数 (is_cex=False): {normal_count:,}")
print(f"   有交互的普通钱包数: {has_interaction:,}")

# 显示示例
if cex_count > 0:
    print(f"\n   示例1 - CEX钱包 (is_cex=True):")
    cex_examples = output_df[output_df['is_cex']].head(3)
    for _, row in cex_examples.iterrows():
        print(f"     地址: {row['address'][:30]}...")
        print(f"     is_cex: {row['is_cex']}")
        print(f"     Top5: {row['top1_region']}, {row['top2_region']}, {row['top3_region']}...")

interactive_count = output_df[(~output_df['is_cex']) & (output_df['top1_region'] != '')].shape[0]
if interactive_count > 0:
    print(f"\n   示例2 - 有交互的普通钱包:")
    interactive_examples = output_df[(~output_df['is_cex']) & (output_df['top1_region'] != '')].head(5)
    for _, row in interactive_examples.iterrows():
        print(f"     地址: {row['address'][:30]}...")
        print(f"     is_cex: {row['is_cex']}")
        print(f"     Top5: {row['top1_region']}, {row['top2_region']}, {row['top3_region']}")

print(f"\n   示例3 - 无交互的普通钱包:")
no_interaction_examples = output_df[(~output_df['is_cex']) & (output_df['top1_region'] == '')].head(3)
for _, row in no_interaction_examples.iterrows():
    print(f"     地址: {row['address'][:30]}...")
    print(f"     is_cex: {row['is_cex']}")
    print(f"     Top1: '{row['top1_region']}' (空)")

print("\n" + "="*70)
print("处理完成！输出文件列说明:")
print("  - address: 钱包地址")
print("  - domain_name: 域名")
print("  - is_cex: 是否为CEX地址 (True/False)")
print("  - top1_region ~ top5_region: 交互最多的5个CEX地区")
print("="*70)