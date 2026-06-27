# GBDT_model.py

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.utils.class_weight import compute_class_weight
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import warnings
import time
import sys
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class HierarchicalGBDTClassifier:
    """
    Hierarchical GBDT Classifier with simplified categorical features.
    
    Features used:
    - Numerical: All numerical features (active_days, avg_tx_per_day, night_ratio, etc.)
    - Categorical: Only top1_cex_region, top2_cex_region (removed token, namespace, cex names)
    - EXCLUDED: cex_interaction_type, top1_token~top10_token, top1_namespace~top10_namespace,
                top1_cex~top5_cex, data_quality
    """
    
    def __init__(self, random_state=42, verbose=True, feature_penalty=None):
        self.random_state = random_state
        self.verbose = verbose
        self.feature_penalty = feature_penalty or {}
        self.model_level1 = None
        self.model_level2_na_lac = None
        self.model_level3_ame_europe = None
        self.training_time = {}
        self.training_history = {
            'level1': {'loss': [], 'accuracy': []},
            'level2': {'loss': [], 'accuracy': []},
            'level3': {'loss': [], 'accuracy': []}
        }
        self.validation_history = {
            'level1': {'loss': [], 'accuracy': []},
            'level2': {'loss': [], 'accuracy': []},
            'level3': {'loss': [], 'accuracy': []}
        }
        self.penalized_features = []
        self.label_encoders = {}
        self.categorical_feature_names = []
        self.feature_names = []
    
    def _print_progress(self, message, level="INFO"):
        if self.verbose:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
            sys.stdout.flush()
    
    def _get_categorical_features(self, X):
        """
        获取所有需要编码的分类特征
        简化版：只保留 top1_cex_region 和 top2_cex_region
        移除了：token, namespace, cex 名称, data_quality
        """
        categorical_features = [
            # 只保留这两个 CEX 区域特征
            'top1_cex_region', 'top2_cex_region',
        ]
        
        # 只返回数据中存在的特征
        return [col for col in categorical_features if col in X.columns]
    
    def _prepare_data(self, X, fit_encoders=False):
        """
        Prepare features with simplified categorical encoding.
        """
        self._print_progress("Starting data preprocessing...")
        X_processed = X.copy()
        
        # ========== 识别分类特征 ==========
        if fit_encoders:
            self.categorical_feature_names = self._get_categorical_features(X)
            self._print_progress(f"Identified {len(self.categorical_feature_names)} categorical features")
            if self.verbose and len(self.categorical_feature_names) > 0:
                print(f"  Categorical features: {self.categorical_feature_names}")
        
        # 获取所有数值特征（排除分类特征）
        all_numeric_cols = X_processed.select_dtypes(include=[np.number]).columns.tolist()
        numeric_cols = [col for col in all_numeric_cols if col not in self.categorical_feature_names]
        
        # ========== 处理数值特征 ==========
        self._print_progress(f"Processing {len(numeric_cols)} numerical features...")
        for col in tqdm(numeric_cols, desc="Filling numerical features", disable=not self.verbose):
            X_processed[col] = pd.to_numeric(X_processed[col], errors='coerce').fillna(0)
            
            if col in self.feature_penalty:
                penalty = self.feature_penalty[col]
                X_processed[col] = X_processed[col] * penalty
                self.penalized_features.append(col)
                self._print_progress(f"Applied penalty factor {penalty} to feature: {col}")
        
        # ========== 处理分类特征 ==========
        if len(self.categorical_feature_names) > 0:
            self._print_progress(f"Encoding {len(self.categorical_feature_names)} categorical features...")
            
            # 统一转换为字符串
            for col in self.categorical_feature_names:
                if col in X_processed.columns:
                    X_processed[col] = X_processed[col].fillna('MISSING')
                    X_processed[col] = X_processed[col].astype(str)
                    X_processed[col] = X_processed[col].str.strip()
                    X_processed[col] = X_processed[col].replace('', 'MISSING')
            
            for col in tqdm(self.categorical_feature_names, desc="Encoding categorical features", disable=not self.verbose):
                if col not in X_processed.columns:
                    self._print_progress(f"⚠️  Column '{col}' not found, skipping", level="WARNING")
                    continue
                
                if fit_encoders:
                    le = LabelEncoder()
                    all_values = list(X_processed[col].unique()) + ['UNKNOWN']
                    le.fit(all_values)
                    self.label_encoders[col] = le
                    X_processed[col] = le.transform(X_processed[col])
                    self._print_progress(f"Fitted encoder for {col} with {len(le.classes_)} classes (including UNKNOWN)")
                else:
                    if col not in self.label_encoders:
                        self._print_progress(f"⚠️  Encoder for '{col}' not found, creating new", level="WARNING")
                        le = LabelEncoder()
                        all_values = list(X_processed[col].unique()) + ['UNKNOWN']
                        le.fit(all_values)
                        self.label_encoders[col] = le
                        X_processed[col] = le.transform(X_processed[col])
                        continue
                    
                    le = self.label_encoders[col]
                    
                    if 'UNKNOWN' in le.classes_:
                        unknown_idx = le.transform(['UNKNOWN'])[0]
                    else:
                        classes = list(le.classes_) + ['UNKNOWN']
                        le = LabelEncoder()
                        le.fit(classes)
                        self.label_encoders[col] = le
                        unknown_idx = le.transform(['UNKNOWN'])[0]
                    
                    def safe_transform_with_le(x, encoder=le, unknown=unknown_idx):
                        try:
                            return encoder.transform([x])[0]
                        except ValueError:
                            return unknown
                    
                    X_processed[col] = X_processed[col].apply(safe_transform_with_le)
                    
                    if not hasattr(self, '_warned_features'):
                        self._warned_features = set()
                    if col not in self._warned_features:
                        if (X_processed[col] == unknown_idx).any():
                            self._print_progress(f"⚠️  New categories found in '{col}', mapped to UNKNOWN", level="WARNING")
                            self._warned_features.add(col)
                
                if col in self.feature_penalty:
                    penalty = self.feature_penalty[col]
                    X_processed[col] = X_processed[col] * penalty
                    self.penalized_features.append(col)
                    self._print_progress(f"Applied penalty factor {penalty} to feature: {col}")
        
        # ========== 确保所有列都是数值类型 ==========
        remaining_cols = X_processed.select_dtypes(include=['object', 'category']).columns
        if len(remaining_cols) > 0:
            self._print_progress(f"⚠️  Warning: {len(remaining_cols)} columns still non-numeric, converting...", level="WARNING")
            for col in remaining_cols:
                try:
                    X_processed[col] = pd.to_numeric(X_processed[col], errors='coerce').fillna(0)
                except:
                    X_processed[col] = 0
        
        X_processed = X_processed.astype(np.float32)
        
        if len(self.penalized_features) > 0:
            print(f"\n⚠️  Feature Penalties Applied:")
            for feat in set(self.penalized_features):
                print(f"  {feat}: factor = {self.feature_penalty[feat]} "
                      f"({(1-self.feature_penalty[feat])*100:.0f}% reduction)")
        
        self._print_progress("Data preprocessing completed!")
        return X_processed
    
    # ========== 以下是其他方法（保持不变） ==========
    
    def _compute_inverse_frequency_weights(self, y):
        """
        Compute inverse frequency weights as described in the paper.
        Enhanced with additional weights for NA_LAC and Africa.
        """
        classes = np.unique(y)
        class_counts = np.array([np.sum(y == cls) for cls in classes])
        total_samples = len(y)
        n_classes = len(classes)
        
        # 基础反频率权重
        class_weights = total_samples / (n_classes * class_counts)
        sample_weights = np.zeros(len(y))
        
        for cls, weight in zip(classes, class_weights):
            sample_weights[y == cls] = weight
        
        # 🔧 为 NA_LAC 增加权重（北美和拉美）
        na_lac_classes = ['NA_LAC']
        for cls in na_lac_classes:
            if cls in classes:
                mask = y == cls
                sample_weights[mask] *= 1.5  # 增加50%权重
                print(f"Boosted {cls} weight by 50%")
        
        # 🔧 为 Africa 增加权重（在 Level 3 中体现）
        # 注意：Africa 在 Level 3 中是 'Africa and Middle East'
        # 我们需要在 Level 3 的训练中增加权重
        # 但由于 _compute_inverse_frequency_weights 在 Level 1,2,3 都会被调用，
        # 我们需要区分是哪个 Level
        
        sample_weights = sample_weights * (total_samples / np.sum(sample_weights))
        return sample_weights

    def _create_level1_target(self, y):
        mapping = {
            'North America': 'NA_LAC',
            'Latin America and Caribbean': 'NA_LAC',
            'Europe': 'AME_Europe',
            'Africa and Middle East': 'AME_Europe',
            'Asia and Pacific': 'Asia'
        }
        return np.array([mapping[val] for val in y])
    
    def _train_with_progress(self, model, X_train, X_val, y_train, y_val, 
                            sample_weights, model_name, level):
        self._print_progress(f"Starting training {model_name}...")
        
        n_estimators = model.n_estimators
        self._print_progress(f"Total iterations: {n_estimators}")
        
        pbar = tqdm(total=n_estimators, desc=f"Training {model_name}", 
                   disable=not self.verbose, unit="trees")
        
        model.warm_start = True
        
        val_accuracies = []
        val_losses = []
        train_accuracies = []
        train_losses = []
        
        batch_size = 10
        for i in range(0, n_estimators, batch_size):
            current_n = min(i + batch_size, n_estimators)
            model.n_estimators = current_n
            
            model.fit(X_train, y_train, sample_weight=sample_weights)
            
            train_pred = model.predict(X_train)
            train_acc = accuracy_score(y_train, train_pred)
            train_loss = 1 - train_acc
            
            val_pred = model.predict(X_val)
            val_acc = accuracy_score(y_val, val_pred)
            val_loss = 1 - val_acc
            
            train_accuracies.append(train_acc)
            train_losses.append(train_loss)
            val_accuracies.append(val_acc)
            val_losses.append(val_loss)
            
            pbar.update(current_n - i)
            pbar.set_postfix({
                'train_acc': f'{train_acc:.4f}',
                'val_acc': f'{val_acc:.4f}'
            })
        
        pbar.close()
        model.warm_start = False
        
        self.training_history[level]['accuracy'] = train_accuracies
        self.training_history[level]['loss'] = train_losses
        self.validation_history[level]['accuracy'] = val_accuracies
        self.validation_history[level]['loss'] = val_losses
        
        self._print_progress(f"{model_name} training completed!")
        return model
    
    def fit(self, X, y, val_size=0.2):
        print("="*70)
        print("🚀 Starting Hierarchical GBDT Model Training (Simplified)")
        print("   ✅ Using Inverse Frequency Weighting for Class Imbalance")
        print("   ✅ Simplified Categorical Features: ONLY top1_cex_region, top2_cex_region")
        print("   ✅ EXCLUDED: token, namespace, cex names, data_quality")
        if self.feature_penalty:
            print("   ✅ Feature Penalties Active")
        print("="*70)
        start_time = time.time()
        
        self.feature_names = X.columns.tolist()
        
        self._print_progress("Step 1/5: Preparing data with feature penalties")
        X_processed = self._prepare_data(X, fit_encoders=True)
        y = np.array(y)
        
        X_train, X_val, y_train, y_val = train_test_split(
            X_processed, y, test_size=val_size, random_state=self.random_state, stratify=y
        )
        
        print(f"\n📊 Data Split:")
        print(f"  Training set: {len(X_train)} samples")
        print(f"  Validation set: {len(X_val)} samples")
        
        print(f"\n📊 Original Class Distribution (Training):")
        for cls in np.unique(y_train):
            count = np.sum(y_train == cls)
            pct = count / len(y_train) * 100
            print(f"  {cls}: {count} ({pct:.1f}%)")
        
        # ========== Level 1 ==========
        self._print_progress("Step 2/5: Training Level 1 - Coarse Classification (3 classes)")
        print("  Classes: [NA+LAC, AME+Europe, Asia]")
        y_train_level1 = self._create_level1_target(y_train)
        y_val_level1 = self._create_level1_target(y_val)
        level1_classes = np.unique(y_train_level1)
        
        print(f"\n  Level 1 Class Distribution:")
        for cls in level1_classes:
            count = np.sum(y_train_level1 == cls)
            pct = count / len(y_train_level1) * 100
            print(f"    {cls}: {count} ({pct:.1f}%)")
        
        sample_weights_l1 = self._compute_inverse_frequency_weights(y_train_level1)
        
        print(f"\n  ✅ Inverse Frequency Weights (Level 1):")
        unique_classes = np.unique(y_train_level1)
        for cls in unique_classes:
            mask = y_train_level1 == cls
            avg_weight = np.mean(sample_weights_l1[mask])
            count = np.sum(mask)
            print(f"    {cls}: count={count}, avg_weight={avg_weight:.3f}")
        
        self.model_level1 = GradientBoostingClassifier(
            n_estimators=80,
            learning_rate=0.06,
            max_depth=8,
            min_samples_split=20,
            min_samples_leaf=10,
            subsample=0.8,
            random_state=self.random_state,
            verbose=0,
            max_features=None
        )
        
        l1_start = time.time()
        self.model_level1 = self._train_with_progress(
            self.model_level1, X_train, X_val, 
            y_train_level1, y_val_level1, 
            sample_weights_l1, "Level 1", "level1"
        )
        self.training_time['level1'] = time.time() - l1_start
        print(f"  ✅ Level 1 completed (Time: {self.training_time['level1']:.2f}s)")
        
        # ========== Level 2 ==========
        self._print_progress("Step 3/5: Training Level 2 - NA vs LAC Fine Classification")
        
        mask_na_lac = np.isin(y_train, ['North America', 'Latin America and Caribbean'])
        X_train_l2 = X_train[mask_na_lac]
        y_train_l2 = y_train[mask_na_lac]
        mask_na_lac_val = np.isin(y_val, ['North America', 'Latin America and Caribbean'])
        X_val_l2 = X_val[mask_na_lac_val]
        y_val_l2 = y_val[mask_na_lac_val]
        
        if len(np.unique(y_train_l2)) >= 2:
            print(f"  Training samples: {len(y_train_l2)}")
            for cls in np.unique(y_train_l2):
                count = np.sum(y_train_l2 == cls)
                pct = count / len(y_train_l2) * 100
                print(f"    {cls}: {count} ({pct:.1f}%)")
            
            sample_weights_l2 = self._compute_inverse_frequency_weights(y_train_l2)
            
            print(f"\n  ✅ Inverse Frequency Weights (Level 2):")
            unique_classes = np.unique(y_train_l2)
            for cls in unique_classes:
                mask = y_train_l2 == cls
                avg_weight = np.mean(sample_weights_l2[mask])
                count = np.sum(mask)
                print(f"    {cls}: count={count}, avg_weight={avg_weight:.3f}")
            
            self.model_level2_na_lac = GradientBoostingClassifier(
                n_estimators=50,
                learning_rate=0.06,
                max_depth=6,
                min_samples_split=20,
                min_samples_leaf=10,
                subsample=0.8,
                random_state=self.random_state,
                verbose=0,
                max_features=None
            )
            
            l2_start = time.time()
            self.model_level2_na_lac = self._train_with_progress(
                self.model_level2_na_lac, X_train_l2, X_val_l2,
                y_train_l2, y_val_l2,
                sample_weights_l2, "Level 2 (NA vs LAC)", "level2"
            )
            self.training_time['level2'] = time.time() - l2_start
            print(f"  ✅ Level 2 completed (Time: {self.training_time['level2']:.2f}s)")
        else:
            print(f"  ⚠️  NA/LAC has only {len(np.unique(y_train_l2))} classes, skipping")
            self.model_level2_na_lac = None
        
        # 在 fit 方法中，Level 3 训练部分

        # ========== Level 3: AME vs Europe ==========
        self._print_progress("Step 4/5: Training Level 3 - AME vs Europe Fine Classification")

        mask_ame_europe = np.isin(y_train, ['Africa and Middle East', 'Europe'])
        X_train_l3 = X_train[mask_ame_europe]
        y_train_l3 = y_train[mask_ame_europe]
        mask_ame_europe_val = np.isin(y_val, ['Africa and Middle East', 'Europe'])
        X_val_l3 = X_val[mask_ame_europe_val]
        y_val_l3 = y_val[mask_ame_europe_val]

        if len(np.unique(y_train_l3)) >= 2:
            print(f"  Training samples: {len(y_train_l3)}")
            for cls in np.unique(y_train_l3):
                count = np.sum(y_train_l3 == cls)
                pct = count / len(y_train_l3) * 100
                print(f"    {cls}: {count} ({pct:.1f}%)")
            
            # 计算基础权重
            sample_weights_l3 = self._compute_inverse_frequency_weights(y_train_l3)
            
            # 🔧 为 Africa 增加额外权重
            africa_mask = y_train_l3 == 'Africa and Middle East'
            if africa_mask.sum() > 0:
                # 增加 80% 权重（比 NA_LAC 的 50% 更高，因为非洲样本更少）
                sample_weights_l3[africa_mask] *= 1.5
                print(f"  ✅ Boosted Africa weight by 50%")
            
            print(f"\n  ✅ Inverse Frequency Weights (Level 3 with Africa boost):")
            unique_classes = np.unique(y_train_l3)
            for cls in unique_classes:
                mask = y_train_l3 == cls
                avg_weight = np.mean(sample_weights_l3[mask])
                count = np.sum(mask)
                print(f"    {cls}: count={count}, avg_weight={avg_weight:.3f}")
            
            self.model_level3_ame_europe = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.06,
                max_depth=8,
                min_samples_split=20,
                min_samples_leaf=10,
                subsample=0.8,
                random_state=self.random_state,
                verbose=0,
                max_features='sqrt'
            )
            
            l3_start = time.time()
            self.model_level3_ame_europe = self._train_with_progress(
                self.model_level3_ame_europe, X_train_l3, X_val_l3,
                y_train_l3, y_val_l3,
                sample_weights_l3, "Level 3 (AME vs Europe)", "level3"
            )
            self.training_time['level3'] = time.time() - l3_start
            print(f"  ✅ Level 3 completed (Time: {self.training_time['level3']:.2f}s)")
        else:
            print(f"  ⚠️  AME/Europe has only {len(np.unique(y_train_l3))} classes, skipping")
            self.model_level3_ame_europe = None
        
        total_time = time.time() - start_time
        self.training_time['total'] = total_time
        
        print("\n" + "="*70)
        print("✅ Hierarchical Model Training Complete!")
        print("="*70)
        print(f"📊 Training Time Statistics:")
        print(f"  Level 1: {self.training_time['level1']:.2f}s")
        if 'level2' in self.training_time:
            print(f"  Level 2: {self.training_time['level2']:.2f}s")
        if 'level3' in self.training_time:
            print(f"  Level 3: {self.training_time['level3']:.2f}s")
        print(f"  Total: {total_time:.2f}s")
        print("="*70)
        
        return self
    
    def predict(self, X):
        self._print_progress("Starting prediction...")
        X_processed = self._prepare_data(X, fit_encoders=False)
        X_processed = X_processed.astype(np.float32)
        
        pred_level1 = self.model_level1.predict(X_processed)
        
        final_predictions = np.array([''] * len(X_processed), dtype=object)
        pred_stats = {'Asia': 0, 'NA_LAC': 0, 'AME_Europe': 0}
        
        self._print_progress(f"Processing {len(X_processed)} samples...")
        
        for i, (pred, row) in enumerate(tqdm(zip(pred_level1, X_processed.values), 
                                              total=len(X_processed), 
                                              desc="Prediction progress", 
                                              disable=not self.verbose)):
            pred_stats[pred] += 1
            
            if pred == 'Asia':
                final_predictions[i] = 'Asia and Pacific'
            elif pred == 'NA_LAC':
                if self.model_level2_na_lac is not None:
                    final_predictions[i] = self.model_level2_na_lac.predict([row])[0]
                else:
                    final_predictions[i] = 'North America'
            elif pred == 'AME_Europe':
                if self.model_level3_ame_europe is not None:
                    final_predictions[i] = self.model_level3_ame_europe.predict([row])[0]
                else:
                    final_predictions[i] = 'Europe'
        
        print(f"\n📊 Prediction Statistics:")
        for key, value in pred_stats.items():
            print(f"  {key}: {value} ({value/len(X_processed)*100:.1f}%)")
        
        return final_predictions
    
    def predict_proba(self, X):
        """
        预测每个地区的概率分布（软分类）
        
        Parameters:
        -----------
        X : DataFrame
            输入特征
        
        Returns:
        --------
        probs : numpy array, shape (n_samples, 5)
            每个样本对5个地区的概率分布
            顺序: ['Africa and Middle East', 'Asia and Pacific', 'Europe', 
                'Latin America and Caribbean', 'North America']
        """
        self._print_progress("Starting probability prediction...")
        X_processed = self._prepare_data(X, fit_encoders=False)
        X_processed = X_processed.astype(np.float32)
        
        # 区域名称
        region_names = ['Africa and Middle East', 'Asia and Pacific', 'Europe', 
                        'Latin America and Caribbean', 'North America']
        
        # Level 1: 粗分类概率
        prob_level1 = self.model_level1.predict_proba(X_processed)
        level1_classes = self.model_level1.classes_
        
        # 初始化最终概率矩阵 (n_samples, 5)
        final_probs = np.zeros((len(X_processed), 5))
        
        for i, row in enumerate(X_processed.values):
            # Level 1 概率
            l1_probs = prob_level1[i]
            
            # 对于每个 Level 1 类别，分配到具体区域
            for j, l1_class in enumerate(level1_classes):
                l1_prob = l1_probs[j]
                
                if l1_class == 'Asia':
                    # Asia -> Asia and Pacific (index 1)
                    final_probs[i, 1] += l1_prob
                    
                elif l1_class == 'NA_LAC':
                    if self.model_level2_na_lac is not None:
                        # 获取 Level 2 概率 (NA vs LAC)
                        l2_probs = self.model_level2_na_lac.predict_proba([row])[0]
                        l2_classes = self.model_level2_na_lac.classes_
                        
                        for k, l2_class in enumerate(l2_classes):
                            if l2_class == 'Latin America and Caribbean':
                                final_probs[i, 3] += l1_prob * l2_probs[k]
                            elif l2_class == 'North America':
                                final_probs[i, 4] += l1_prob * l2_probs[k]
                    else:
                        # 如果 Level 2 不存在，默认分到北美
                        final_probs[i, 4] += l1_prob
                        
                elif l1_class == 'AME_Europe':
                    if self.model_level3_ame_europe is not None:
                        # 获取 Level 3 概率 (AME vs Europe)
                        l3_probs = self.model_level3_ame_europe.predict_proba([row])[0]
                        l3_classes = self.model_level3_ame_europe.classes_
                        
                        for k, l3_class in enumerate(l3_classes):
                            if l3_class == 'Africa and Middle East':
                                final_probs[i, 0] += l1_prob * l3_probs[k]
                            elif l3_class == 'Europe':
                                final_probs[i, 2] += l1_prob * l3_probs[k]
                    else:
                        # 如果 Level 3 不存在，默认分到欧洲
                        final_probs[i, 2] += l1_prob
        
        # 确保每行概率和为1（归一化）
        row_sums = final_probs.sum(axis=1, keepdims=True)
        # 避免除以0
        row_sums = np.where(row_sums == 0, 1, row_sums)
        final_probs = final_probs / row_sums
        
        return final_probs


