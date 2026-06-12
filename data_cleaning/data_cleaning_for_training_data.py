import pandas as pd
import numpy as np
from numpy.polynomial import Polynomial
import warnings
warnings.filterwarnings('ignore')


def load_and_deduplicate_wallet(file_path):
    """
    加载数据并根据wallet去重，处理标签不一致的情况
    只保留需要的原始列，其他全部丢弃
    """
    print("=" * 60)
    print("步骤1: 加载数据并处理重复钱包")
    print("=" * 60)
    
    # 定义需要读取的列（只读取需要的，节省内存）
    required_columns = [
        'wallet', 'final_label',
        # 24小时特征
        'pct_hour_0', 'pct_hour_1', 'pct_hour_2', 'pct_hour_3', 'pct_hour_4',
        'pct_hour_5', 'pct_hour_6', 'pct_hour_7', 'pct_hour_8', 'pct_hour_9',
        'pct_hour_10', 'pct_hour_11', 'pct_hour_12', 'pct_hour_13', 'pct_hour_14',
        'pct_hour_15', 'pct_hour_16', 'pct_hour_17', 'pct_hour_18', 'pct_hour_19',
        'pct_hour_20', 'pct_hour_21', 'pct_hour_22', 'pct_hour_23',
        # 金额特征
        'avg_transaction_amount_eth', 'large_tx_ratio', 'micro_tx_ratio',
        # 时间比例特征
        'night_ratio', 'early_morning_ratio', 'daytime_ratio', 'weekend_ratio',
        # 季节性特征
        'avg_tx_hour_period1', 'avg_tx_hour_period2', 'avg_tx_hour_period3', 
        'avg_tx_hour_period4', 'tx_hour_variance',
        # Gas特征
        'avg_gas_price', 'avg_tx_fee_eth',
        # 活动特征
        'wallet_age_days', 'active_days', 'avg_tx_per_day',
        # 协议特征
        'dex_count', 'lending_count', 'nft_count', 'bridge_count',
        # Top tokens (top1-10)
        'top1_token', 'top1_token_count', 'top2_token', 'top2_token_count',
        'top3_token', 'top3_token_count', 'top4_token', 'top4_token_count',
        'top5_token', 'top5_token_count', 'top6_token', 'top6_token_count',
        'top7_token', 'top7_token_count', 'top8_token', 'top8_token_count',
        'top9_token', 'top9_token_count', 'top10_token', 'top10_token_count',
        # Top namespaces (top1-10)
        'top1_namespace', 'top1_namespace_count', 'top2_namespace', 'top2_namespace_count',
        'top3_namespace', 'top3_namespace_count', 'top4_namespace', 'top4_namespace_count',
        'top5_namespace', 'top5_namespace_count', 'top6_namespace', 'top6_namespace_count',
        'top7_namespace', 'top7_namespace_count', 'top8_namespace', 'top8_namespace_count',
        'top9_namespace', 'top9_namespace_count', 'top10_namespace', 'top10_namespace_count',
        # CEX特征 (top1-3)
        'top1_cex_region', 'top1_cex_count', 'top2_cex_region', 'top2_cex_count',
        'top3_cex_region', 'top3_cex_count', 'cex_interaction_type'
    ]
    
    # 读取CSV，只读取需要的列
    try:
        df = pd.read_csv(file_path, usecols=[col for col in required_columns if col in pd.read_csv(file_path, nrows=0).columns])
    except:
        # 如果无法提前获取列名，先读取全部再筛选
        df = pd.read_csv(file_path)
        available_cols = [col for col in required_columns if col in df.columns]
        df = df[available_cols + (['wallet', 'final_label'] if 'final_label' in df.columns else [])]
    
    print(f"原始数据形状: {df.shape}")
    print(f"原始唯一钱包数: {df['wallet'].nunique()}")
    
    # 处理重复钱包：选择出现最多的final_label
    def get_majority_label(group):
        return group.mode()[0] if not group.mode().empty else group.iloc[0]
    
    # 按wallet分组聚合
    agg_dict = {
        'final_label': get_majority_label,
    }
    
    # 添加所有数值特征到聚合字典（取均值）
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in numeric_cols:
        if col != 'wallet':
            agg_dict[col] = 'mean'
    
    # 添加分类特征（取众数）
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    for col in categorical_cols:
        if col not in ['wallet', 'final_label']:
            agg_dict[col] = lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0]
    
    df_dedup = df.groupby('wallet').agg(agg_dict).reset_index()
    
    # 检查标签不一致的情况
    label_conflicts = df.groupby('wallet')['final_label'].nunique()
    conflict_wallets = label_conflicts[label_conflicts > 1].index.tolist()
    print(f"标签不一致的钱包数: {len(conflict_wallets)}")
    print(f"去重后数据形状: {df_dedup.shape}")
    print(f"去重后唯一钱包数: {df_dedup['wallet'].nunique()}")
    
    return df_dedup


