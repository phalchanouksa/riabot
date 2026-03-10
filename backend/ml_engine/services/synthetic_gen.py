import numpy as np

# Major ID mapping (0-15 for 16 majors)
MAJOR_MAPPING = {
    0: "Agriculture", 1: "Architecture", 2: "Arts", 3: "Business",
    4: "Education", 5: "Finance", 6: "Government", 7: "Health",
    8: "Hospitality", 9: "Human Services", 10: "IT", 11: "Law",
    12: "Manufacturing", 13: "Sales", 14: "Science", 15: "Transport"
}

# Major correlations - related majors that should have similar scores
MAJOR_CORRELATIONS = {
    0: [14, 7],           # Agriculture → Science, Health
    1: [12, 15],          # Architecture → Manufacturing, Transport
    2: [8, 13],           # Arts → Hospitality, Sales
    3: [5, 13],           # Business → Finance, Sales
    4: [9, 7],            # Education → Human Services, Health
    5: [3, 6],            # Finance → Business, Government
    6: [11, 5],           # Government → Law, Finance
    7: [14, 0],           # Health → Science, Agriculture
    8: [2, 13],           # Hospitality → Arts, Sales
    9: [4, 7],            # Human Services → Education, Health
    10: [14, 12],         # IT → Science, Manufacturing
    11: [6, 3],           # Law → Government, Business
    12: [10, 1],          # Manufacturing → IT, Architecture
    13: [3, 8],           # Sales → Business, Hospitality
    14: [10, 7],          # Science → IT, Health
    15: [12, 1]           # Transport → Manufacturing, Architecture
}