def predict_proba_level1(self, X):
    """
    只返回 Level 1 的概率（3个粗分类）
    用于快速诊断
    """
    X_processed = self._prepare_data(X, fit_encoders=False)
    X_processed = X_processed.astype(np.float32)
    return self.model_level1.predict_proba(X_processed)

def plot_confusion_matrix_normalized(y_true, y_pred, title="Confusion Matrix"):
    cm = confusion_matrix(y_true, y_pred)
    labels = np.unique(y_true)
    
    cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    cm_normalized = cm_normalized * 100
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    sns.heatmap(cm_normalized, annot=True, fmt='.1f', cmap='Blues',
                xticklabels=labels, yticklabels=labels, ax=ax,
                cbar_kws={'label': 'Percentage (%)', 'shrink': 0.8},
                vmin=0, vmax=100,
                annot_kws={'size': 12, 'weight': 'bold'})
    
    ax.set_xlabel('Predicted Region', fontsize=14, fontweight='bold')
    ax.set_ylabel('True Region', fontsize=14, fontweight='bold')
    ax.set_title(f'{title}\n(Rows are normalized to sum to 100%)', 
                fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    return fig


def plot_feature_importance_with_penalty(model, feature_names, penalized_features, top_n=25):
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]
    
    colors = []
    for i in indices:
        if feature_names[i] in penalized_features:
            colors.append('orange')
        else:
            colors.append('skyblue')
    
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(range(top_n), importances[indices][::-1], color=colors[::-1])
    ax.set_yticks(range(top_n))
    ax.set_yticklabels([feature_names[i] for i in indices[::-1]])
    ax.set_xlabel('Feature Importance', fontsize=12)
    ax.set_title(f'Top {top_n} Most Important Features - Level 1\n(Orange: Penalized Features)', 
                fontsize=14)
    ax.grid(True, alpha=0.3, axis='x')
    
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='skyblue', label='Normal Feature'),
                       Patch(facecolor='orange', label='Penalized Feature')]
    ax.legend(handles=legend_elements, loc='lower right')
    
    plt.tight_layout()
    return fig