def polynomial_features_from_hours(df):
    """
    将24小时百分比数据转换为3次多项式系数
    """
    print("\n" + "=" * 60)
    print("步骤2: 24小时分布 → 3次多项式系数")
    print("=" * 60)
    
    hour_cols = [f'pct_hour_{i}' for i in range(24)]
    available_cols = [col for col in hour_cols if col in df.columns]
    
    if not available_cols:
        print("警告: 未找到小时特征列，跳过此步骤")
        return df
    
    print(f"找到 {len(available_cols)} 个小时特征列")
    
    # 空值填充0
    df[available_cols] = df[available_cols].fillna(0)
    
    # 检查数据样例
    sample_row = df[available_cols].iloc[0]
    print(f"样例小时分布总和: {sample_row.sum():.4f}")
    
    # 提取小时数据并转换为多项式系数
    polynomial_coeffs = []
    hours = np.arange(24)
    # 标准化小时值到[-1, 1]范围，提高数值稳定性
    hours_normalized = (hours - 11.5) / 12.5
    
    for idx, row in df.iterrows():
        hourly_pct = row[available_cols].values.astype(float)
        
        # 如果总和为0（全零），使用均匀分布
        if hourly_pct.sum() == 0:
            hourly_pct = np.ones(24) / 24
        
        try:
            coeffs = Polynomial.fit(hours_normalized, hourly_pct, deg=3).convert().coef
            polynomial_coeffs.append(coeffs)
        except Exception as e:
            polynomial_coeffs.append([0, 0, 0, 0])
    
    # 创建多项式系数特征
    coeff_df = pd.DataFrame(polynomial_coeffs, 
                           columns=['pct_poly_c0', 'pct_poly_c1', 'pct_poly_c2', 'pct_poly_c3'])
    
    # 检查系数是否全零
    print(f"多项式系数统计:")
    for col in coeff_df.columns:
        non_zero_count = (coeff_df[col] != 0).sum()
        print(f"  {col}: 非零值数量 = {non_zero_count}/{len(coeff_df)}")
    
    df = pd.concat([df, coeff_df], axis=1)
    
    # 删除原始小时特征
    df = df.drop(columns=available_cols)
    
    print(f"新增特征: pct_poly_c0, pct_poly_c1, pct_poly_c2, pct_poly_c3")
    print(f"删除原始小时特征: {len(available_cols)}个")
    
    return df


def process_numerical_features(df, feature_list, fill_value=0):
    """
    处理数值特征：空值填充
    """
    for feature in feature_list:
        if feature in df.columns:
            df[feature] = df[feature].fillna(fill_value)
    return df


