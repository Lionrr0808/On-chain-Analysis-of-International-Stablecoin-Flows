import csv
from dune_client.client import DuneClient

# 初始化 Dune API
DUNE_API_KEY = "okXp1OEjB1Nei7dayJVh5zXCDyAHzNuH"  # 在 Dune Settings → API 中获取
dune = DuneClient(DUNE_API_KEY)

# 你的查询 ID（在 Dune 查询页面 URL 中找到，例如：https://dune.com/queries/1234567）
QUERY_ID = 7627505  # 替换为你的实际查询ID

def export_query_result_to_csv(query_id, output_file):
    """
    导出 Dune 查询结果到 CSV 文件
    """
    print(f"正在获取查询 {query_id} 的结果...")
    
    # 获取最新执行的查询结果
    try:
        # 方式1: 获取最新结果（不重新运行，不扣积分）
        result = dune.get_latest_result(query_id)
        print("✓ 成功获取查询结果")
    except Exception as e:
        print(f"获取最新结果失败，尝试重新执行查询...")
        # 方式2: 重新运行查询（会消耗积分）
        result = dune.run_query(query_id=query_id)
        print("✓ 查询执行完成")
    
    # 提取数据行
    rows = result.result.rows if hasattr(result.result, 'rows') else result.rows
    
    if not rows:
        print("查询结果为空！")
        return
    
    # 获取列名
    columns = list(rows[0].keys())
    
    # 写入 CSV 文件
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ 成功导出 {len(rows)} 行数据到 {output_file}")

# 执行导出
export_query_result_to_csv(QUERY_ID, "ens_results.csv")
