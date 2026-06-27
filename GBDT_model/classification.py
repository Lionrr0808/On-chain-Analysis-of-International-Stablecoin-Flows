# predict_with_encoding.py

import pandas as pd
import numpy as np
import joblib
import time
import sys
from GBDT_model import HierarchicalGBDTClassifier, load_model

def print_progress(message, level="INFO"):
    """打印进度信息"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()


def print_region_stats(data, title="Region Distribution", show_bar=True):
    """
    打印5类区域的统计信息
    """
    all_regions = [
        'Africa and Middle East',
        'Asia and Pacific',
        'Europe',
        'Latin America and Caribbean',
        'North America'
    ]
    
    print("\n" + "="*70)
    print(f"📊 {title}")
    print("="*70)
    
    total = len(data)
    print(f"\n  Total samples: {total:,}")
    
    region_counts = {}
    for region in all_regions:
        count = (data == region).sum()
        region_counts[region] = count
    
    print(f"\n  {'Region':<32} {'Count':<12} {'Percentage':<10}")
    print(f"  {'-'*65}")
    
    for region in all_regions:
        count = region_counts[region]
        pct = count / total * 100 if total > 0 else 0
        bar = '█' * int(pct / 2) if show_bar and pct > 0 else ''
        print(f"  {region:<32} {count:>10,}   {pct:>6.1f}%    {bar}")
    
    other_count = total - sum(region_counts.values())
    if other_count > 0:
        pct = other_count / total * 100
        print(f"  {'Other':<32} {other_count:>10,}   {pct:>6.1f}%")
    
    print(f"  {'-'*65}")
    print(f"  {'TOTAL':<32} {total:>10,}   {'100.0%':>6}")
    
    print(f"\n  📈 Summary Statistics:")
    max_region = max(region_counts, key=region_counts.get)
    max_count = region_counts[max_region]
    min_region = min(region_counts, key=region_counts.get)
    min_count = region_counts[min_region]
    print(f"    Most common: {max_region} ({max_count:,}, {max_count/total*100:.1f}%)")
    print(f"    Least common: {min_region} ({min_count:,}, {min_count/total*100:.1f}%)")
    print(f"    Range: {max_count - min_count:,} ({((max_count-min_count)/total*100):.1f}%)")
    
    p_squared = sum([(count/total)**2 for count in region_counts.values()])
    diversity = 1 - p_squared
    print(f"    Diversity Index (Simpson): {diversity:.4f} (0=no diversity, 1=max diversity)")
    
    return region_counts


def print_probability_stats(probs_df, region_names, title="Probability Aggregation"):
    """
    打印概率累加统计
    """
    print("\n" + "="*70)
    print(f"📊 {title}")
    print("="*70)
    
    total = len(probs_df)
    print(f"\n  Total samples: {total:,}")
    print(f"\n  {'Region':<32} {'Sum Prob':<14} {'Percentage':<10}")
    print(f"  {'-'*65}")
    
    prob_sum_total = 0
    for region in region_names:
        prob_sum = probs_df[region].sum()
        prob_sum_total += prob_sum
        pct = prob_sum / total * 100
        bar = '█' * int(pct / 2) if pct > 0 else ''
        print(f"  {region:<32} {prob_sum:>10.1f}    {pct:>6.1f}%    {bar}")
    
    print(f"  {'-'*65}")
    print(f"  {'TOTAL':<32} {prob_sum_total:>10.1f}    {'100.0%':>6}")
    
    print(f"\n  📈 Summary Statistics:")
    max_region = max(region_names, key=lambda r: probs_df[r].sum())
    max_sum = probs_df[max_region].sum()
    min_region = min(region_names, key=lambda r: probs_df[r].sum())
    min_sum = probs_df[min_region].sum()
    print(f"    Most common: {max_region} ({max_sum:.1f}, {max_sum/total*100:.1f}%)")
    print(f"    Least common: {min_region} ({min_sum:.1f}, {min_sum/total*100:.1f}%)")
    
    return {region: probs_df[region].sum() for region in region_names}


def print_batch_stats(batch_num, processed, total, batch_predictions, batch_probs, region_names):
    """
    每10000个样本打印一次统计
    """
    print(f"\n  📊 Batch {batch_num} Stats (processed: {processed:,}/{total:,}):")
    print(f"     Hard classification distribution:")
    pred_counts = pd.Series(batch_predictions).value_counts()
    for region, count in pred_counts.items():
        pct = count / len(batch_predictions) * 100
        print(f"       {region}: {count:,} ({pct:.1f}%)")
    
    print(f"     Probability aggregation distribution:")
    prob_sum = batch_probs.sum(axis=0)
    for idx, region in enumerate(region_names):
        pct = prob_sum[idx] / len(batch_probs) * 100
        print(f"       {region}: {prob_sum[idx]:.1f} ({pct:.1f}%)")


def main():
    """
    主函数：预测 classification_data_final_cleaned.csv 中钱包的区域标签
    """
    print("="*80)
    print("🚀 Wallet Region Prediction with Probability Aggregation")
    print("="*80)
    
    # ========== 1. 加载模型 ==========
    print_progress("Loading model and components...")
    
    try:
        model, feature_names = load_model('GBDT_model_simplified')
    except FileNotFoundError:
        print_progress("❌ Model files not found! Please train the model first.", level="ERROR")
        print_progress("   Expected files: GBDT_model_simplified.joblib", level="ERROR")
        return
    except Exception as e:
        print_progress(f"❌ Error loading model: {e}", level="ERROR")
        return
    
    print(f"✅ Model loaded successfully!")
    print(f"   Total features: {len(feature_names)}")
    print(f"   Categorical features: {len(model.categorical_feature_names) if hasattr(model, 'categorical_feature_names') else 0}")
    
    # ========== 2. 加载数据 ==========
    print_progress("Loading data...")
    
    data_file = 'classification_data_final_cleaned.csv'
    
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16']
    data_loaded = False
    
    for encoding in encodings:
        try:
            new_data = pd.read_csv(data_file, encoding=encoding)
            print(f"✅ Data loaded successfully with encoding: {encoding}")
            data_loaded = True
            break
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            print(f"❌ Error: File '{data_file}' not found!")
            return
        except Exception as e:
            print(f"⚠️  Error with encoding {encoding}: {e}")
            continue
    
    if not data_loaded:
        print_progress("❌ Could not load data with any encoding", level="ERROR")
        return
    
    print(f"   Total samples: {len(new_data):,}")
    print(f"   Total columns: {len(new_data.columns)}")
    
    # ========== 3. 检查必要的列 ==========
    required_cols = ['cex_interaction_type', 'top1_cex_region']
    missing_cols = [col for col in required_cols if col not in new_data.columns]
    if missing_cols:
        print(f"❌ Error: Missing columns: {missing_cols}")
        print(f"   Available columns: {new_data.columns.tolist()[:10]}...")
        return
    
    # ========== 4. 分离数据 ==========
    mask_cex_address = new_data['cex_interaction_type'] == 'cex_address'
    mask_predict = ~mask_cex_address
    
    print(f"\n📊 Data Split:")
    print(f"  Direct assignment (cex_address): {mask_cex_address.sum():,} ({mask_cex_address.sum()/len(new_data)*100:.1f}%)")
    print(f"  Model prediction (non-cex_address): {mask_predict.sum():,} ({mask_predict.sum()/len(new_data)*100:.1f}%)")
    
    # ========== 5. 初始化预测结果列 ==========
    new_data['predicted_region'] = None
    new_data['prediction_type'] = None
    region_names = ['Africa and Middle East', 'Asia and Pacific', 'Europe', 
                    'Latin America and Caribbean', 'North America']
    
    # 初始化概率列
    for region in region_names:
        new_data[f'prob_{region}'] = None
    
    # ========== 6. 处理 cex_address 的样本（直接赋值） ==========
    if mask_cex_address.sum() > 0:
        print_progress("Assigning direct labels for cex_address samples...")
        new_data.loc[mask_cex_address, 'predicted_region'] = new_data.loc[mask_cex_address, 'top1_cex_region']
        new_data.loc[mask_cex_address, 'prediction_type'] = 'direct_assignment'
        
        # 🔧 直接赋值样本的概率：对应区域为1，其他为0
        for region in region_names:
            new_data.loc[mask_cex_address, f'prob_{region}'] = 0.0
        # 根据 top1_cex_region 设置概率为1
        for idx in new_data[mask_cex_address].index:
            region = new_data.loc[idx, 'top1_cex_region']
            if region in region_names:
                new_data.loc[idx, f'prob_{region}'] = 1.0
        
        direct_counts = new_data.loc[mask_cex_address, 'predicted_region'].value_counts()
        print(f"\n  Direct assignment distribution ({mask_cex_address.sum():,} samples):")
        for region, count in direct_counts.items():
            pct = count / mask_cex_address.sum() * 100
            print(f"    {region}: {count:,} ({pct:.1f}%)")
    
    # ========== 7. 预测非 cex_address 的样本 ==========
    if mask_predict.sum() > 0:
        print_progress(f"Predicting with model for {mask_predict.sum():,} samples...")
        print(f"   Progress will be reported every 10,000 samples")
        print(f"   {'='*55}")
        
        # 准备特征数据
        X_predict = new_data.loc[mask_predict, feature_names].copy()
        
        # 检查缺失特征
        missing_features = set(feature_names) - set(X_predict.columns)
        if missing_features:
            print(f"  ⚠️  Warning: Missing {len(missing_features)} features")
            for col in missing_features:
                X_predict[col] = np.nan
                print(f"    → Added missing feature: {col}")
        
        # 按特征顺序排列
        X_predict = X_predict[feature_names]
        
        # 获取索引
        predict_indices = new_data.index[mask_predict].tolist()
        total_predict = len(predict_indices)
        
        # 分批预测（每批10000个）
        batch_size = 10000
        start_time = time.time()
        all_predictions = []
        all_probs = []
        
        print(f"\n  Starting prediction at {time.strftime('%H:%M:%S')}")
        
        batch_num = 0
        for i in range(0, total_predict, batch_size):
            batch_num += 1
            batch_indices = predict_indices[i:i+batch_size]
            batch_start = time.time()
            
            # 获取当前批次
            batch_data = X_predict.loc[batch_indices]
            
            # 🔧 获取概率
            batch_probs = model.predict_proba(batch_data)
            all_probs.extend(batch_probs)
            
            # 获取硬分类（用于对比）
            batch_predictions = model.predict(batch_data)
            all_predictions.extend(batch_predictions)
            
            # 计算进度
            processed = min(i + batch_size, total_predict)
            progress_pct = processed / total_predict * 100
            batch_time = time.time() - batch_start
            elapsed_time = time.time() - start_time
            
            # 预估剩余时间
            if i > 0:
                avg_time_per_batch = elapsed_time / batch_num
                remaining_batches = (total_predict - processed) / batch_size
                eta = remaining_batches * avg_time_per_batch
                eta_str = f"{eta:.1f}s" if eta < 60 else f"{eta/60:.1f}min"
            else:
                eta_str = "calculating..."
            
            # 🔧 每10000个或最后一批输出进度 + 统计
            if processed % 10000 == 0 or processed == total_predict:
                print(f"\n  📊 Progress: {processed:,}/{total_predict:,} ({progress_pct:.1f}%) | "
                      f"Batch: {batch_time:.2f}s | "
                      f"Elapsed: {elapsed_time:.1f}s | "
                      f"ETA: {eta_str}")
                
                # 🔧 打印当前批次的统计
                print_batch_stats(batch_num, processed, total_predict, 
                                 batch_predictions, batch_probs, region_names)
        
        # 保存预测结果
        new_data.loc[mask_predict, 'predicted_region'] = all_predictions
        new_data.loc[mask_predict, 'prediction_type'] = 'model_predicted'
        
        # 保存概率
        for idx, region in enumerate(region_names):
            new_data.loc[mask_predict, f'prob_{region}'] = [p[idx] for p in all_probs]
        
        total_time = time.time() - start_time
        print(f"\n  ✅ Prediction completed at {time.strftime('%H:%M:%S')}")
        print(f"  Total time: {total_time:.2f}s ({total_time/60:.2f}min)")
        print(f"  Average speed: {total_predict/total_time:.1f} samples/second")
    
    # ========== 8. 检查未赋值情况 ==========
    na_count = new_data['predicted_region'].isna().sum()
    if na_count > 0:
        print(f"\n⚠️  Warning: {na_count:,} samples have no prediction! Filling with 'Unknown'")
        new_data.loc[new_data['predicted_region'].isna(), 'predicted_region'] = 'Unknown'
        new_data.loc[new_data['predicted_region'].isna(), 'prediction_type'] = 'unknown'
        for region in region_names:
            new_data.loc[new_data['predicted_region'].isna(), f'prob_{region}'] = 0.0
    
    # ========== 9. 统计5类标签（硬分类） ==========
    print_region_stats(new_data['predicted_region'], "Overall Region Distribution - Hard Classification")
    
    # ========== 10. 统计概率累加 ==========
    # 创建概率DataFrame
    prob_df = new_data[['prob_' + r for r in region_names]]
    prob_df.columns = region_names
    print_probability_stats(prob_df, region_names, "Regional Distribution - Probability Aggregation")
    
    # ========== 11. 分别统计两种方式 ==========
    if mask_cex_address.sum() > 0:
        print_region_stats(
            new_data.loc[mask_cex_address, 'predicted_region'],
            "Direct Assignment Distribution (cex_address samples)"
        )
        
        # 概率统计 - 直接赋值
        prob_direct = new_data.loc[mask_cex_address, ['prob_' + r for r in region_names]]
        prob_direct.columns = region_names
        print_probability_stats(prob_direct, region_names, "Probability Aggregation (cex_address samples)")
    
    if mask_predict.sum() > 0:
        print_region_stats(
            new_data.loc[mask_predict, 'predicted_region'],
            "Model Prediction Distribution (non-cex_address samples)"
        )
        
        # 概率统计 - 模型预测
        prob_model = new_data.loc[mask_predict, ['prob_' + r for r in region_names]]
        prob_model.columns = region_names
        print_probability_stats(prob_model, region_names, "Probability Aggregation (non-cex_address samples)")
    
    # ========== 12. 按 cex_interaction_type 分类统计 ==========
    print("\n" + "="*70)
    print("📊 Distribution by CEX Interaction Type")
    print("="*70)
    
    cex_types = new_data['cex_interaction_type'].value_counts()
    print(f"\n  CEX Interaction Type Distribution:")
    for cex_type, count in cex_types.items():
        pct = count / len(new_data) * 100
        print(f"    {cex_type}: {count:,} ({pct:.1f}%)")
    
    print(f"\n  Region Distribution by CEX Interaction Type:")
    print(f"  {'CEX Type':<25} {'Region':<32} {'Count':<10} {'%':<8}")
    print(f"  {'-'*80}")
    
    for cex_type in new_data['cex_interaction_type'].unique():
        subset = new_data[new_data['cex_interaction_type'] == cex_type]
        total_subset = len(subset)
        region_counts = subset['predicted_region'].value_counts()
        
        for idx, (region, count) in enumerate(region_counts.items()):
            if idx < 3:
                pct = count / total_subset * 100
                print(f"  {cex_type:<25} {region:<32} {count:>8,}   {pct:>5.1f}%")
        
        if len(region_counts) > 3:
            other_count = total_subset - region_counts.head(3).sum()
            print(f"  {cex_type:<25} {'Other':<32} {other_count:>8,}   {other_count/total_subset*100:>5.1f}%")
        
        print(f"  {'-'*80}")
    
    # ========== 13. 保存结果 ==========
    print("\n" + "="*70)
    print("📁 Saving Results")
    print("="*70)
    
    output_file = 'predictions_with_probabilities.csv'
    new_data.to_csv(output_file, index=False)
    print(f"  ✅ Saved: {output_file}")
    
    # 保存统计摘要
    all_regions = region_names
    
    summary_stats = []
    total = len(new_data)
    for region in all_regions:
        count = (new_data['predicted_region'] == region).sum()
        prob_sum = new_data[f'prob_{region}'].sum()
        pct_count = count / total * 100
        pct_prob = prob_sum / total * 100
        summary_stats.append({
            'Region': region,
            'Hard_Count': count,
            'Hard_Percentage': pct_count,
            'Prob_Sum': prob_sum,
            'Prob_Percentage': pct_prob
        })
    summary_df = pd.DataFrame(summary_stats)
    summary_df.to_csv('region_distribution_summary_with_probs.csv', index=False)
    print("  ✅ Saved: region_distribution_summary_with_probs.csv")
    
    # ========== 14. 显示示例 ==========
    print("\n📋 Sample predictions (first 20 rows):")
    sample_cols = ['wallet', 'cex_interaction_type', 'top1_cex_region', 'predicted_region', 'prediction_type']
    sample_cols = [col for col in sample_cols if col in new_data.columns]
    # 添加概率列
    for region in region_names[:2]:  # 只显示前两个概率列
        sample_cols.append(f'prob_{region}')
    print(new_data[sample_cols].head(20).to_string())
    
    print("\n" + "="*70)
    print("✅ All processing completed!")
    print("="*70)


if __name__ == "__main__":
    main()