def process_top_tokens(df):
    """
    处理Top Tokens: 
    - 保留top1-5的token名称和计数
    - top6-10转换为聚合特征后删除原始列
    """
    print("\n" + "=" * 60)
    print("步骤3: 处理Top Tokens (保留top1-5, top6-10聚合)")
    print("=" * 60)
    
    # 处理top1-5：空值处理
    for i in range(1, 6):
        token_col = f'top{i}_token'
        count_col = f'top{i}_token_count'
        
        if token_col in df.columns:
            # 直接转换为category，保持NaN不变
            df[token_col] = df[token_col].astype('category')
        if count_col in df.columns:
            df[count_col] = df[count_col].fillna(0)
    
    # 处理top6-10：聚合特征
    token_count_cols = [f'top{i}_token_count' for i in range(6, 11) if f'top{i}_token_count' in df.columns]
    token_name_cols = [f'top{i}_token' for i in range(6, 11) if f'top{i}_token' in df.columns]
    
    if token_count_cols:
        # 聚合特征1: top6-10总交易次数
        df['top6_10_token_total_count'] = df[token_count_cols].sum(axis=1)
        
        # 聚合特征2: top6-10唯一token数量
        # 先将NaN填充为临时字符串再计算
        df_temp = df[token_name_cols].fillna('_null_')
        df['top6_10_token_diversity'] = df_temp.nunique(axis=1)
        
        # 聚合特征3: top6-10占总交易的比例（如果有total_transactions）
        if 'total_transactions' in df.columns:
            df['top6_10_token_ratio'] = df['top6_10_token_total_count'] / df['total_transactions'].replace(0, 1)
        else:
            df['top6_10_token_ratio'] = 0
        
        # 删除原始top6-10特征
        df = df.drop(columns=token_count_cols + token_name_cols)
        print(f"新增聚合特征: top6_10_token_total_count, top6_10_token_diversity, top6_10_token_ratio")
        print(f"删除原始top6-10特征: {len(token_count_cols + token_name_cols)}个")
    
    return df


def process_top_namespaces(df):
    """
    处理Top Namespaces:
    - 保留top1-5的namespace名称和计数
    - top6-10转换为聚合特征后删除原始列
    """
    print("\n" + "=" * 60)
    print("步骤4: 处理Top Namespaces (保留top1-5, top6-10聚合)")
    print("=" * 60)
    
    # 处理top1-5：空值处理
    for i in range(1, 6):
        ns_col = f'top{i}_namespace'
        count_col = f'top{i}_namespace_count'
        
        if ns_col in df.columns:
            # 直接转换为category，保持NaN不变
            df[ns_col] = df[ns_col].astype('category')
        if count_col in df.columns:
            df[count_col] = df[count_col].fillna(0)
    
    # 处理top6-10：聚合特征
    ns_count_cols = [f'top{i}_namespace_count' for i in range(6, 11) if f'top{i}_namespace_count' in df.columns]
    ns_name_cols = [f'top{i}_namespace' for i in range(6, 11) if f'top{i}_namespace' in df.columns]
    
    if ns_count_cols:
        # 聚合特征1: top6-10总交互次数
        df['top6_10_namespace_total_count'] = df[ns_count_cols].sum(axis=1)
        
        # 聚合特征2: top6-10唯一namespace数量
        # 先将NaN填充为临时字符串再计算
        df_temp = df[ns_name_cols].fillna('_null_')
        df['top6_10_namespace_diversity'] = df_temp.nunique(axis=1)
        
        # 聚合特征3: top6-10占总交互的比例
        if 'total_transactions' in df.columns:
            df['top6_10_namespace_ratio'] = df['top6_10_namespace_total_count'] / df['total_transactions'].replace(0, 1)
        else:
            df['top6_10_namespace_ratio'] = 0
        
        # 删除原始top6-10特征
        df = df.drop(columns=ns_count_cols + ns_name_cols)
        print(f"新增聚合特征: top6_10_namespace_total_count, top6_10_namespace_diversity, top6_10_namespace_ratio")
        print(f"删除原始top6-10特征: {len(ns_count_cols + ns_name_cols)}个")
    
    return df


