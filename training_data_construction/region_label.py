import asyncio
import aiohttp
import pandas as pd
import json
import os
import time
import re
from datetime import datetime
from collections import Counter

# ========== 配置部分 ==========
API_KEY = ""  # 替换成你的
API_URL = "https://api.deepseek.com/v1/chat/completions"
INPUT_CSV = "filtered_addresses_with_domains.csv"
OUTPUT_CSV = "classified_domains.csv"

# 速度配置
MAX_CONCURRENT = 300
TIMEOUT = 90
BATCH_SIZE = 5000
SAVE_INTERVAL = 10000
VALIDATION_INTERVAL = 5000  # 每5000个输出一次验证

# 文件
PROGRESS_FILE = "progress.json"
CACHE_FILE = "domain_label_cache.json"

# Token统计
token_stats = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "cache_hit_tokens": 0,
    "cache_miss_tokens": 0,
    "total_requests": 0,
}

REGION_MAPPING = {
    0: "Unclassified",
    1: "Latin America and Caribbean",
    2: "North America",
    3: "Africa and Middle East",
    4: "Europe",
    5: "Asia and Pacific"
}

# ========== 提示词 ==========
SYSTEM_PROMPT = """You are trained to classify ENS domain names into regions. Output ONLY a single digit 0-5."""

USER_PROMPT_TEMPLATE = """You are trained to classify ENS domain names into the following regions: 
{{"Latin America and Caribbean"(1),"North America"(2),"Africa and Middle East"(3),"Europe"(4),"Asia and Pacific"(5),"Unclassified"(0)}}.
Use the number after each region as the output.

Consider references to:
- Language (e.g., Chinese pinyin, Spanish, French, English)
- Cultures (e.g., music, sports, memes)
- Localities (city names, landmarks)
- Memes and internet culture

Be creative and mindful of:
- Language commonly used in crypto and Web3
- Languages spoken in multiple regions (e.g., English, French, Spanish)

If you cannot classify into any of the 5 regions, classify it as "Unclassified" (0).

Domain: {domain}

Output ONLY the number (0-5):"""

# ========== 进度和缓存管理 ==========
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"processed_indices": [], "last_index": -1, "total": 0}

def save_progress(processed_indices, last_index, total, reason=None):
    progress = {
        "processed_indices": list(processed_indices),
        "last_index": last_index,
        "total": total,
        "last_update": datetime.now().isoformat(),
        "reason": reason
    }
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

domain_cache = load_cache()

# ========== 分类函数 ==========
async def classify_domain(session, domain: str, semaphore, idx: int, balance_event=None) -> tuple:
    global token_stats
    
    if not domain or pd.isna(domain):
        return domain, "0"
    
    if domain in domain_cache:
        return domain, domain_cache[domain]
    
    async with semaphore:
        user_content = USER_PROMPT_TEMPLATE.format(domain=domain)
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-v4-flash",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.4,
            "top_p": 0.4,
            "max_tokens": 150  # 保持150，没改
        }
        
        try:
            async with session.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT) as response:
                if response.status == 402:
                    if balance_event:
                        balance_event.set()
                    return domain, "0"
                
                if response.status == 200:
                    resp_json = await response.json()
                    full_content = resp_json['choices'][0]['message']['content'].strip()
                    
                    usage = resp_json.get('usage', {})
                    token_stats["prompt_tokens"] += usage.get('prompt_tokens', 0)
                    token_stats["completion_tokens"] += usage.get('completion_tokens', 0)
                    token_stats["cache_hit_tokens"] += usage.get('prompt_cache_hit_tokens', 0)
                    token_stats["cache_miss_tokens"] += usage.get('prompt_cache_miss_tokens', 0)
                    token_stats["total_requests"] += 1
                    
                    numbers = re.findall(r'\d', full_content)
                    if numbers:
                        label = numbers[0]
                    else:
                        text_to_num = {
                            'unclassified': '0', 'latin': '1', 'caribbean': '1',
                            'north': '2', 'africa': '3', 'middle east': '3',
                            'europe': '4', 'asia': '5', 'pacific': '5'
                        }
                        lower = full_content.lower()
                        label = '0'
                        for word, num in text_to_num.items():
                            if word in lower:
                                label = num
                                break
                    
                    if label not in ['0', '1', '2', '3', '4', '5']:
                        label = "0"
                    
                    domain_cache[domain] = label
                    return domain, label
                else:
                    return domain, "0"
        except asyncio.TimeoutError:
            return domain, "0"
        except Exception:
            return domain, "0"

