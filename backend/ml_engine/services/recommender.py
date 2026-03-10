import os
import numpy as np
from pytorch_tabnet.tab_model import TabNetClassifier
import torch

class MajorRecommender:
    _model = None
    _model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saved_models', 'major_model.zip')

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls.load_model()
        return cls._model

    @classmethod
    def load_model(cls):
        if os.path.exists(cls._model_path):
            try:
                clf = TabNetClassifier()
                clf.load_model(cls._model_path)
                cls._model = clf
                print(f"Model loaded successfully from {cls._model_path}")
            except Exception as e:
                print(f"Failed to load model: {e}")
                cls._model = None
        else:
            print(f"Model file not found at {cls._model_path}")
            cls._model = None

    @classmethod
    def reload_model(cls):
        print("Reloading model...")
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

        # Ensure features is 2D array
        if isinstance(features, list):
            features = np.array([features])
        elif isinstance(features, np.ndarray) and features.ndim == 1:
            features = features.reshape(1, -1)

        try:
            prediction = model.predict(features)
            major_id = prediction[0]
            return cls.get_major_name(major_id)
        except Exception as e:
            print(f"Prediction error: {e}")
            return None

    @staticmethod
    def get_major_name(major_id):
        # Reverse mapping
        MAJOR_ID_TO_NAME = {
            0: "Agriculture",
            1: "Architecture",
            2: "Arts",
            3: "Business",
            4: "Education",
            5: "Finance",
            6: "Government",
            7: "Health",
            8: "Hospitality",
            9: "Human Services",
            10: "IT",
            11: "Law",
            12: "Manufacturing",
            13: "Sales",
            14: "Science",
            15: "Transport"
        }
        return MAJOR_ID_TO_NAME.get(int(major_id), "Unknown")