def process_cex_features(df):
    """
    处理CEX特征:
    - 保留 top1-2 的 cex_region 和 cex_count
    - top3-5 转换为聚合特征后删除原始列
    """
    print("\n" + "=" * 60)
    print("步骤5: 处理CEX特征 (保留top1-2, top3-5聚合)")
    print("=" * 60)
    
    # 处理top1-2 CEX count（数值特征，直接填充0）
    for i in range(1, 3):
        count_col = f'top{i}_cex_count'
        if count_col in df.columns:
            df[count_col] = df[count_col].fillna(0)
    
    # 处理top1-2 CEX region（先填充临时值用于计算，稍后替换回NaN）
    for i in range(1, 3):
        region_col = f'top{i}_cex_region'
        if region_col in df.columns:
            # 先填充NaN为临时字符串，用于计算聚合特征
            df[region_col] = df[region_col].fillna('_no_cex_')
    
    # 处理cex_interaction_type
    if 'cex_interaction_type' in df.columns:
        df['cex_interaction_type'] = df['cex_interaction_type'].fillna('no_cex_interaction')
    
    # ========== 处理 top3-5：聚合特征 ==========
    # top3-5 的 count 列
    count_cols_3_5 = [f'top{i}_cex_count' for i in range(3, 6) if f'top{i}_cex_count' in df.columns]
    # top3-5 的 region 列
    region_cols_3_5 = [f'top{i}_cex_region' for i in range(3, 6) if f'top{i}_cex_region' in df.columns]
    
    if count_cols_3_5:
        # 先填充NaN为0
        for col in count_cols_3_5:
            df[col] = df[col].fillna(0)
        
        # 聚合特征1: top3-5总交互次数
        df['top3_5_cex_total_count'] = df[count_cols_3_5].sum(axis=1)
        
        # 聚合特征2: top3-5唯一CEX区域数量
        if region_cols_3_5:
            # 先填充NaN为临时字符串
            for col in region_cols_3_5:
                df[col] = df[col].fillna('_no_cex_')
            df_region_temp = df[region_cols_3_5].copy()
            df['top3_5_cex_region_diversity'] = df_region_temp.nunique(axis=1)
        else:
            df['top3_5_cex_region_diversity'] = 0
        
        # 删除原始top3-5特征
        df = df.drop(columns=count_cols_3_5 + region_cols_3_5)
        print(f"新增聚合特征: top3_5_cex_total_count, top3_5_cex_region_diversity")
        print(f"删除原始top3-5特征: {len(count_cols_3_5 + region_cols_3_5)}个")
    
    # ========== top1-2 聚合特征 ==========
    # 聚合特征：top1-2总交互次数
    count_cols_1_2 = [f'top{i}_cex_count' for i in range(1, 3) if f'top{i}_cex_count' in df.columns]
    if count_cols_1_2:
        df['top1_2_cex_total_count'] = df[count_cols_1_2].sum(axis=1)
        
        # 聚合特征：唯一CEX区域数量
        region_cols_1_2 = [f'top{i}_cex_region' for i in range(1, 3) if f'top{i}_cex_region' in df.columns]
        if region_cols_1_2:
            df_region_temp = df[region_cols_1_2].copy()
            df['top1_2_cex_region_diversity'] = df_region_temp.nunique(axis=1)
            df['has_multiple_cex_regions'] = (df['top1_2_cex_region_diversity'] > 1).astype(int)
        
        print(f"新增聚合特征: top1_2_cex_total_count, top1_2_cex_region_diversity, has_multiple_cex_regions")
    
    # 现在将 region 列中的 '_no_cex_' 替换回 NaN，然后转换为 category
    for i in range(1, 3):
        region_col = f'top{i}_cex_region'
        if region_col in df.columns:
            # 将临时填充值替换回 NaN
            df[region_col] = df[region_col].replace('_no_cex_', np.nan)
            # 转换为 category，保留 NaN
            df[region_col] = df[region_col].astype('category')
    
    # 转换 cex_interaction_type 为 category
    if 'cex_interaction_type' in df.columns:
        df['cex_interaction_type'] = df['cex_interaction_type'].astype('category')
    
    return df


