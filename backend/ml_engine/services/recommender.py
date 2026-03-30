import os
import json
import numpy as np
from pytorch_tabnet.tab_model import TabNetClassifier

# Full 16-major name lookup (original IDs, never changes)
ALL_MAJOR_NAMES = {
    0: "Agriculture",   1: "Architecture",  2: "Arts",          3: "Business",
    4: "Education",     5: "Finance",       6: "Government",    7: "Health",
    8: "Hospitality",   9: "Human Services",10: "IT",           11: "Law",
    12: "Manufacturing",13: "Sales",        14: "Science",      15: "Transport",
}

class MajorRecommender:
    _model = None
    _model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saved_models', 'major_model.zip')
    _config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saved_models', 'major_config.json')

    # class_to_major_id: maps model output class index → original major ID
    # e.g., if only majors [0,2,10] were trained: {0:0, 1:2, 2:10}
    _class_to_major_id: dict = {}

    @classmethod
    def _load_class_mapping(cls):
        """Load enabled_majors from config and build class→major_id mapping."""
        try:
            if os.path.exists(cls._config_path):
                with open(cls._config_path, 'r') as f:
                    data = json.load(f)
                    enabled = sorted(data.get("enabled_majors", list(range(16))))
                    cls._class_to_major_id = {idx: mid for idx, mid in enumerate(enabled)}
                    return
        except Exception as e:
            print(f"Warning: Could not load major_config.json: {e}")
        # Fallback: assume all 16 majors (identity mapping)
        cls._class_to_major_id = {i: i for i in range(16)}

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls.load_model()
        return cls._model

    @classmethod
    def load_model(cls):
        cls._load_class_mapping()
        if os.path.exists(cls._model_path):
            try:
                clf = TabNetClassifier()
                clf.load_model(cls._model_path)
                cls._model = clf
                print(f"Model loaded successfully from {cls._model_path}")
                print(f"Enabled majors mapping: {cls._class_to_major_id}")
            except Exception as e:
                print(f"Failed to load model: {e}")
                cls._model = None
        else:
            print(f"Model file not found at {cls._model_path}")
            cls._model = None

    @classmethod
    def reload_model(cls):
        print("Reloading model...")
        cls._model = None
        cls.load_model()

    @classmethod
    def recommend(cls, features):
        """
        Predicts the major based on features.
        features: list or numpy array of 256 integers.
        Returns: Major Name (string) or None if model not loaded.
        """
        model = cls.get_model()
        if model is None:
            return None

        if isinstance(features, list):
            features = np.array([features])
        elif isinstance(features, np.ndarray) and features.ndim == 1:
            features = features.reshape(1, -1)

        try:
            prediction = model.predict(features)
            class_idx = prediction[0]
            return cls.get_major_name(class_idx)
        except Exception as e:
            print(f"Prediction error: {e}")
            return None

    @classmethod
    def get_major_name(cls, class_idx: int) -> str:
        """Convert model output class index → human-readable major name."""
        if not cls._class_to_major_id:
            cls._load_class_mapping()
        original_id = cls._class_to_major_id.get(int(class_idx), int(class_idx))
        return ALL_MAJOR_NAMES.get(original_id, f"Major {original_id}")

    @classmethod
    def get_original_major_id(cls, class_idx: int) -> int:
        """Convert model class index → original 0-15 major ID."""
        if not cls._class_to_major_id:
            cls._load_class_mapping()
        return cls._class_to_major_id.get(int(class_idx), int(class_idx))

    @classmethod
    def get_enabled_majors(cls) -> list:
        """Return list of enabled original major IDs."""
        if not cls._class_to_major_id:
            cls._load_class_mapping()
        return sorted(cls._class_to_major_id.values())
