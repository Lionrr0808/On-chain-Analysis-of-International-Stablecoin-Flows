# extract_consistent_data.py
import pandas as pd

# 文件路径
input_file = "training_set_with_two_labels.csv"
output_file = "final_training_data.csv"

print("="*60)
print("提取一致数据 - 构建最终训练集")
print("="*60)

# 读取文件
print("\n1. 读取文件...")
df = pd.read_csv(input_file, encoding='utf-8-sig')
print(f"   ✅ 共 {len(df)} 行")

# 检查列
if 'cex_region_label' not in df.columns or 'domain_name_label' not in df.columns:
    print("❌ 缺少必要列")
    exit()

# 统一格式
df['cex_region_label'] = df['cex_region_label'].astype(str).str.strip()
df['domain_name_label'] = df['domain_name_label'].astype(str).str.strip()

# 筛选一致的数据
print("\n2. 筛选一致的数据...")
consistent_mask = df['cex_region_label'] == df['domain_name_label']
df_consistent = df[consistent_mask].copy()
consistent_count = len(df_consistent)
total_count = len(df)

print(f"   ✅ 一致数据: {consistent_count} 个 ({consistent_count/total_count*100:.2f}%)")
print(f"   ⚠️ 剔除不一致: {total_count - consistent_count} 个")

# 添加 final_label 列（使用一致的标签）
df_consistent['final_label'] = df_consistent['cex_region_label']

# 可选：把数字标签转换成文字（如果你想要文字标签）
region_names = {
    "0": "Unclassified",
    "1": "Latin America and Caribbean",
    "2": "North America",
    "3": "Africa and Middle East",
    "4": "Europe",
    "5": "Asia and Pacific"
}
df_consistent['final_label_name'] = df_consistent['final_label'].map(region_names)

# 保存
print("\n3. 保存文件...")
df_consistent.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"   ✅ 已保存到: {output_file}")

# 统计
print("\n" + "="*60)
print("📊 最终训练集统计")
print("="*60)
print(f"   总样本数: {len(df_consistent)}")
print(f"   列数: {len(df_consistent.columns)}")

print("\n标签分布:")
label_counts = df_consistent['final_label_name'].value_counts()
for label, count in label_counts.items():
    print(f"   {label}: {count} 个 ({count/len(df_consistent)*100:.1f}%)")

print(f"\n✅ 完成！")
print(f"   输出文件: {output_file}")
print(f"   最后一列: final_label (数字) 和 final_label_name (文字)")