def final_cleanup(df):
    """
    最终清理：确保所有数值特征都没有缺失值
    注意：分类特征的NaN保留，让GBDT处理；数值特征全部填充
    """
    print("\n" + "=" * 60)
    print("步骤6: 最终清理（数值特征填充，分类特征保留NaN）")
    print("=" * 60)
    
    # 处理所有数值列：填充缺失值
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in numeric_cols:
        if df[col].isnull().any():
            # 根据列名决定填充策略
            if any(keyword in col.lower() for keyword in ['hour', 'period', 'dst', 'time']):
                df[col] = df[col].fillna(-1)
            else:
                df[col] = df[col].fillna(0)
            print(f"  填充数值列 {col}")
    
    # 分类特征：确保是category类型，保留NaN
    object_cols = df.select_dtypes(include=['object']).columns.tolist()
    for col in object_cols:
        if col not in ['wallet', 'final_label']:
            # 将空字符串替换为NaN
            df[col] = df[col].replace('', np.nan)
            df[col] = df[col].astype('category')
    
    categorical_cols_final = df.select_dtypes(include=['category']).columns.tolist()
    print(f"  分类特征（保留NaN）: {len(categorical_cols_final)}个")
    
    return df


def main():
    """
    主函数：执行完整的特征筛选和处理流程
    """
    print("=" * 80)
    print("钱包区域预测模型 - 特征处理流水线")
    print("=" * 80)
    
    # 1. 加载数据并去重
    df = load_and_deduplicate_wallet('final_training_data.csv')
    
    # 2. 24小时分布 → 多项式系数
    df = polynomial_features_from_hours(df)
    
    # 3. 处理基础数值特征
    print("\n" + "=" * 60)
    print("步骤: 处理基础数值特征")
    print("=" * 60)
    
    # 金额特征（填充0）
    amount_features = ['avg_transaction_amount_eth', 'large_tx_ratio', 'micro_tx_ratio']
    df = process_numerical_features(df, amount_features, fill_value=0)
    
    # 时间比例特征（填充0）
    time_ratio_features = ['night_ratio', 'early_morning_ratio', 'daytime_ratio', 'weekend_ratio']
    df = process_numerical_features(df, time_ratio_features, fill_value=0)
    
    # 季节性特征（填充-1）
    seasonal_features = ['avg_tx_hour_period1', 'avg_tx_hour_period2', 
                         'avg_tx_hour_period3', 'avg_tx_hour_period4', 'tx_hour_variance']
    df = process_numerical_features(df, seasonal_features, fill_value=-1)
    
    # Gas特征（填充0）
    gas_features = ['avg_gas_price', 'avg_tx_fee_eth']
    df = process_numerical_features(df, gas_features, fill_value=0)
    
    # 活动特征（填充0）
    activity_features = ['wallet_age_days', 'active_days', 'avg_tx_per_day']
    df = process_numerical_features(df, activity_features, fill_value=0)
    
    # 协议特征（填充0）
    protocol_features = ['dex_count', 'lending_count', 'nft_count', 'bridge_count']
    df = process_numerical_features(df, protocol_features, fill_value=0)
    
    # 4. 处理Top Tokens
    df = process_top_tokens(df)
    
    # 5. 处理Top Namespaces
    df = process_top_namespaces(df)
    
    # 6. 处理CEX特征
    df = process_cex_features(df)
    
    # 7. 最终清理
    df = final_cleanup(df)
    
    # 8. 分离特征和标签
    print("\n" + "=" * 60)
    print("步骤7: 准备最终训练数据")
    print("=" * 60)
    
    # 保存wallet列
    wallet_col = df['wallet']
    
    # 分离标签和特征
    if 'final_label' in df.columns:
        y = df['final_label']
        X = df.drop(columns=['wallet', 'final_label'])
    else:
        print("警告: 未找到'final_label'列")
        y = None
        X = df.drop(columns=['wallet'])
    
    # 定义最终保留的特征顺序
    final_feature_order = [
        # 多项式系数
        'pct_poly_c0', 'pct_poly_c1', 'pct_poly_c2', 'pct_poly_c3',
        # 金额特征
        'avg_transaction_amount_eth', 'large_tx_ratio', 'micro_tx_ratio',
        # 时间比例
        'night_ratio', 'early_morning_ratio', 'daytime_ratio', 'weekend_ratio',
        # 季节性
        'avg_tx_hour_period1', 'avg_tx_hour_period2', 'avg_tx_hour_period3', 
        'avg_tx_hour_period4', 'tx_hour_variance',
        # Gas
        'avg_gas_price', 'avg_tx_fee_eth',
        # 活动
        'wallet_age_days', 'active_days', 'avg_tx_per_day',
        # 协议
        'dex_count', 'lending_count', 'nft_count', 'bridge_count',
        # Top1-5 tokens
        'top1_token', 'top1_token_count', 'top2_token', 'top2_token_count',
        'top3_token', 'top3_token_count', 'top4_token', 'top4_token_count',
        'top5_token', 'top5_token_count',
        # Top1-5 namespaces
        'top1_namespace', 'top1_namespace_count', 'top2_namespace', 'top2_namespace_count',
        'top3_namespace', 'top3_namespace_count', 'top4_namespace', 'top4_namespace_count',
        'top5_namespace', 'top5_namespace_count',
        # Top6-10聚合特征
        'top6_10_token_total_count', 'top6_10_token_diversity', 'top6_10_token_ratio',
        'top6_10_namespace_total_count', 'top6_10_namespace_diversity', 'top6_10_namespace_ratio',
        # CEX top1-3
        'top1_cex_region', 'top1_cex_count', 'top2_cex_region', 'top2_cex_count',
        'top3_cex_region', 'top3_cex_count', 'cex_interaction_type',
        # CEX聚合特征
        'top1_3_cex_total_count', 'top1_3_cex_region_diversity', 'has_multiple_cex_regions'
    ]
    
    # 只保留存在的特征
    existing_features = [col for col in final_feature_order if col in X.columns]
    X = X[existing_features]
    
    # 确保所有分类特征都是category类型
    for col in X.select_dtypes(include=['object']).columns:
        X[col] = X[col].astype('category')
    
    # 获取分类特征列表
    categorical_features = X.select_dtypes(include=['category']).columns.tolist()
    
    print(f"\n最终特征数量: {X.shape[1]}")
    print(f"分类特征数量: {len(categorical_features)}")
    print(f"分类特征列表: {categorical_features}")
    
    # 9. 保存处理后的数据
    output_path = 'cleaned_training_data.csv'
    final_df = pd.concat([wallet_col.reset_index(drop=True), 
                          X.reset_index(drop=True), 
                          y.reset_index(drop=True)] if y is not None else [wallet_col.reset_index(drop=True), X.reset_index(drop=True)], axis=1)
    final_df.to_csv(output_path, index=False)
    print(f"\n处理后的数据已保存至: {output_path}")
    
    # 10. 输出数据摘要
    print("\n" + "=" * 60)
    print("数据摘要")
    print("=" * 60)
    print(f"样本数量: {len(final_df)}")
    print(f"特征数量: {X.shape[1]}")
    print(f"\n标签分布:")
    if y is not None:
        print(y.value_counts())
    
    # 最终缺失值检查（数值特征应该没有缺失，分类特征可以有NaN）
    numeric_missing = X.select_dtypes(include=[np.number]).isnull().sum().sum()
    categorical_missing = X.select_dtypes(include=['category']).isnull().sum().sum()
    
    print(f"\n缺失值检查:")
    print(f"  数值特征缺失数量: {numeric_missing} (应为0)")
    print(f"  分类特征缺失数量: {categorical_missing} (GBDT会自动处理)")
    
    if numeric_missing > 0:
        print("  警告: 数值特征仍有缺失值!")
        cols_with_missing = X.select_dtypes(include=[np.number]).columns[X.select_dtypes(include=[np.number]).isnull().any()].tolist()
        print(f"  包含缺失值的数值列: {cols_with_missing}")
    else:
        print("  ✓ 所有数值特征缺失值已处理完毕!")
    
    return X, y, categorical_features


if __name__ == "__main__":
    X, y, categorical_features = main()
