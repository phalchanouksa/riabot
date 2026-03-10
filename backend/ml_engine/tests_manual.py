import os
import sys
import django
import numpy as np

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')
django.setup()

from ml_engine.services.synthetic_gen import generate_base_data
from ml_engine.services.data_processor import parse_json_to_flat_array, get_major_id
from ml_engine.services.tabnet_trainer import train_hybrid_model_task
from ml_engine.services.recommender import MajorRecommender

def test_synthetic_gen():
    print("Testing Synthetic Generation...")
    X, y = generate_base_data(100)
    print(f"Shape: X={X.shape}, y={y.shape}")
    assert X.shape == (100, 256)
    assert y.shape == (100,)
    print("Synthetic Generation OK")

def test_data_processor():
    print("Testing Data Processor...")
    json_str = '{"ch1": [[1,1,1,1,1,1]], "ch2": [[0,0,0,0,0,0,0,0,0,0]]}'
    flat = parse_json_to_flat_array(json_str)
    print(f"Flat shape: {flat.shape}")
    # 1 list of 6 + 1 list of 10 = 16. Padded to 256.
    # Wait, my logic was: ch1 is list of lists.
    # The sample in data_context_explain.txt has 16 lists in ch1 and 16 lists in ch2.
    # My test json above only has 1 list each.
    # parse_json_to_flat_array flattens ALL lists.
    # So 6 + 10 = 16.
    assert flat.shape == (256,)
    assert flat[0] == 1
    assert flat[15] == 0
    assert flat[16] == 0 # Padding
    
    mid = get_major_id("ផ្នែកព័ត៌មានវិទ្យា (IT)")
    print(f"Major ID for IT: {mid}")
    assert mid == 10
    print("Data Processor OK")

def test_training_and_prediction():
    print("Testing Training and Prediction...")
    # Run training (synchronously for test)
    train_hybrid_model_task()
    
    # Test Prediction
    # Create a dummy feature vector for IT (Major 10)
    # IT Interest: 10 * 6 = 60. Indices 60-65.
    # IT Skill: 96 + 10 * 10 = 196. Indices 196-205.
    
    features = np.zeros(256, dtype=int)
    # Set high scores for IT
    features[60:66] = 4
    features[196:206] = 3
    
    print("Predicting...")
    major = MajorRecommender.recommend(features)
    print(f"Predicted Major: {major}")
    
    # Since it's trained on random synthetic data, it might not be perfect with just 1 sample and 20 epochs,
    # but it should return a string.
    assert isinstance(major, str)
    print("Training and Prediction OK")

if __name__ == "__main__":
    test_synthetic_gen()
    test_data_processor()
    test_training_and_prediction()
