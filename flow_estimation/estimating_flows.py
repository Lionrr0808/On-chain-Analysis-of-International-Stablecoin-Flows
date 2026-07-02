import pandas as pd
import numpy as np
from collections import defaultdict

def load_and_process_data(wallet_prob_file, transfer_file):
    """
    加载钱包概率数据和交易数据
    """
    print("正在加载数据...")
    
    # 读取钱包概率数据
    wallet_df = pd.read_csv(wallet_prob_file)
    print(f"加载了 {len(wallet_df)} 个钱包")
    
    # 读取交易数据
    transfer_df = pd.read_csv(transfer_file)
    print(f"加载了 {len(transfer_df)} 笔交易")
    
    # 打印列名以便调试
    print(f"\n交易数据列名: {transfer_df.columns.tolist()}")
    print(f"钱包数据列名: {wallet_df.columns.tolist()}")
    
    # 统一地址格式为小写
    wallet_df['wallet'] = wallet_df['wallet'].astype(str).str.lower().str.strip()
    transfer_df['from_address'] = transfer_df['from_address'].astype(str).str.lower().str.strip()
    transfer_df['to_address'] = transfer_df['to_address'].astype(str).str.lower().str.strip()
    
    return wallet_df, transfer_df

def create_wallet_probability_dict(wallet_df):
    """
    创建钱包地址到概率分布的映射
    """
    wallet_prob_dict = {}
    
    # 定义地区列
    region_columns = [
        'prob_Africa and Middle East',
        'prob_Asia and Pacific',
        'prob_Europe',
        'prob_Latin America and Caribbean',
        'prob_North America'
    ]
    
    for _, row in wallet_df.iterrows():
        wallet = row['wallet']
        # 提取该钱包的5个地区概率
        probs = row[region_columns].values
        
        # 确保概率归一化
        if probs.sum() > 0:
            probs = probs / probs.sum()
        
        wallet_prob_dict[wallet] = {
            'Africa and Middle East': probs[0],
            'Asia and Pacific': probs[1],
            'Europe': probs[2],
            'Latin America and Caribbean': probs[3],
            'North America': probs[4]
        }
    
    print(f"创建了 {len(wallet_prob_dict)} 个钱包的概率映射")
    return wallet_prob_dict, region_columns

def filter_transactions(transfer_df, wallet_prob_dict):
    """
    筛选from和to地址都在钱包列表中的交易
    """
    print("正在筛选交易...")
    
    # 获取所有钱包地址集合
    wallet_set = set(wallet_prob_dict.keys())
    
    # 显示一些地址示例用于调试
    print(f"\n钱包地址示例（前5个）: {list(wallet_set)[:5]}")
    print(f"交易中的from_address示例（前5个）: {transfer_df['from_address'].head(5).tolist()}")
    print(f"交易中的to_address示例（前5个）: {transfer_df['to_address'].head(5).tolist()}")
    
    # 检查地址匹配情况
    from_in_wallet = transfer_df['from_address'].isin(wallet_set).sum()
    to_in_wallet = transfer_df['to_address'].isin(wallet_set).sum()
    print(f"\n在钱包中的from_address数量: {from_in_wallet}/{len(transfer_df)}")
    print(f"在钱包中的to_address数量: {to_in_wallet}/{len(transfer_df)}")
    
    # 筛选条件：from地址和to地址都在钱包集合中
    filtered_df = transfer_df[
        transfer_df['from_address'].isin(wallet_set) & 
        transfer_df['to_address'].isin(wallet_set)
    ].copy()
    
    print(f"\n筛选出 {len(filtered_df)} 笔符合条件的交易")
    return filtered_df

def calculate_region_flows(filtered_df, wallet_prob_dict, region_names):
    """
    计算地区间的流量矩阵
    返回: flow_matrix[from_region][to_region] = 总流量
    """
    print("正在计算地区间流量...")
    
    # 初始化流量矩阵
    flow_matrix = defaultdict(lambda: defaultdict(float))
    
    # 用于统计总流入和总流出
    total_inflow = defaultdict(float)
    total_outflow = defaultdict(float)
    
    for idx, row in filtered_df.iterrows():
        from_wallet = row['from_address']
        to_wallet = row['to_address']
        token_amount = row['token_amount']
        
        # 检查token_amount是否为有效数值
        if pd.isna(token_amount) or token_amount == 0:
            continue
        
        # 获取from和to钱包的概率分布
        from_probs = wallet_prob_dict[from_wallet]
        to_probs = wallet_prob_dict[to_wallet]
        
        # 计算该笔交易在各个地区间的流量
        for i, from_region in enumerate(region_names):
            from_prob = from_probs[from_region]
            if from_prob == 0:
                continue
                
            for j, to_region in enumerate(region_names):
                to_prob = to_probs[to_region]
                if to_prob == 0:
                    continue
                
                flow_amount = token_amount * from_prob * to_prob
                
                # 累加到流量矩阵
                flow_matrix[from_region][to_region] += flow_amount
                
                # 累加总流出和总流入
                total_outflow[from_region] += flow_amount
                total_inflow[to_region] += flow_amount
        
        # 每处理10000笔交易显示进度
        if (idx + 1) % 10000 == 0:
            print(f"  已处理 {idx + 1:,} 笔交易...")
    
    return flow_matrix, total_inflow, total_outflow

