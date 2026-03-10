import os
import numpy as np
import threading
from pytorch_tabnet.tab_model import TabNetClassifier
from .synthetic_gen import generate_base_data
from .data_processor import load_all_real_data
from .recommender import MajorRecommender

TRAINING_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'training_data')
SAVED_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saved_models')
MODEL_PATH = os.path.join(SAVED_MODELS_DIR, 'major_model.zip')

from pytorch_tabnet.callbacks import Callback

class TrainingState:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TrainingState, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance
    
    def reset(self):
        self.status = "IDLE" # IDLE, TRAINING, COMPLETED, ERROR
        self.current_epoch = 0
        self.total_epochs = 0
        self.logs = []
        self.metrics = {}
        
    def log(self, message):
        print(message)
        self.logs.append(message)
        # Keep only last 100 logs
        if len(self.logs) > 100:
            self.logs.pop(0)
            
    def set_status(self, status):
        self.status = status
        
    def update_progress(self, epoch, total):
        self.current_epoch = epoch
        self.total_epochs = total
        
    def to_dict(self):
        return {
            "status": self.status,
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "logs": self.logs,
            "metrics": self.metrics
        }

class StatusCallback(Callback):
    def __init__(self, state):
        self.state = state
        
    def on_epoch_end(self, epoch, logs=None):
        self.state.update_progress(epoch + 1, self.state.total_epochs)
        if logs:
            # Construct a detailed log message with all metrics
            parts = [f"Epoch {epoch + 1}"]
            for key, value in logs.items():
                if isinstance(value, float):
                    parts.append(f"{key}={value:.4f}")
                else:
                    parts.append(f"{key}={value}")
            
            self.state.log(", ".join(parts))
            self.state.metrics = logs

