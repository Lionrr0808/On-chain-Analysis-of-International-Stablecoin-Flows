import pandas as pd

# 读取 CSV 文件的第 7 列和第 8 列（索引从 0 开始）
df = pd.read_csv('2025.5.1-2026.5.1.csv', usecols=[7, 8])

# 合并两列，去重，并删除空值
unique_values = pd.Series(
    pd.concat([df.iloc[:, 0], df.iloc[:, 1]]).dropna().unique(),
    name='wallet address'
)

# 保存到新的 CSV 文件
unique_values.to_csv('unique_wallet_addresses.csv', index=False)

print(f"已保存 {len(unique_values)} 个唯一地址到 unique_wallet_addresses.csv")