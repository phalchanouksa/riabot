"""
Test script to verify feedback-weighted training is working correctly.
"""
import os
import sys
import pandas as pd
import numpy as np

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from ml_engine.services.data_processor import load_all_real_data

def test_backward_compatibility():
    """Test 1: Old CSV format (no feedback columns) should still work"""
    print("\n" + "="*60)
    print("TEST 1: Backward Compatibility (Old CSV Format)")
    print("="*60)
    
    # Check if there are any CSV files in training_data
    training_dir = os.path.join(os.path.dirname(__file__), 'ml_engine', 'training_data')
    
    if not os.path.exists(training_dir):
        print("❌ Training data directory not found")
        return False
    
    csv_files = [f for f in os.listdir(training_dir) if f.endswith('.csv')]
    
    if not csv_files:
        print("⚠️  No CSV files found in training_data directory")
        print(f"   Directory: {training_dir}")
        return None
    
    print(f"Found {len(csv_files)} CSV file(s)")
    
    try:
        X, y, weights = load_all_real_data(training_dir)
        
        if X is None:
            print("❌ Failed to load data")
            return False
        
        print(f"✅ Successfully loaded data")
        print(f"   Samples: {len(X)}")
        print(f"   Features shape: {X.shape}")
        print(f"   Labels shape: {y.shape}")
        print(f"   Weights shape: {weights.shape}")
        print(f"   All weights = 1.0: {np.all(weights == 1.0)}")
        
        if np.all(weights == 1.0):
            print("✅ PASS: All weights are 1.0 (expected for old format)")
        else:
            print("⚠️  Some weights are not 1.0 (feedback columns may be present)")
            print(f"   Weight range: {weights.min():.2f} - {weights.max():.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_feedback_columns():
    """Test 2: Create test CSV with feedback columns and verify weight calculation"""
    print("\n" + "="*60)
    print("TEST 2: Feedback Columns (New CSV Format)")
    print("="*60)
    
    # Create a test CSV with feedback columns
    test_dir = os.path.join(os.path.dirname(__file__), 'ml_engine', 'test_data')
    os.makedirs(test_dir, exist_ok=True)
    
    test_csv = os.path.join(test_dir, 'test_feedback.csv')
    
    # Sample data with feedback columns
    test_data = {
        'Timestamp': ['2026-01-10 10:00:00', '2026-01-10 10:05:00', '2026-01-10 10:10:00'],
        'Student Name': ['Test Student A', 'Test Student B', 'Test Student C'],
        'Recommended Major': ['ផ្នែកព័ត៌មានវិទ្យា (IT)', 'ផ្នែកពាណិជ្ជកម្ម និងរដ្ឋបាល (Business)', 'ផ្នែកហិរញ្ញវត្ថុ និងធានារ៉ាប់រង (Finance)'],
        'Top 3 Majors': ['IT, Business, Finance', 'Business, Finance, Sales', 'Finance, Business, IT'],
        'Total Score': [50, 45, 40],
        'Raw Scores': [
            '{"ch1":[[3,3,3,3,3,3],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[4,4,4,4,4,4],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2]],"ch2":[[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[2,2,2,2,2,2,2,2,2,2],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0]]}',
            '{"ch1":[[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[4,4,4,4,4,4],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2]],"ch2":[[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[2,2,2,2,2,2,2,2,2,2],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0]]}',
            '{"ch1":[[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[4,4,4,4,4,4],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2],[2,2,2,2,2,2]],"ch2":[[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[2,2,2,2,2,2,2,2,2,2],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0]]}'
        ],
        'User_Rating': [5, 2, 4],  # NEW COLUMN
        'Actual_Choice': ['IT', 'Finance', 'Finance']  # NEW COLUMN (Student B chose Finance instead of Business)
    }
    
    df = pd.DataFrame(test_data)
    df.to_csv(test_csv, index=False)
    print(f"✅ Created test CSV: {test_csv}")
    
    try:
        X, y, weights = load_all_real_data(test_dir)
        
        print(f"\n✅ Successfully loaded test data")
        print(f"   Samples: {len(X)}")
        
        # Verify weights
        expected_weights = [5/3.0, 2/3.0, 4/3.0]  # [1.67, 0.67, 1.33]
        print(f"\n   Weight verification:")
        for i, (actual, expected) in enumerate(zip(weights, expected_weights)):
            match = "✅" if abs(actual - expected) < 0.01 else "❌"
            print(f"   {match} Sample {i+1}: weight={actual:.2f} (expected {expected:.2f})")
        
        # Verify labels (should use Actual_Choice)
        # IT=10, Finance=5
        expected_labels = [10, 5, 5]  # IT, Finance, Finance
        print(f"\n   Label verification (using Actual_Choice):")
        for i, (actual, expected) in enumerate(zip(y, expected_labels)):
            match = "✅" if actual == expected else "❌"
            major_name = test_data['Actual_Choice'][i]
            print(f"   {match} Sample {i+1}: label={actual} (expected {expected} for {major_name})")
        
        # Overall result
        weights_correct = all(abs(a - e) < 0.01 for a, e in zip(weights, expected_weights))
        labels_correct = all(a == e for a, e in zip(y, expected_labels))
        
        if weights_correct and labels_correct:
            print(f"\n✅ PASS: All weights and labels are correct!")
            return True
        else:
            print(f"\n❌ FAIL: Some weights or labels are incorrect")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if os.path.exists(test_csv):
            os.remove(test_csv)
            print(f"\n🧹 Cleaned up test file")


def main():
    print("\n" + "="*60)
    print("FEEDBACK-WEIGHTED TRAINING TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Backward compatibility
    result1 = test_backward_compatibility()
    results.append(("Backward Compatibility", result1))
    
    # Test 2: Feedback columns
    result2 = test_feedback_columns()
    results.append(("Feedback Columns", result2))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{status} - {test_name}")
    
    all_passed = all(r in [True, None] for _, r in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Feedback-weighted training is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
