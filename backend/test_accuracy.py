import os
import csv
import json
import re
import requests

API_URL = "http://127.0.0.1:8000/api/ml/predict/"
DATA_FILE = "NEA_Assessment_Data - Sheet1.csv"

def extract_expected_major(khmer_major_string):
    """
    Extracts the English major name from strings like: 
    'ផ្នែកព័ត៌មានវិទ្យា (IT)' -> 'IT'
    """
    match = re.search(r'\((.*?)\)', khmer_major_string)
    if match:
        return match.group(1).strip()
    return khmer_major_string.strip()

def run_accuracy_test():
    if not os.path.exists(DATA_FILE):
        print(f"File {DATA_FILE} not found!")
        return

    print("=========================================================")
    print("🤖 STARTING FULL TABNET MODEL & API ACCURACY TEST")
    print("=========================================================\n")

    correct = 0
    total = 0

    with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_scores = row.get("Raw Scores")
            recommended = row.get("Recommended Major", "")
            
            if not raw_scores or not recommended:
                print(f"Skipping row for {row.get('Student Name', 'Unknown')}: Missing 'Raw Scores' or 'Recommended Major'")
                continue

            expected_major = extract_expected_major(recommended)
            
            # Parse the JSON string directly
            try:
                scores_data = json.loads(raw_scores)
            except json.JSONDecodeError as e:
                print(f"Skipping row for {row.get('Student Name', 'Unknown')}: JSON Decode Error - {e}")
                continue

            # Call the Django ML API
            try:
                response = requests.post(API_URL, json=scores_data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    predicted_major = result.get('major')
                    
                    total += 1
                    status = "❌ FAIL"
                    if predicted_major == expected_major:
                        correct += 1
                        status = "✅ PASS"
                        
                    print(f"Student: {row.get('Student Name', 'Unknown')}")
                    print(f"Expected: {expected_major.ljust(15)} | Predicted: {str(predicted_major).ljust(15)} | {status}")
                else:
                    print(f"API Error: HTTP {response.status_code}")
            except requests.exceptions.ConnectionError:
                print("Could not connect to Django API. Is the server running?")
                return

    if total > 0:
        accuracy = (correct / total) * 100
        print("\n=========================================================")
        print(f"📊 FINAL ACCURACY: {correct}/{total} ({accuracy:.2f}%)")
        if accuracy >= 70:
            print("🚀 The model is performing GREAT! (70%+ Requirement Met)")
        else:
            print("⚠️ The model is performing BELOW expectations.")
        print("=========================================================")
    else:
        print("No valid test data rows found.")

if __name__ == "__main__":
    run_accuracy_test()