def create_flow_dataframe(flow_matrix, region_names):
    """
    创建流量矩阵DataFrame
    """
    # 创建DataFrame
    df_flow = pd.DataFrame(index=region_names, columns=region_names)
    
    for from_region in region_names:
        for to_region in region_names:
            df_flow.loc[from_region, to_region] = flow_matrix[from_region].get(to_region, 0)
    
    # 添加总流出列
    df_flow['Total Outflow'] = df_flow.sum(axis=1)
    
    # 添加总流入行
    total_inflow = df_flow.sum(axis=0)
    df_flow.loc['Total Inflow'] = total_inflow
    
    return df_flow

def create_percentage_dataframe(df_flow, region_names):
    """
    创建百分比形式的流量矩阵
    """
    # 复制DataFrame
    df_pct = df_flow.copy()
    
    # 计算每个from地区流向各个to地区的百分比
    for from_region in region_names:
        total = df_flow.loc[from_region, region_names].sum()
        if total > 0:
            for to_region in region_names:
                df_pct.loc[from_region, to_region] = (df_flow.loc[from_region, to_region] / total) * 100
        else:
            for to_region in region_names:
                df_pct.loc[from_region, to_region] = 0
    
    # 计算总流出的百分比（基于总流出）
    total_outflow_sum = df_flow['Total Outflow'].sum()
    if total_outflow_sum > 0:
        for from_region in region_names:
            df_pct.loc[from_region, 'Total Outflow'] = (df_flow.loc[from_region, 'Total Outflow'] / total_outflow_sum) * 100
    else:
        for from_region in region_names:
            df_pct.loc[from_region, 'Total Outflow'] = 0
    
    # 计算总流入的百分比（基于总流入）
    total_inflow_sum = df_flow.loc['Total Inflow', region_names].sum()
    if total_inflow_sum > 0:
        for to_region in region_names:
            df_pct.loc['Total Inflow', to_region] = (df_flow.loc['Total Inflow', to_region] / total_inflow_sum) * 100
    else:
        for to_region in region_names:
            df_pct.loc['Total Inflow', to_region] = 0
    
    # 处理Total Inflow的总计
    df_pct.loc['Total Inflow', 'Total Outflow'] = 100.0
    
    return df_pct

