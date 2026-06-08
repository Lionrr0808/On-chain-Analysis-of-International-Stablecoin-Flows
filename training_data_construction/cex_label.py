import pandas as pd

# 读取CSV文件
df = pd.read_csv('training-wallet_features_all_with_name.csv')

# 第一步：筛选出 total_transactions >= 30 的行
df_filtered = df[df['total_transactions'] >= 30].copy()

# 定义需要使用的列
top_cex_columns = [
    'top1_cex', 'top1_cex_region', 'top1_cex_count',
    'top2_cex', 'top2_cex_region', 'top2_cex_count',
    'top3_cex', 'top3_cex_region', 'top3_cex_count',
    'top4_cex', 'top4_cex_region', 'top4_cex_count',
    'top5_cex', 'top5_cex_region', 'top5_cex_count'
]

# 定义打标签的函数
def assign_label(row):
    # 提取 top1 的地区和计数
    top1_region = row['top1_cex_region']
    top1_count = row['top1_cex_count']
    
    # 如果 top1_region 为空，直接返回空
    if pd.isna(top1_region):
        return ''
    
    # 收集所有 top1-top5 的计数（用于计算总和）
    all_counts = []
    for i in range(1, 6):
        count_col = f'top{i}_cex_count'
        if pd.notna(row[count_col]):
            all_counts.append(row[count_col])
    
    total_sum = sum(all_counts)
    
    if total_sum == 0:
        return ''
    
    # 收集与 top1 地区相同的所有计数（包括 top1 本身）
    same_region_count = 0
    for i in range(1, 6):
        region_col = f'top{i}_cex_region'
        count_col = f'top{i}_cex_count'
        if pd.notna(row[region_col]) and pd.notna(row[count_col]):
            if row[region_col] == top1_region:
                same_region_count += row[count_col]
    
    # 计算占比
    ratio = same_region_count / total_sum
    
    # 如果占比 >= 90%，返回 top1 地区标签，否则返回空
    if ratio >= 0.9:
        return top1_region
    else:
        return ''

# 应用标签函数
df_filtered['cex_region_label'] = df_filtered.apply(assign_label, axis=1)

# 保存结果到新文件
df_filtered.to_csv('training_wallet_features_with_cex_label.csv', index=False)

print(f"处理完成！")
print(f"原始数据行数: {len(df)}")
print(f"筛选后行数 (total_transactions >= 30): {len(df_filtered)}")
print(f"\n标签分布（非空）:")
label_counts = df_filtered[df_filtered['cex_region_label'] != '']['cex_region_label'].value_counts()
print(label_counts)
print(f"\n空标签行数: {(df_filtered['cex_region_label'] == '').sum()}")