# ========== 批量处理 ==========
async def process_batch(session, batch_items, semaphore, balance_event):
    tasks = [classify_domain(session, domain, semaphore, idx, balance_event) for idx, domain in batch_items]
    results = await asyncio.gather(*tasks)
    return dict(results)

# ========== 成本计算 ==========
def calculate_cost():
    INPUT_CACHE_HIT_PRICE = 0.02 / 1_000_000
    INPUT_CACHE_MISS_PRICE = 1 / 1_000_000
    OUTPUT_PRICE = 2 / 1_000_000
    
    return {
        "input_hit": token_stats["cache_hit_tokens"] * INPUT_CACHE_HIT_PRICE,
        "input_miss": token_stats["cache_miss_tokens"] * INPUT_CACHE_MISS_PRICE,
        "output": token_stats["completion_tokens"] * OUTPUT_PRICE,
        "total": (token_stats["cache_hit_tokens"] * INPUT_CACHE_HIT_PRICE + 
                  token_stats["cache_miss_tokens"] * INPUT_CACHE_MISS_PRICE + 
                  token_stats["completion_tokens"] * OUTPUT_PRICE)
    }

# ========== 验证函数 ==========
def print_validation(df, processed_count):
    df_processed = df.iloc[:processed_count]
    non_zero = df_processed[
        (df_processed['domain_name_label'].astype(str) != '0') & 
        (df_processed['domain_name_label'].astype(str) != '') &
        (df_processed['domain_name_label'].notna())
    ]
    
    if len(non_zero) == 0:
        return
    
    print("\n" + "="*70)
    print(f"📊 验证点 - 已处理 {processed_count} 个")
    print("="*70)
    for _, row in non_zero.tail(10).iterrows():
        label = row['domain_name_label']
        try:
            label_int = int(float(label)) if label else 0
            region = REGION_MAPPING.get(label_int, "Unknown")
        except (ValueError, TypeError):
            region = "Unknown"
        name = str(row['name'])[:45]
        print(f"   {name:45} -> {label} ({region})")
    
    counts = {}
    for label in df_processed['domain_name_label']:
        if label and label != '':
            try:
                label_int = int(float(label))
                counts[label_int] = counts.get(label_int, 0) + 1
            except (ValueError, TypeError):
                pass
    
    if counts:
        print("\n分布:")
        for label, count in sorted(counts.items()):
            region = REGION_MAPPING.get(label, "Unknown")
            print(f"   {label}({region}): {count}")
    print("="*70)