def train_hybrid_model_task(n_synthetic=5000, max_epochs=20, patience=5, batch_size=256):
    state = TrainingState()
    state.reset()
    state.set_status("TRAINING")
    state.log("Starting hybrid training task...")
    
    try:
        # 1. Load Synthetic Data (if needed)
        if n_synthetic > 0:
            state.log(f"Generating NEW synthetic data ({n_synthetic} samples)...")
            X_syn, y_syn = generate_base_data(n_samples=n_synthetic)
        else:
            state.log("Skipping synthetic data generation (n_synthetic=0).")
            X_syn, y_syn = None, None
        
        # 2. Load Real Data
        state.log(f"Loading real data from {TRAINING_DATA_DIR}...")
        X_real, y_real, weights_real = load_all_real_data(TRAINING_DATA_DIR)
        
        # 3. Merge (including weights)
        if X_real is not None and y_real is not None:
            if X_syn is not None and y_syn is not None:
                state.log(f"Merging {len(X_real)} real samples with {len(X_syn)} synthetic samples.")
                # Create default weights for synthetic data
                weights_syn = np.ones(len(X_syn))
                X_final = np.concatenate((X_syn, X_real), axis=0)
                y_final = np.concatenate((y_syn, y_real), axis=0)
                weights_final = np.concatenate((weights_syn, weights_real), axis=0)
            else:
                state.log(f"Using only real data ({len(X_real)} samples).")
                X_final = X_real
                y_final = y_real
                weights_final = weights_real
        elif X_syn is not None and y_syn is not None:
            state.log("No real data found. Using only synthetic data.")
            X_final = X_syn
            y_final = y_syn
            weights_final = np.ones(len(X_syn))  # All synthetic = weight 1.0
        else:
            raise ValueError("No training data available (both real and synthetic are empty).")
            
        # Split into Train/Validation
        from sklearn.model_selection import train_test_split
        
        # Check if dataset is large enough for validation split
        n_samples = len(X_final)
        unique_classes = len(np.unique(y_final))
        
        # For very small datasets, skip validation to avoid split issues
        if n_samples < 20 or n_samples < unique_classes * 2:
            state.log(f"Dataset too small ({n_samples} samples, {unique_classes} classes). Skipping validation split.")
            X_train = X_final
            y_train = y_final
            weights_train = weights_final
            X_valid = None
            y_valid = None
        else:
            # Use stratified split to ensure all classes appear in both sets
            try:
                X_train, X_valid, y_train, y_valid, weights_train, weights_valid = train_test_split(
                    X_final, y_final, weights_final,
                    test_size=0.2, 
                    random_state=42,
                    stratify=y_final  # Ensures class distribution is maintained
                )
                state.log(f"Training on {len(X_train)} samples, Validating on {len(X_valid)} samples.")
            except ValueError as e:
                # If stratification fails (e.g., some class has only 1 sample)
                state.log(f"Stratified split failed: {str(e)}. Using non-stratified split.")
                X_train, X_valid, y_train, y_valid, weights_train, weights_valid = train_test_split(
                    X_final, y_final, weights_final,
                    test_size=0.2, 
                    random_state=42
                )
                state.log(f"Training on {len(X_train)} samples, Validating on {len(X_valid)} samples.")

            
        # 4. Train
        state.log("Initializing TabNetClassifier...")
        clf = TabNetClassifier(verbose=0) # Disable default print
        
        state.log(f"Configuration: max_epochs={max_epochs}, patience={patience}, batch_size={batch_size}")
        state.log("Fitting model...")
        state.total_epochs = max_epochs
        
        # Prepare evaluation sets
        if X_valid is not None and y_valid is not None:
            eval_set = [(X_train, y_train), (X_valid, y_valid)]
            eval_name = ['train', 'valid']
        else:
            eval_set = [(X_train, y_train)]
            eval_name = ['train']
        
        clf.fit(
            X_train=X_train, y_train=y_train,
            weights=weights_train,  # Use sample weights
            eval_set=eval_set,
            eval_name=eval_name,
            eval_metric=['accuracy'],
            max_epochs=max_epochs,
            patience=patience,
            batch_size=batch_size, 
            virtual_batch_size=min(128, batch_size // 2),
            num_workers=0,
            drop_last=False,
            callbacks=[StatusCallback(state)]
        )
        
        # Check for Early Stopping
        actual_epochs_run = len(clf.history['loss'])
        if clf.best_epoch < (max_epochs - 1):
            state.log("Early stopping activated")
            state.log(f"Training stopped at epoch {actual_epochs_run} of {max_epochs}")
            state.log(f"No improvement for {patience} consecutive epochs")
            state.log(f"Best model at epoch {clf.best_epoch + 1}")
            
            # Get metrics if available
            try:
                if 'valid_accuracy' in clf.history and len(clf.history['valid_accuracy']) > clf.best_epoch:
                    best_val_acc = clf.history['valid_accuracy'][clf.best_epoch]
                    state.log(f"Best validation accuracy: {best_val_acc:.4f} ({best_val_acc*100:.2f}%)")
                elif 'train_accuracy' in clf.history and len(clf.history['train_accuracy']) > clf.best_epoch:
                    best_train_acc = clf.history['train_accuracy'][clf.best_epoch]
                    state.log(f"Best training accuracy: {best_train_acc:.4f} ({best_train_acc*100:.2f}%)")
            except (KeyError, IndexError, TypeError):
                pass
        else:
            state.log("Training completed all epochs")
        
        # 5. Evaluation
        if X_valid is not None and y_valid is not None:
            state.log("Calculating detailed evaluation metrics...")
            from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
            
            # Predictions
            y_pred = clf.predict(X_valid)
            y_prob = clf.predict_proba(X_valid)
            
            # 1. Classification Report & Confusion Matrix
            report = classification_report(y_valid, y_pred, output_dict=True, zero_division=0)
            cm = confusion_matrix(y_valid, y_pred).tolist()
            
            # 2. Top-k Accuracy (Top-3)
            top_k = 3
            top_k_hits = 0
            for i in range(len(y_valid)):
                # Get indices of top k probabilities
                top_indices = np.argsort(y_prob[i])[-top_k:]
                if y_valid[i] in top_indices:
                    top_k_hits += 1
            top_k_acc = top_k_hits / len(y_valid)
            
            # Store in state
            state.metrics['evaluation'] = {
                'confusion_matrix': cm,
                'classification_report': report,
                'top_k_accuracy': top_k_acc,
                'test_accuracy': accuracy_score(y_valid, y_pred)
            }
            state.log(f"Evaluation complete. Top-3 Accuracy: {top_k_acc:.4f}")

        # 6. Save
        if not os.path.exists(SAVED_MODELS_DIR):
            os.makedirs(SAVED_MODELS_DIR)
            
        # Generate timestamped filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f"model_{timestamp}.zip"
        save_path_no_ext = os.path.join(SAVED_MODELS_DIR, f"model_{timestamp}")
        
        # Save the versioned model
        clf.save_model(save_path_no_ext)
        state.log(f"Model saved to {model_filename}")
        
        # Register and Activate
        from .model_manager import ModelManager, ACTIVE_MODEL_PATH
        
        # Prepare metrics for registry
        metrics_to_save = state.metrics.get('evaluation', {})
        if not metrics_to_save and 'valid_accuracy' in clf.history:
             metrics_to_save = {'test_accuracy': clf.history['valid_accuracy'][-1]}
             
        config = {
            'max_epochs': max_epochs,
            'patience': patience,
            'batch_size': batch_size,
            'n_synthetic': n_synthetic
        }
        
        ModelManager.register_model(model_filename, metrics_to_save, config)
        
        # Copy to active path (major_model.zip)
        import shutil
        shutil.copy2(save_path_no_ext + '.zip', ACTIVE_MODEL_PATH)
        state.log(f"Model activated as {os.path.basename(ACTIVE_MODEL_PATH)}")
        
        # 7. Reload
        MajorRecommender.reload_model()
        state.log("Training complete and model reloaded.")
        state.set_status("COMPLETED")
        
    except Exception as e:
        state.log(f"Error during training: {str(e)}")
        state.set_status("ERROR")

def start_training(n_synthetic=5000, max_epochs=20, patience=5, batch_size=256):
    """
    Dispatch training to Celery worker (production) or fall back to threading (dev).
    Returns a dict with dispatch info.
    """
    # Check if already training
    state = TrainingState()
    if state.status == "TRAINING":
        return None

    # Try Celery first (production-safe)
    try:
        from ml_engine.tasks import train_model_task
        result = train_model_task.delay(
            n_synthetic=n_synthetic,
            max_epochs=max_epochs,
            patience=patience,
            batch_size=batch_size
        )
        return {"dispatch": "celery", "task_id": result.id}
    except Exception as e:
        # Celery/Redis not available — fall back to thread (dev mode)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Celery unavailable ({e}), falling back to threading.")
        
        thread = threading.Thread(
            target=train_hybrid_model_task,
            args=(n_synthetic, max_epochs, patience, batch_size)
        )
        thread.start()
        return {"dispatch": "thread"}


# Backward-compatible alias
start_training_thread = start_training
