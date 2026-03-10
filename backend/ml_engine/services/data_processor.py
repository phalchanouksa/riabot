import json
import os
import pandas as pd
import numpy as np
import glob
import re

# Mapping based on data_context_explain.txt
MAJOR_KEYWORDS = {
    "Agriculture": 0,
    "Architecture": 1,
    "Arts": 2,
    "Business": 3,
    "Education": 4,
    "Finance": 5,
    "Government": 6,
    "Health": 7,
    "Hospitality": 8,
    "Human Services": 9,
    "IT": 10,
    "Law": 11,
    "Manufacturing": 12,
    "Sales": 13,
    "Science": 14,
    "Transport": 15
}

def get_major_id(major_string):
    """
    Extracts the major ID from the major string.
    Example: "ផ្នែកព័ត៌មានវិទ្យា (IT)" -> 10
    """
    if not isinstance(major_string, str):
        return -1
        
    for keyword, mid in MAJOR_KEYWORDS.items():
        if keyword in major_string:
            return mid
    return -1

def parse_json_to_flat_array(json_input):
    """
    Flattens the nested JSON structure into a 256-element array.
    Input can be a JSON string or a dict.
    Structure: {"ch1": [[...], ...], "ch2": [[...], ...]}
    """
    if isinstance(json_input, str):
        try:
            data = json.loads(json_input)
        except json.JSONDecodeError:
            return np.zeros(256, dtype=int)
    else:
        data = json_input

    if not data:
        return np.zeros(256, dtype=int)

    # Flatten ch1 (Interests)
    ch1 = data.get("ch1", [])
    ch1_flat = [item for sublist in ch1 for item in sublist]

    # Flatten ch2 (Skills)
    ch2 = data.get("ch2", [])
    ch2_flat = [item for sublist in ch2 for item in sublist]

    # Combine
    full_flat = ch1_flat + ch2_flat

    # Pad or truncate to 256
    if len(full_flat) < 256:
        full_flat.extend([0] * (256 - len(full_flat)))
    elif len(full_flat) > 256:
        full_flat = full_flat[:256]

    return np.array(full_flat, dtype=int)

def load_all_real_data(data_folder):
    """
    Iterates through all .csv files in the data_folder.
    Parses "Raw Scores" and "Recommended Major".
    
    Optional columns:
    - "Actual_Choice": If present, used as label instead of "Recommended Major"
    - "User_Rating": If present (1-5), converted to sample weight (0.33-1.67)
    
    Returns:
        X_real: Features array
        y_real: Labels array
        weights_real: Sample weights array (1.0 if no rating)
    """
    all_files = glob.glob(os.path.join(data_folder, "*.csv"))
    
    if not all_files:
        return None, None, None

    X_list = []
    y_list = []
    weights_list = []

    for filename in all_files:
        try:
            df = pd.read_csv(filename)
            
            # Check required columns
            if "Raw Scores" not in df.columns or "Recommended Major" not in df.columns:
                continue

            for _, row in df.iterrows():
                # Parse Features
                raw_scores = row["Raw Scores"]
                features = parse_json_to_flat_array(raw_scores)
                
                # Parse Label (prefer Actual_Choice if available)
                if "Actual_Choice" in df.columns and pd.notna(row["Actual_Choice"]):
                    major_str = row["Actual_Choice"]
                else:
                    major_str = row["Recommended Major"]
                
                label = get_major_id(major_str)
                
                # Calculate weight based on User_Rating
                weight = 1.0  # Default weight
                if "User_Rating" in df.columns and pd.notna(row["User_Rating"]):
                    try:
                        rating = float(row["User_Rating"])
                        # Normalize: 1-star=0.33, 3-star=1.0, 5-star=1.67
                        weight = rating / 3.0
                    except (ValueError, TypeError):
                        weight = 1.0  # Fallback to default if invalid
                
                if label != -1:
                    X_list.append(features)
                    y_list.append(label)
                    weights_list.append(weight)
                    
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

    if not X_list:
        return None, None, None

    return np.array(X_list), np.array(y_list), np.array(weights_list)

def validate_csv_format(file_obj):
    """
    Validates the uploaded CSV file format.
    Returns (True, None) if valid, or (False, error_message).
    """
    try:
        # Read first few lines to check headers and sample data
        # We don't want to read the whole file into memory if it's huge, 
        # but for validation we need to check headers at least.
        df = pd.read_csv(file_obj, nrows=5)
        
        required_columns = ["Timestamp", "Student Name", "Recommended Major", "Top 3 Majors", "Total Score", "Raw Scores"]
        
        # Check columns
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            return False, f"Missing columns: {', '.join(missing)}"
            
        # Check Raw Scores format for the first row
        if not df.empty:
            raw_scores = df.iloc[0]["Raw Scores"]
            try:
                data = json.loads(raw_scores)
                if "ch1" not in data or "ch2" not in data:
                    return False, "Invalid Raw Scores format: missing 'ch1' or 'ch2'"
            except json.JSONDecodeError:
                return False, "Invalid Raw Scores format: not valid JSON"
                
        # Reset file pointer
        file_obj.seek(0)
        return True, None
        
    except Exception as e:
        return False, f"CSV Validation Error: {str(e)}"