# ========== 主函数 ==========
async def main():
    print("="*60)
    print("域名分类任务 - 优化版（max_tokens=150）")
    print(f"输入: {INPUT_CSV}")
    print(f"并发: {MAX_CONCURRENT}")
    print("="*60)
    
    # 读取CSV
    print("\n1. 读取文件...")
    df = pd.read_csv(INPUT_CSV, encoding='utf-8')
    print(f"   共 {len(df)} 行")
    
    if 'name' not in df.columns:
        print("错误: 没有找到'name'列")
        return
    
    if 'domain_name_label' not in df.columns:
        df['domain_name_label'] = ""
    
    # 加载进度
    print("\n2. 加载进度...")
    progress = load_progress()
    processed_indices = set(progress.get("processed_indices", []))
    
    # 从缓存恢复
    for idx, name in enumerate(df['name']):
        if str(name) in domain_cache:
            df.at[idx, 'domain_name_label'] = domain_cache[str(name)]
            processed_indices.add(idx)
    
    # 未处理的行
    unprocessed = [i for i in range(len(df)) if i not in processed_indices]
    
    print(f"   总数据: {len(df)}")
    print(f"   已处理: {len(processed_indices)}")
    print(f"   待处理: {len(unprocessed)}")
    
    if len(unprocessed) == 0:
        print("\n✅ 已完成！")
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        return
    
    # 继续确认
    if len(processed_indices) > 0:
        res = input(f"\n从第 {len(processed_indices)+1} 行继续？(y/n): ")
        if res.lower() != 'y':
            unprocessed = list(range(len(df)))
            processed_indices = set()
            df['domain_name_label'] = ""
    
    # 准备数据
    items = [(idx, str(df.iloc[idx]['name'])) for idx in unprocessed]
    total = len(items)
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n3. 开始分类...")
    print(f"   待处理: {total} 个")
    print(f"   批次: {num_batches}")
    print("="*60)
    
    start_time = time.time()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    balance_event = asyncio.Event()
    
    processed_count = len(processed_indices)
    last_milestone = 0
    
    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT,
        limit_per_host=MAX_CONCURRENT,
        ttl_dns_cache=600,
        keepalive_timeout=30
    )
    async with aiohttp.ClientSession(connector=connector) as session:
        for batch_num in range(num_batches):
            if balance_event.is_set():
                print("\n⚠️ 余额不足，已暂停")
                save_progress(processed_indices, -1, len(df), "insufficient_balance")
                return
            
            batch_start = batch_num * BATCH_SIZE
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch_items = items[batch_start:batch_end]
            
            # 简洁的进度提示
            print(f"\n   🔄 批次 {batch_num+1}/{num_batches} ({len(batch_items)}个)...", end="", flush=True)
            
            batch_time = time.time()
            results = await process_batch(session, batch_items, semaphore, balance_event)
            batch_time = time.time() - batch_time
            
            # 更新结果
            batch_indices = []
            batch_labels = []
            for idx, domain in batch_items:
                if domain in results:
                    batch_indices.append(idx)
                    batch_labels.append(results[domain])

            if batch_indices:
                df.loc[batch_indices, 'domain_name_label'] = batch_labels
            
            for idx, _ in batch_items:
                processed_indices.add(idx)
            processed_count += len(batch_items)
            
            # 每5批保存一次进度和缓存
            if batch_num % 5 == 0 or batch_num == num_batches - 1:
                save_progress(list(processed_indices), batch_items[-1][0] if batch_items else -1, len(df))
                save_cache(domain_cache)
            
            # 计算速度
            batch_speed = len(batch_items) / batch_time
            elapsed_total = time.time() - start_time
            avg_speed = processed_count / elapsed_total if elapsed_total > 0 else 0
            remaining_seconds = (total - processed_count + len(processed_indices)) / avg_speed if avg_speed > 0 else 0
            
            # 一行显示所有信息
            print(f" 完成 {batch_speed:.1f}个/秒 | 平均 {avg_speed:.1f}个/秒 | 进度 {processed_count}/{len(df)} ({processed_count/len(df)*100:.1f}%) | 剩余 {remaining_seconds/3600:.1f}小时")
            
            # 验证点
            milestone = (processed_count // VALIDATION_INTERVAL) * VALIDATION_INTERVAL
            if milestone > last_milestone and milestone > 0:
                print_validation(df, processed_count)
                last_milestone = milestone
            
            # 每10批强制保存一次
            if batch_num % 10 == 0 or batch_num == num_batches - 1:
                df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
                print(f"   💾 已保存结果（批次 {batch_num}）")
    
    # 最终保存
    print("\n4. 保存最终结果...")
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    # 统计
    cost = calculate_cost()
    elapsed = time.time() - start_time
    
    print("\n" + "="*60)
    print("📊 最终统计")
    print("="*60)
    
    valid_labels = []
    for label in df['domain_name_label']:
        if label and label != '':
            try:
                valid_labels.append(int(float(label)))
            except (ValueError, TypeError):
                pass
    
    counts = Counter(valid_labels)
    for label, count in sorted(counts.items()):
        region = REGION_MAPPING.get(label, "Unknown")
        print(f"   类别 {label} ({region}): {count}")
    
    print(f"\n⏱️  耗时: {elapsed/60:.1f}分钟")
    print(f"⚡ 平均速度: {len(df)/elapsed:.1f}个/秒")
    
    print("\n💰 成本:")
    print(f"   输入缓存命中: {token_stats['cache_hit_tokens']:,} tokens → ¥{cost['input_hit']:.4f}")
    print(f"   输入缓存未命中: {token_stats['cache_miss_tokens']:,} tokens → ¥{cost['input_miss']:.4f}")
    print(f"   输出: {token_stats['completion_tokens']:,} tokens → ¥{cost['output']:.4f}")
    print(f"   总计: ¥{cost['total']:.4f}")
    
    # 清理
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    
    print(f"\n✅ 完成！结果: {OUTPUT_CSV}")

if __name__ == "__main__":
    asyncio.run(main())