def print_flow_results(df_flow, df_pct, region_names):
    """
    打印流量结果
    """
    print("\n" + "="*80)
    print("稳定币地区间流量分析结果")
    print("="*80)
    
    # 1. 打印流量矩阵（绝对值）
    print("\n📊 地区间流量矩阵（绝对值）:")
    print("-"*80)
    print("行: 来源地区 (From), 列: 目标地区 (To)")
    print("-"*80)
    
    # 格式化显示
    display_df = df_flow.copy()
    for col in display_df.columns:
        display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
    
    print(display_df)
    
    # 2. 打印流量矩阵（百分比）
    print("\n\n📊 地区间流量矩阵（百分比）:")
    print("-"*80)
    print("行: 来源地区 (From), 列: 目标地区 (To)")
    print("说明：每行表示从该地区流出的资金分配到各个目标地区的比例")
    print("-"*80)
    
    display_pct = df_pct.copy()
    for col in display_pct.columns:
        display_pct[col] = display_pct[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")
    
    print(display_pct)
    
    # 3. 打印汇总统计
    print("\n\n📈 汇总统计:")
    print("-"*80)
    print(f"{'地区':<30} {'总流出':>20} {'总流出%':>12} {'总流入':>20} {'总流入%':>12} {'净流入':>15}")
    print("-"*80)
    
    total_outflow_all = df_flow['Total Outflow'].sum()
    total_inflow_all = df_flow.loc['Total Inflow', region_names].sum()
    
    for region in region_names:
        outflow = df_flow.loc[region, 'Total Outflow']
        inflow = df_flow.loc['Total Inflow', region]
        net = inflow - outflow
        
        outflow_pct = (outflow / total_outflow_all * 100) if total_outflow_all > 0 else 0
        inflow_pct = (inflow / total_inflow_all * 100) if total_inflow_all > 0 else 0
        
        print(f"{region:<30} {outflow:>20,.2f} {outflow_pct:>11.2f}% {inflow:>20,.2f} {inflow_pct:>11.2f}% {net:>15,.2f}")
    
    print("-"*80)
    print(f"{'总计':<30} {total_outflow_all:>20,.2f} {'100.00%':>12} {total_inflow_all:>20,.2f} {'100.00%':>12} {total_inflow_all - total_outflow_all:>15,.2f}")
    print("="*80)
    
    # 4. 解释
    print("\n💡 说明：")
    print("- 总流出%: 该地区流出占所有地区总流出的比例")
    print("- 总流入%: 该地区流入占所有地区总流入的比例")
    print("- 净流入: 正值表示净流入，负值表示净流出")

def save_results(df_flow, df_pct, region_names):
    """
    保存结果到CSV文件
    """
    # 保存绝对值矩阵
    df_flow.to_csv('flow_matrix_absolute.csv')
    print(f"\n✅ 流量矩阵（绝对值）已保存到 flow_matrix_absolute.csv")
    
    # 保存百分比矩阵
    df_pct.to_csv('flow_matrix_percentage.csv')
    print(f"✅ 流量矩阵（百分比）已保存到 flow_matrix_percentage.csv")
    
    # 创建汇总表
    summary_data = []
    total_outflow_all = df_flow['Total Outflow'].sum()
    total_inflow_all = df_flow.loc['Total Inflow', region_names].sum()
    
    for region in region_names:
        outflow = df_flow.loc[region, 'Total Outflow']
        inflow = df_flow.loc['Total Inflow', region]
        net = inflow - outflow
        
        outflow_pct = (outflow / total_outflow_all * 100) if total_outflow_all > 0 else 0
        inflow_pct = (inflow / total_inflow_all * 100) if total_inflow_all > 0 else 0
        
        summary_data.append({
            'Region': region,
            'Total Outflow': outflow,
            'Outflow %': outflow_pct,
            'Total Inflow': inflow,
            'Inflow %': inflow_pct,
            'Net Flow': net
        })
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_csv('flow_summary.csv', index=False)
    print(f"✅ 汇总统计已保存到 flow_summary.csv")

def main():
    """
    主函数
    """
    # 文件路径
    wallet_prob_file = 'predictions_with_probabilities.csv'
    transfer_file = 'transfer_data.csv'
    
    try:
        # 1. 加载数据并统一地址格式
        wallet_df, transfer_df = load_and_process_data(wallet_prob_file, transfer_file)
        
        # 2. 创建钱包概率字典
        wallet_prob_dict, region_columns = create_wallet_probability_dict(wallet_df)
        
        # 3. 筛选交易
        filtered_df = filter_transactions(transfer_df, wallet_prob_dict)
        
        if len(filtered_df) == 0:
            print("\n⚠️ 警告：没有找到符合条件的交易！")
            return
        
        # 4. 定义地区名称
        region_names = [
            'Africa and Middle East',
            'Asia and Pacific',
            'Europe',
            'Latin America and Caribbean',
            'North America'
        ]
        
        # 5. 计算地区间流量
        flow_matrix, total_inflow, total_outflow = calculate_region_flows(
            filtered_df, wallet_prob_dict, region_names
        )
        
        # 6. 创建DataFrame
        df_flow = create_flow_dataframe(flow_matrix, region_names)
        df_pct = create_percentage_dataframe(df_flow, region_names)
        
        # 7. 打印结果
        print_flow_results(df_flow, df_pct, region_names)
        
        # 8. 保存结果
        save_results(df_flow, df_pct, region_names)
        
        # 9. 保存筛选后的交易数据
        filtered_df.to_csv('filtered_transactions.csv', index=False)
        print(f"✅ 筛选后的交易数据已保存到 filtered_transactions.csv")
        
        # 10. 输出统计信息
        print(f"\n📊 数据统计：")
        print(f"- 总交易笔数: {len(transfer_df):,}")
        print(f"- 符合条件的交易笔数: {len(filtered_df):,}")
        print(f"- 匹配率: {len(filtered_df)/len(transfer_df)*100:.2f}%")
        print(f"- 参与交易的钱包数量: {len(set(filtered_df['from_address']) | set(filtered_df['to_address'])):,}")
        
        if len(filtered_df) > 0:
            print(f"\n💰 Token Amount 统计：")
            print(f"- 总交易金额: {filtered_df['token_amount'].sum():,.2f}")
            print(f"- 平均交易金额: {filtered_df['token_amount'].mean():,.2f}")
            print(f"- 最大交易金额: {filtered_df['token_amount'].max():,.2f}")
            print(f"- 最小交易金额: {filtered_df['token_amount'].min():,.2f}")
        
    except FileNotFoundError as e:
        print(f"错误：找不到文件 - {e}")
    except KeyError as e:
        print(f"错误：列名不存在 - {e}")
        print("\n请检查CSV文件的列名是否匹配：")
        print("期望的列名：'wallet', 'from_address', 'to_address', 'token_amount'")
        print("以及概率列：'prob_Africa and Middle East', 'prob_Asia and Pacific', 'prob_Europe', 'prob_Latin America and Caribbean', 'prob_North America'")
    except Exception as e:
        print(f"发生错误：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()