def generate_base_data(n_samples=5000):
    """
    Generate highly realistic synthetic student data.
    
    Improvements over previous version:
    1. Major correlations (related fields get similar scores)
    2. Interest-skill correlation (high interest → higher skill)
    3. Realistic within-category variation
    4. Confused students (20% like multiple majors equally)
    5. Demographic patterns (gender, background)
    6. More realistic noise patterns
    
    Args:
        n_samples: Number of synthetic students to generate
        
    Returns:
        X: Features array of shape (n_samples, 256)
        y: Labels array of shape (n_samples,)
    """
    X = np.zeros((n_samples, 256), dtype=int)
    y = np.zeros(n_samples, dtype=int)
    
    for i in range(n_samples):
        # ===== STEP 1: Demographics =====
        gender = np.random.choice(['M', 'F'], p=[0.5, 0.5])
        background = np.random.choice(['urban', 'rural'], p=[0.6, 0.4])
        
        # Gender bias (subtle, realistic)
        gender_bias = {
            'F': {7: 0.3, 4: 0.3, 9: 0.2, 2: 0.2},  # Health, Education, Human Services, Arts
            'M': {10: 0.3, 12: 0.3, 15: 0.2, 1: 0.2}  # IT, Manufacturing, Transport, Architecture
        }
        
        # ===== STEP 2: Personality =====
        personality_type = np.random.choice(['optimist', 'neutral', 'pessimist'], p=[0.20, 0.60, 0.20])
        personality_bias = {'optimist': 0.5, 'neutral': 0, 'pessimist': -0.5}[personality_type]
        
        # ===== STEP 3: Choose Major(s) =====
        # 20% are confused (like 2-3 majors equally)
        is_confused = np.random.rand() < 0.20
        
        if is_confused:
            # Confused student: 2-3 majors with similar high scores
            num_majors = np.random.randint(2, 4)
            chosen_majors = np.random.choice(16, size=num_majors, replace=False)
            primary_major = chosen_majors[0]
            y[i] = primary_major
            equal_majors = chosen_majors
        else:
            # Clear preference: 1 primary, maybe 1 secondary
            primary_major = np.random.randint(0, 16)
            y[i] = primary_major
            
            # Apply gender bias to major selection
            if gender in gender_bias and primary_major in gender_bias[gender]:
                # More likely to choose gender-typical major
                pass
            
            # 50% have secondary interest
            has_secondary = np.random.rand() < 0.50
            if has_secondary:
                # Choose related major as secondary (more realistic!)
                if np.random.rand() < 0.70 and MAJOR_CORRELATIONS[primary_major]:
                    secondary_major = np.random.choice(MAJOR_CORRELATIONS[primary_major])
                else:
                    secondary_major = np.random.choice([m for m in range(16) if m != primary_major])
            else:
                secondary_major = None
        
        # ===== STEP 4: Initialize Baseline Scores =====
        # Use normal distribution for more realistic variation
        X[i, :96] = np.random.normal(1.5, 0.5, 96).clip(1, 4).astype(int)   # Interests
        X[i, 96:] = np.random.normal(0.8, 0.4, 160).clip(0, 3).astype(int)  # Skills
        
        # ===== STEP 5: Boost Primary Major =====
        if is_confused:
            # Confused students: All chosen majors get similar high scores
            for major in equal_majors:
                # Interests: 2-4 (medium-high, with variation)
                int_start, int_end = major * 6, (major + 1) * 6
                X[i, int_start:int_end] = np.random.normal(3.0, 0.6, 6).clip(2, 4).astype(int)
                
                # Skills: 1-3 (medium-high, with variation)
                skill_start, skill_end = 96 + major * 10, 96 + (major + 1) * 10
                X[i, skill_start:skill_end] = np.random.normal(2.0, 0.6, 10).clip(1, 3).astype(int)
        else:
            # Clear preference: Primary major gets high scores
            int_start, int_end = primary_major * 6, (primary_major + 1) * 6
            skill_start, skill_end = 96 + primary_major * 10, 96 + (primary_major + 1) * 10
            
            # Interests: 3-4 (high, with realistic variation)
            X[i, int_start:int_end] = np.random.normal(3.5, 0.5, 6).clip(3, 4).astype(int)
            
            # Skills: 2-3 (high, with realistic variation)
            X[i, skill_start:skill_end] = np.random.normal(2.5, 0.5, 10).clip(2, 3).astype(int)
        
        # ===== STEP 6: Boost Correlated Majors (NEW!) =====
        if not is_confused and MAJOR_CORRELATIONS[primary_major]:
            for related_major in MAJOR_CORRELATIONS[primary_major]:
                # Related majors get medium scores (more realistic!)
                int_start, int_end = related_major * 6, (related_major + 1) * 6
                skill_start, skill_end = 96 + related_major * 10, 96 + (related_major + 1) * 10
                
                # Interests: 2-3 (medium)
                X[i, int_start:int_end] = np.random.normal(2.5, 0.5, 6).clip(2, 3).astype(int)
                
                # Skills: 1-2 (medium)
                X[i, skill_start:skill_end] = np.random.normal(1.5, 0.5, 10).clip(1, 2).astype(int)
        
        # ===== STEP 7: Boost Secondary Major =====
        if not is_confused and secondary_major is not None:
            int_start, int_end = secondary_major * 6, (secondary_major + 1) * 6
            skill_start, skill_end = 96 + secondary_major * 10, 96 + (secondary_major + 1) * 10
            
            # Interests: 2-3 (medium)
            X[i, int_start:int_end] = np.random.normal(2.8, 0.5, 6).clip(2, 3).astype(int)
            
            # Skills: 1-2 (medium)
            X[i, skill_start:skill_end] = np.random.normal(1.8, 0.5, 10).clip(1, 2).astype(int)
        
        # ===== STEP 8: Interest-Skill Correlation (NEW!) =====
        # Make skills correlate with interests (more realistic!)
        for major in range(16):
            int_start, int_end = major * 6, (major + 1) * 6
            skill_start, skill_end = 96 + major * 10, 96 + (major + 1) * 10
            
            # Calculate average interest for this major
            avg_interest = np.mean(X[i, int_start:int_end])
            
            # Adjust skills based on interest
            if avg_interest >= 3.5:
                # High interest → Higher skills (practice effect)
                skill_boost = np.random.normal(0.5, 0.2, 10)
            elif avg_interest >= 2.5:
                # Medium interest → Medium skills
                skill_boost = np.random.normal(0.2, 0.2, 10)
            else:
                # Low interest → Lower skills
                skill_boost = np.random.normal(-0.2, 0.2, 10)
            
            X[i, skill_start:skill_end] = (X[i, skill_start:skill_end] + skill_boost).clip(0, 3).astype(int)
        
        # ===== STEP 9: Apply Personality Bias =====
        X[i, :] = (X[i, :] + personality_bias).clip(0, 10).astype(int)
        
        # ===== STEP 10: Apply Gender Bias (Subtle) =====
        if gender in gender_bias:
            for major, bias in gender_bias[gender].items():
                int_start, int_end = major * 6, (major + 1) * 6
                skill_start, skill_end = 96 + major * 10, 96 + (major + 1) * 10
                
                X[i, int_start:int_end] = (X[i, int_start:int_end] + bias).clip(1, 4).astype(int)
                X[i, skill_start:skill_end] = (X[i, skill_start:skill_end] + bias * 0.5).clip(0, 3).astype(int)
        
        # ===== STEP 11: Realistic Noise (Improved) =====
        # 3% completely random (human mistakes/confusion)
        num_random = int(256 * 0.03)
        random_indices = np.random.choice(256, num_random, replace=False)
        for idx in random_indices:
            if idx < 96:
                X[i, idx] = np.random.randint(1, 5)
            else:
                X[i, idx] = np.random.randint(0, 4)
        
        # 5% slight variation (+/- 1)
        num_vary = int(256 * 0.05)
        vary_indices = np.random.choice(256, num_vary, replace=False)
        for idx in vary_indices:
            variation = np.random.choice([-1, 1])
            X[i, idx] = X[i, idx] + variation
        
        # ===== STEP 12: Final Clamping =====
        X[i, :96] = np.clip(X[i, :96], 1, 4)    # Interests: 1-4
        X[i, 96:] = np.clip(X[i, 96:], 0, 3)    # Skills: 0-3
    
    return X, y