def train_model(data_path, test_size=0.1, val_size=0.2, cex_penalty=0.3):
    """
    Train simplified hierarchical GBDT model.
    """
    print("="*70)
    print("📂 Loading Data...")
    print("="*70)
    
    df = pd.read_csv(data_path)
    print(f"✅ Data loaded successfully!")
    print(f"  Total samples: {len(df)}")
    print(f"  Total columns: {df.shape[1]}")
    
    label_col = 'final_label'
    if label_col not in df.columns:
        print(f"❌ Error: '{label_col}' not found in columns")
        return None, None, None, None, None
    
    # ========== 定义要排除的特征 ==========
    exclude_cols = [
        'wallet', 
        label_col, 
        'cex_interaction_type',
        # 排除所有 token 特征
        'top1_token', 'top2_token', 'top3_token', 'top4_token', 'top5_token',
        'top6_token', 'top7_token', 'top8_token', 'top9_token', 'top10_token',
        'top1_token_count', 'top2_token_count', 'top3_token_count', 'top4_token_count', 'top5_token_count',
        'top6_token_count', 'top7_token_count', 'top8_token_count', 'top9_token_count', 'top10_token_count',
        # 排除所有 namespace 特征
        'top1_namespace', 'top2_namespace', 'top3_namespace', 'top4_namespace', 'top5_namespace',
        'top6_namespace', 'top7_namespace', 'top8_namespace', 'top9_namespace', 'top10_namespace',
        'top1_namespace_count', 'top2_namespace_count', 'top3_namespace_count', 'top4_namespace_count', 'top5_namespace_count',
        'top6_namespace_count', 'top7_namespace_count', 'top8_namespace_count', 'top9_namespace_count', 'top10_namespace_count',
        # 排除 CEX 名称（只保留 region）
        'top1_cex', 'top2_cex', 'top3_cex', 'top4_cex', 'top5_cex',
        'top1_cex_count', 'top2_cex_count', 'top3_cex_count', 'top4_cex_count', 'top5_cex_count',
        # 排除 data_quality
        'data_quality','top1_5_cex_total_count','top1_5_cex_region_diversity'

    ]
    
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    print(f"\n✅ EXCLUDED features: {len(exclude_cols)} features removed")
    print(f"   Using {len(feature_cols)} features for training")
    print(f"\n📋 Features kept:")
    print(f"  Categorical: top1_cex_region, top2_cex_region")
    print(f"  Numerical: All other features")
    
    X = df[feature_cols]
    y = df[label_col]
    
    print(f"\n📊 Dataset Information:")
    print(f"  Number of features: {len(feature_cols)}")
    print(f"  Target classes: {y.nunique()}")
    
    print(f"\n📊 Class Distribution (Full Dataset):")
    for cls in y.value_counts().index:
        count = y.value_counts()[cls]
        pct = count / len(y) * 100
        print(f"  {cls}: {count} ({pct:.1f}%)")
    
    # Define feature penalties
    feature_penalty = {
        'top1_cex_region': cex_penalty,
        'top2_cex_region': cex_penalty * 0.8,
    }
    
    feature_penalty = {k: v for k, v in feature_penalty.items() if k in feature_cols}
    
    if feature_penalty:
        print(f"\n⚠️  Feature Penalty Configuration:")
        for feat, penalty in feature_penalty.items():
            print(f"  {feat}: factor = {penalty} ({(1-penalty)*100:.0f}% reduction)")
    
    # Split data
    print(f"\n🔀 Splitting Training and Test Sets (Test: {test_size*100:.0f}%)")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    print(f"  Training set: {len(X_train)} samples")
    print(f"  Test set: {len(X_test)} samples")
    
    # Train model
    print("\n")
    model = HierarchicalGBDTClassifier(
        random_state=42, 
        verbose=True,
        feature_penalty=feature_penalty
    )
    model.fit(X_train, y_train, val_size=val_size)
    
    # Visualizations
    print("\n" + "="*70)
    print("📊 Generating Visualizations")
    print("="*70)
    
    print("\n1. Plotting feature importance...")
    fig_feat = plot_feature_importance_with_penalty(
        model.model_level1, 
        feature_cols,
        model.penalized_features,
        top_n=25
    )
    fig_feat.savefig('feature_importance_simplified.png', dpi=300, bbox_inches='tight')
    print("   ✅ Saved: feature_importance_simplified.png")
    
    print("\n2. Evaluating on test set...")
    print("\n⏳ Making predictions on test set...")
    y_pred = model.predict(X_test)
    
    print("\n3. Plotting confusion matrix...")
    fig_cm = plot_confusion_matrix_normalized(
        y_test, y_pred, 
        title="Confusion Matrix - Simplified Model"
    )
    fig_cm.savefig('confusion_matrix_simplified.png', dpi=300, bbox_inches='tight')
    print("   ✅ Saved: confusion_matrix_simplified.png")
    
    # Performance Metrics
    print("\n" + "="*70)
    print("📈 Model Performance Report")
    print("   ✅ Simplified Features (No token, namespace, cex names)")
    if feature_penalty:
        print("   ✅ Using Feature Penalty for CEX Region Features")
    print("="*70)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    acc = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average='macro')
    f1_weighted = f1_score(y_test, y_pred, average='weighted')
    
    print(f"\n🎯 Overall Test Metrics:")
    print(f"  Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print(f"  Macro F1: {f1_macro:.4f}")
    print(f"  Weighted F1: {f1_weighted:.4f}")
    
    # Per-class accuracy
    print("\n📊 Per-Class Performance:")
    print("="*70)
    cm = confusion_matrix(y_test, y_pred)
    for i, cls in enumerate(np.unique(y_test)):
        total = np.sum(y_test == cls)
        correct = cm[i, i]
        acc_class = correct / total if total > 0 else 0
        print(f"  {cls}: {acc_class:.2%} ({correct}/{total})")
    
    # Feature importance summary
    print("\n📊 Feature Importance Analysis:")
    print("="*70)
    importances = model.model_level1.feature_importances_
    feature_importance_dict = dict(zip(feature_cols, importances))
    sorted_features = sorted(feature_importance_dict.items(), key=lambda x: x[1], reverse=True)
    
    print("\nTop 10 Features:")
    for i, (feat, imp) in enumerate(sorted_features[:10]):
        penalized = " (PENALIZED)" if feat in feature_penalty else ""
        print(f"  {i+1}. {feat}: {imp:.4f}{penalized}")
    
    plt.show()
    
    print("\n" + "="*70)
    print("✅ All visualizations completed!")
    print("="*70)
    
    return model, X_train, X_test, y_train, y_test

def save_model(model, feature_names, filepath_prefix='GBDT_model'):
    joblib.dump(model, f'{filepath_prefix}.joblib')
    print(f"✅ Model saved to {filepath_prefix}.joblib")
    
    joblib.dump(feature_names, f'{filepath_prefix}_features.joblib')
    print(f"✅ Feature names saved to {filepath_prefix}_features.joblib")
    
    encoder_info = {
        'label_encoders': model.label_encoders,
        'categorical_feature_names': model.categorical_feature_names
    }
    joblib.dump(encoder_info, f'{filepath_prefix}_encoders.joblib')
    print(f"✅ Encoder info saved to {filepath_prefix}_encoders.joblib")
    
    config_info = {
        'feature_names': feature_names,
        'feature_penalty': model.feature_penalty,
        'excluded_features': ['wallet', 'final_label', 'cex_interaction_type', 
                              'token features', 'namespace features', 'cex names', 'data_quality'],
        'training_time': model.training_time,
        'random_state': model.random_state
    }
    joblib.dump(config_info, f'{filepath_prefix}_config.joblib')
    print(f"✅ Config info saved to {filepath_prefix}_config.joblib")


def load_model(filepath_prefix='GBDT_model'):
    model = joblib.load(f'{filepath_prefix}.joblib')
    print(f"✅ Model loaded from {filepath_prefix}.joblib")
    
    try:
        feature_names = joblib.load(f'{filepath_prefix}_features.joblib')
        print(f"✅ Feature names loaded from {filepath_prefix}_features.joblib")
    except:
        print(f"⚠️  Feature names file not found")
        feature_names = None
    
    try:
        encoder_info = joblib.load(f'{filepath_prefix}_encoders.joblib')
        model.label_encoders = encoder_info['label_encoders']
        model.categorical_feature_names = encoder_info['categorical_feature_names']
        print(f"✅ Encoder info loaded from {filepath_prefix}_encoders.joblib")
    except:
        print(f"⚠️  Encoder info file not found")
    
    return model, feature_names


if __name__ == "__main__":
    print("="*80)
    print("🏦 Training Simplified Hierarchical GBDT Model")
    print("   🔧 EXCLUDED: token, namespace, cex names, data_quality")
    print("   ✅ KEPT: top1_cex_region, top2_cex_region + all numerical features")
    print("="*80)
    
    model, X_train, X_test, y_train, y_test = train_model(
        'training_data_final_kept.csv',
        test_size=0.1,
        val_size=0.2,
        cex_penalty=0.5  # 可以尝试不同的惩罚值
    )
    
    save_model(model, X_train.columns.tolist(), 'GBDT_model_simplified')
    
    print("\n" + "="*80)
    print("✅ Training completed successfully!")
    print(f"   Model saved to: GBDT_model_simplified.joblib")
    print("="*80)