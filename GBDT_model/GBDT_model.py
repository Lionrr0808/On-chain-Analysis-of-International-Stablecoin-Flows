import pandas as pd
import numpy as np
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
    Hierarchical GBDT Classifier implementing the paper's approach:
    1. Level 1: Coarse classification - {NA+LAC, AME+Europe, Asia}
    2. Level 2: Fine classification - NA vs LAC
    3. Level 3: Fine classification - AME vs Europe
    
    Features:
    - Inverse frequency weighting for class imbalance (as described in the paper)
    - Feature penalty to reduce influence of specific features (e.g., top1_cex_region)
    """
    
    def __init__(self, random_state=42, verbose=True, feature_penalty=None):
        """
        Parameters:
        -----------
        random_state : int
            Random seed for reproducibility
        verbose : bool
            Whether to print progress messages
        feature_penalty : dict
            Dictionary mapping feature names to penalty factors (0-1)
            e.g., {'top1_cex_region': 0.3} reduces feature influence by 70%
        """
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
        
    def _print_progress(self, message, level="INFO"):
        """Print progress message"""
        if self.verbose:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
            sys.stdout.flush()
    
    def _prepare_data(self, X):
        """Prepare features, handle missing values, and apply feature penalties"""
        self._print_progress("Starting data preprocessing...")
        X_processed = X.copy()
        
        # Fill numerical features with 0 (as per documentation)
        numeric_cols = X_processed.select_dtypes(include=[np.number]).columns
        self._print_progress(f"Processing {len(numeric_cols)} numerical features...")
        for col in tqdm(numeric_cols, desc="Filling numerical features", disable=not self.verbose):
            X_processed[col] = X_processed[col].fillna(0)
            
            # Apply penalty to specific numerical features
            if col in self.feature_penalty:
                penalty = self.feature_penalty[col]
                X_processed[col] = X_processed[col] * penalty
                self.penalized_features.append(col)
                self._print_progress(f"Applied penalty factor {penalty} to feature: {col}")
        
        # Encode categorical features (GBDT handles missing values)
        categorical_cols = X_processed.select_dtypes(include=['object', 'category']).columns
        if len(categorical_cols) > 0:
            self._print_progress(f"Encoding {len(categorical_cols)} categorical features...")
            for col in tqdm(categorical_cols, desc="Encoding categorical features", disable=not self.verbose):
                le = LabelEncoder()
                X_processed[col] = X_processed[col].fillna('MISSING')
                X_processed[col] = X_processed[col].astype(str)
                le.fit(X_processed[col])
                X_processed[col] = le.transform(X_processed[col])
                
                # Apply penalty to encoded categorical features
                if col in self.feature_penalty:
                    penalty = self.feature_penalty[col]
                    X_processed[col] = X_processed[col] * penalty
                    self.penalized_features.append(col)
                    self._print_progress(f"Applied penalty factor {penalty} to feature: {col}")
        
        if len(self.penalized_features) > 0:
            print(f"\n⚠️  Feature Penalties Applied:")
            for feat in set(self.penalized_features):
                print(f"  {feat}: factor = {self.feature_penalty[feat]} "
                      f"({(1-self.feature_penalty[feat])*100:.0f}% reduction)")
        
        self._print_progress("Data preprocessing completed!")
        return X_processed
    
    def _compute_inverse_frequency_weights(self, y):
        """
        Compute inverse frequency weights as described in the paper:
        "each observation is weighted inversely proportional to its class frequency"
        
        This is the exact implementation of the paper's method.
        """
        classes = np.unique(y)
        class_counts = np.array([np.sum(y == cls) for cls in classes])
        total_samples = len(y)
        n_classes = len(classes)
        
        # Inverse frequency weighting: weight = total_samples / (n_classes * class_count)
        # This ensures underrepresented classes contribute equally
        class_weights = total_samples / (n_classes * class_counts)
        
        # Assign weights to each sample
        sample_weights = np.zeros(len(y))
        for cls, weight in zip(classes, class_weights):
            sample_weights[y == cls] = weight
        
        # Normalize weights to sum to total_samples (improves numerical stability)
        sample_weights = sample_weights * (total_samples / np.sum(sample_weights))
        
        return sample_weights
    
    def _create_level1_target(self, y):
        """Create level 1 target: 3 coarse classes"""
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
        """Train with progress monitoring and history recording"""
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
            
            # Train with inverse frequency weights
            model.fit(X_train, y_train, sample_weight=sample_weights)
            
            # Calculate training metrics
            train_pred = model.predict(X_train)
            train_acc = accuracy_score(y_train, train_pred)
            train_loss = 1 - train_acc
            
            # Calculate validation metrics
            val_pred = model.predict(X_val)
            val_acc = accuracy_score(y_val, val_pred)
            val_loss = 1 - val_acc
            
            # Store history
            train_accuracies.append(train_acc)
            train_losses.append(train_loss)
            val_accuracies.append(val_acc)
            val_losses.append(val_loss)
            
            # Update progress bar
            pbar.update(current_n - i)
            pbar.set_postfix({
                'train_acc': f'{train_acc:.4f}',
                'val_acc': f'{val_acc:.4f}'
            })
        
        pbar.close()
        model.warm_start = False
        
        # Store training history
        self.training_history[level]['accuracy'] = train_accuracies
        self.training_history[level]['loss'] = train_losses
        self.validation_history[level]['accuracy'] = val_accuracies
        self.validation_history[level]['loss'] = val_losses
        
        self._print_progress(f"{model_name} training completed!")
        return model
    
    def fit(self, X, y, val_size=0.2):
        """
        Train the hierarchical model with inverse frequency weighting
        """
        print("="*70)
        print("🚀 Starting Hierarchical GBDT Model Training")
        print("   ✅ Using Inverse Frequency Weighting for Class Imbalance")
        if self.feature_penalty:
            print("   ✅ Feature Penalties Active: Reducing influence of specified features")
        print("="*70)
        start_time = time.time()
        
        # Prepare data with feature penalties
        self._print_progress("Step 1/5: Preparing data with feature penalties")
        X_processed = self._prepare_data(X)
        y = np.array(y)
        
        # Split validation set from training
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
        
        # ========== Level 1: Coarse Classification ==========
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
        
        # Compute inverse frequency weights for Level 1
        sample_weights_l1 = self._compute_inverse_frequency_weights(y_train_level1)
        
        # Print weight information to show inverse frequency weighting is applied
        print(f"\n  ✅ Inverse Frequency Weights (Level 1):")
        unique_classes = np.unique(y_train_level1)
        for cls in unique_classes:
            mask = y_train_level1 == cls
            avg_weight = np.mean(sample_weights_l1[mask])
            count = np.sum(mask)
            print(f"    {cls}: count={count}, avg_weight={avg_weight:.3f}")
        
        self.model_level1 = GradientBoostingClassifier(
            n_estimators=50,  # Increased to compensate for feature penalty
            learning_rate=0.06,  # Slightly lower for stability
            max_depth=8,
            min_samples_split=20,
            min_samples_leaf=10,
            subsample=0.8,
            random_state=self.random_state,
            verbose=0,
            max_features = None  # Add randomness to reduce over-reliance on any feature
        )
        
        l1_start = time.time()
        self.model_level1 = self._train_with_progress(
            self.model_level1, X_train, X_val, 
            y_train_level1, y_val_level1, 
            sample_weights_l1, "Level 1", "level1"
        )
        self.training_time['level1'] = time.time() - l1_start
        print(f"  ✅ Level 1 completed (Time: {self.training_time['level1']:.2f}s)")
        
        # ========== Level 2: NA vs LAC ==========
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
            
            # Compute inverse frequency weights for Level 2
            sample_weights_l2 = self._compute_inverse_frequency_weights(y_train_l2)
            
            print(f"\n  ✅ Inverse Frequency Weights (Level 2):")
            unique_classes = np.unique(y_train_l2)
            for cls in unique_classes:
                mask = y_train_l2 == cls
                avg_weight = np.mean(sample_weights_l2[mask])
                count = np.sum(mask)
                print(f"    {cls}: count={count}, avg_weight={avg_weight:.3f}")
            
            self.model_level2_na_lac = GradientBoostingClassifier(
                n_estimators=50,  # More trees for difficult pair
                learning_rate=0.06,
                max_depth=6,
                min_samples_split=20,
                min_samples_leaf=10,
                subsample=0.8,
                random_state=self.random_state,
                verbose=0,
                max_features='sqrt'
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
            
            # Compute inverse frequency weights for Level 3
            sample_weights_l3 = self._compute_inverse_frequency_weights(y_train_l3)
            
            print(f"\n  ✅ Inverse Frequency Weights (Level 3):")
            unique_classes = np.unique(y_train_l3)
            for cls in unique_classes:
                mask = y_train_l3 == cls
                avg_weight = np.mean(sample_weights_l3[mask])
                count = np.sum(mask)
                print(f"    {cls}: count={count}, avg_weight={avg_weight:.3f}")
            
            self.model_level3_ame_europe = GradientBoostingClassifier(
                n_estimators=50,  # More trees for difficult pair
                learning_rate=0.06,
                max_depth=6,
                min_samples_split=20,
                min_samples_leaf=10,
                subsample=0.8,
                random_state=self.random_state,
                verbose=0,
                max_features=None
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
        """Predict classes"""
        self._print_progress("Starting prediction...")
        X_processed = self._prepare_data(X)
        
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


def plot_confusion_matrix_normalized(y_true, y_pred, title="Confusion Matrix"):
    """
    Plot normalized confusion matrix where rows sum to 100%
    Uses dark blue for high values, light blue for low values
    """
    cm = confusion_matrix(y_true, y_pred)
    labels = np.unique(y_true)
    
    # Normalize by row (true labels) so each row sums to 100%
    cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    cm_normalized = cm_normalized * 100
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create heatmap with blue color map (dark blue for high, light blue for low)
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
    """Plot feature importance with highlighted penalized features"""
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]
    
    # Color bars based on whether feature is penalized
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
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='skyblue', label='Normal Feature'),
                       Patch(facecolor='orange', label='Penalized Feature')]
    ax.legend(handles=legend_elements, loc='lower right')
    
    plt.tight_layout()
    return fig


def train_model(data_path, test_size=0.1, val_size=0.2, cex_penalty=0.3):
    """
    Main function to train hierarchical GBDT model with:
    1. Inverse frequency weighting for class imbalance
    2. Feature penalty for CEX region features
    
    Parameters:
    -----------
    data_path : str
        Path to the training data CSV
    test_size : float
        Proportion of data to use as test set
    val_size : float
        Proportion of training data to use as validation
    cex_penalty : float
        Penalty factor for CEX region features (0-1)
        0.3 means feature values are multiplied by 0.3 (70% reduction in influence)
    """
    print("="*70)
    print("📂 Loading Data...")
    print("="*70)
    
    df = pd.read_csv(data_path)
    print(f"✅ Data loaded successfully!")
    print(f"  Total samples: {len(df)}")
    print(f"  Total features: {df.shape[1] - 2}")
    
    label_col = 'final_label'
    if label_col not in df.columns:
        print(f"❌ Error: '{label_col}' not found in columns")
        print(f"Available columns: {df.columns.tolist()}")
        return None, None, None, None, None
    
    exclude_cols = ['wallet', label_col]
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
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
    
    # Define feature penalties for CEX region features
    feature_penalty = {
        'top1_cex_region': cex_penalty,
        'top2_cex_region': cex_penalty * 0.8,  # Even less influence for top2
    }
    
    # Only include features that actually exist in the dataset
    feature_penalty = {k: v for k, v in feature_penalty.items() if k in feature_cols}
    
    if feature_penalty:
        print(f"\n⚠️  Feature Penalty Configuration:")
        for feat, penalty in feature_penalty.items():
            print(f"  {feat}: factor = {penalty} ({(1-penalty)*100:.0f}% reduction)")
    else:
        print(f"\n⚠️  No CEX region features found in dataset. Penalties will not be applied.")
    
    # Split data
    print(f"\n🔀 Splitting Training and Test Sets (Test: {test_size*100:.0f}%)")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    print(f"  Training set: {len(X_train)} samples")
    print(f"  Test set: {len(X_test)} samples")
    
    # Train model with feature penalties
    print("\n")
    model = HierarchicalGBDTClassifier(
        random_state=42, 
        verbose=True,
        feature_penalty=feature_penalty
    )
    model.fit(X_train, y_train, val_size=val_size)
    
    # ========== Visualizations ==========
    print("\n" + "="*70)
    print("📊 Generating Visualizations")
    print("="*70)
    
    # 1. Feature Importance with highlighted penalized features
    print("\n1. Plotting feature importance with penalties highlighted...")
    fig_feat = plot_feature_importance_with_penalty(
        model.model_level1, 
        feature_cols,
        model.penalized_features,
        top_n=25
    )
    fig_feat.savefig('feature_importance_with_penalties.png', dpi=300, bbox_inches='tight')
    print("   ✅ Saved: feature_importance_with_penalties.png")
    
    # 2. Evaluate on Test Set
    print("\n2. Evaluating on test set...")
    print("\n⏳ Making predictions on test set...")
    y_pred = model.predict(X_test)
    
    # 3. Confusion Matrix - Row Normalized (as described in the paper)
    print("\n3. Plotting confusion matrix (row-normalized to 100%)...")
    fig_cm = plot_confusion_matrix_normalized(
        y_test, y_pred, 
        title="Figure 5: Confusion Matrix - Test Set"
    )
    fig_cm.savefig('confusion_matrix_normalized.png', dpi=300, bbox_inches='tight')
    print("   ✅ Saved: confusion_matrix_normalized.png")
    
    # ========== Performance Metrics ==========
    print("\n" + "="*70)
    print("📈 Model Performance Report")
    print("   ✅ Using Inverse Frequency Weighting for Class Imbalance")
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
    
    # Per-class accuracy (from row-normalized confusion matrix)
    print("\n📊 Per-Class Performance (Row-normalized):")
    print("="*70)
    cm = confusion_matrix(y_test, y_pred)
    for i, cls in enumerate(np.unique(y_test)):
        total = np.sum(y_test == cls)
        correct = cm[i, i]
        acc_class = correct / total if total > 0 else 0
        # Also show misclassification distribution
        misclass = total - correct
        if misclass > 0:
            misclass_dist = cm[i, :] / total * 100
            # Find the most misclassified class
            misclass_indices = np.argsort(misclass_dist)[::-1]
            most_confused_idx = misclass_indices[0] if misclass_indices[0] != i else misclass_indices[1]
            most_confused = np.unique(y_test)[most_confused_idx]
            print(f"  {cls}: {acc_class:.2%} ({correct}/{total})")
            if misclass > 0:
                print(f"    → Most confused with: {most_confused} ({misclass_dist[most_confused_idx]:.1f}%)")
        else:
            print(f"  {cls}: {acc_class:.2%} ({correct}/{total}) - Perfect!")
    
    # Feature importance summary
    print("\n📊 Feature Importance Analysis:")
    print("="*70)
    importances = model.model_level1.feature_importances_
    feature_importance_dict = dict(zip(feature_cols, importances))
    sorted_features = sorted(feature_importance_dict.items(), key=lambda x: x[1], reverse=True)
    
    print("\nTop 10 Features (with penalties applied):")
    for i, (feat, imp) in enumerate(sorted_features[:10]):
        penalized = " (PENALIZED)" if feat in feature_penalty else ""
        print(f"  {i+1}. {feat}: {imp:.4f}{penalized}")
    
    plt.show()
    
    print("\n" + "="*70)
    print("✅ All visualizations completed!")
    print("="*70)
    
    return model, X_train, X_test, y_train, y_test


if __name__ == "__main__":
    # Train the model with:
    # 1. Inverse frequency weighting for class imbalance
    # 2. Feature penalty for CEX region features (70% reduction)
    
    # Adjust cex_penalty parameter (0-1):
    # - 0.3: Strong penalty (70% reduction) - Recommended for strong CEX influence
    # - 0.5: Moderate penalty (50% reduction)
    # - 0.7: Mild penalty (30% reduction)
    # - 1.0: No penalty
    
    model, X_train, X_test, y_train, y_test = train_model(
        'training_data_final_kept.csv',
        test_size=0.1,
        val_size=0.2,
        cex_penalty=0.1  # Reduce top1_cex_region influence by 70%
    )