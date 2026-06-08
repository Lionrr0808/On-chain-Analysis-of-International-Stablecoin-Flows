# convert_labels.py
import pandas as pd

# 标签映射（键用整数和字符串都支持）
REGION_MAPPING = {
    0: "Unclassified",
    1: "Latin America and Caribbean",
    2: "North America",
    3: "Africa and Middle East",
    4: "Europe",
    5: "Asia and Pacific"
}

# 读取 CSV
df = pd.read_csv("classified_domains.csv", encoding='utf-8-sig')

# 检查是否有 domain_name_label 列
if 'domain_name_label' not in df.columns:
    print("❌ 没有找到 domain_name_label 列")
    exit()

# 查看列的数据类型
print(f"domain_name_label 数据类型: {df['domain_name_label'].dtype}")
print(f"示例值: {df['domain_name_label'].head(10).tolist()}")

# 转换为整数（先转为数字，再取整）
def convert_label(label):
    try:
        # 处理 float 类型（如 4.0）
        if pd.isna(label):
            return 0
        # 转为整数
        return int(float(label))
    except (ValueError, TypeError):
        return 0

df['label_int'] = df['domain_name_label'].apply(convert_label)

# 转换为文字标签
df['region_name'] = df['label_int'].map(REGION_MAPPING)

# 删除临时列
df = df.drop(columns=['label_int'])

# 保存新文件
output_file = "classified_domains_with_names.csv"
df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n✅ 转换完成！")
print(f"   输出文件: {output_file}")
print(f"   总行数: {len(df)}")

# 显示转换示例
print("\n转换示例（前10行）:")
print(df[['name', 'domain_name_label', 'region_name']].head(10).to_string(index=False))

print("\n📊 标签分布:")
counts = df['region_name'].value_counts()
for region, count in counts.items():
    print(f"   {region}: {count} 个")