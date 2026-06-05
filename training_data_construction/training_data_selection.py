import pandas as pd

# 读取 CSV 文件
df = pd.read_csv('Data/wallet_features_10y_with_domain.csv')

# 筛选条件
# 1. total_transactions > 30
# 2. data_quality 为 high 或 very_high
# 3. domain_name 和 top1_cex 至少存在一个
# 4. cex_interaction_type 不是 'cex_address'
filtered_df = df[
    (df['total_transactions'] > 30) &
    (df['data_quality'].isin(['high', 'very_high'])) &
    ((df['domain_name'].notna()) | (df['top1_cex'].notna())) &
    (df['cex_interaction_type'] != 'cex_address')
]

# 按 total_transactions 降序排序（可选，便于查看）
filtered_df = filtered_df.sort_values('total_transactions', ascending=False)

# 输出统计信息
print("=" * 60)
print("筛选结果统计：")
print("=" * 60)
print(f"筛选出的总记录数：{len(filtered_df):,}")
print(f"\n筛选条件：")
print(f"  - total_transactions > 30")
print(f"  - data_quality = high 或 very_high")
print(f"  - domain_name 或 top1_cex 至少一个不为空")
print(f"  - cex_interaction_type != 'cex_address'")
print("=" * 60)

# 进一步统计细分
both_not_empty = filtered_df[(filtered_df['top1_cex'].notna()) & (filtered_df['domain_name'].notna())]
only_top1 = filtered_df[(filtered_df['top1_cex'].notna()) & (filtered_df['domain_name'].isna())]
only_domain = filtered_df[(filtered_df['top1_cex'].isna()) & (filtered_df['domain_name'].notna())]

print(f"\n细分统计：")
print(f"  - 两者都不为空：{len(both_not_empty):,}")
print(f"  - 只有 top1_cex：{len(only_top1):,}")
print(f"  - 只有 domain_name：{len(only_domain):,}")

print(f"\n数据质量分布：")
print(filtered_df['data_quality'].value_counts())

print(f"\ncex_interaction_type 分布：")
print(filtered_df['cex_interaction_type'].value_counts())

print(f"\ntotal_transactions 统计：")
print(f"  - 最小值：{filtered_df['total_transactions'].min()}")
print(f"  - 最大值：{filtered_df['total_transactions'].max():,}")
print(f"  - 平均值：{filtered_df['total_transactions'].mean():.2f}")
print(f"  - 中位数：{filtered_df['total_transactions'].median():.0f}")

# 保存到 CSV 文件
output_file = 'Data/training_data_without_label.csv'
filtered_df.to_csv(output_file, index=False)
print(f"\n数据已保存到：{output_file}")
print(f"文件大小：{len(filtered_df):,} 行 × {len(filtered_df.columns)} 列")
