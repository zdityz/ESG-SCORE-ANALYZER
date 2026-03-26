import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
import joblib

# --- 1. CONFIGURATION: INDIAN SECTORS ---
# 0: IT/Services (Low Energy)
# 1: Manufacturing/Auto (High Energy)
# 2: Retail/FMCG (Medium Energy)
# 3: Cement/Steel (Very High Energy)
# 4: Pharma/Chemicals (High Energy + Water)
SECTOR_MAP = {0: 0.2, 1: 2.5, 2: 0.8, 3: 5.0, 4: 3.0}

# --- 2. GENERATE SYNTHETIC DATA ---
np.random.seed(42)
n_samples = 5000 

data = {
    'revenue': np.random.randint(5000000, 1000000000, n_samples), # 50L to 100Cr
    'employees': np.random.randint(5, 2000, n_samples),
    'industry_type': np.random.choice(list(SECTOR_MAP.keys()), n_samples)
}

df = pd.DataFrame(data)

# --- 3. PHYSICS SIMULATION WITH REALISTIC OUTLIERS ---
def calculate_energy(row):
    sector_factor = SECTOR_MAP[row['industry_type']]
    
    # Base load from machines (Revenue) + People (Employees)
    revenue_load = (row['revenue'] * 0.0015 * sector_factor)
    employee_load = (row['employees'] * 1500) 
    
    base_energy = revenue_load + employee_load
    
    # --- ADD REALISM (Outliers) ---
    rand_val = np.random.random()
    
    if rand_val < 0.10: 
        # "Bad Apple" (10% chance): Old machinery, waste, inefficient
        # Uses 40-80% MORE energy than necessary
        inefficiency_factor = np.random.uniform(1.4, 1.8)
        final_energy = base_energy * inefficiency_factor
        
    elif rand_val > 0.95:
        # "Green Leader" (5% chance): Solar, LED, highly optimized
        # Uses 20-40% LESS energy
        efficiency_factor = np.random.uniform(0.6, 0.8)
        final_energy = base_energy * efficiency_factor
        
    else:
        # "Standard Company" (85% chance): Normal variation (+/- 10%)
        noise = np.random.normal(0, base_energy * 0.1)
        final_energy = base_energy + noise

    return max(1000, final_energy)

df['energy_usage'] = df.apply(calculate_energy, axis=1)

# --- 4. TRAIN MODEL ---
X = df[['revenue', 'employees', 'industry_type']]
y = df['energy_usage']

print(f"Training Gradient Boosting Model on {n_samples} companies...")
# Note: Gradient Boosting is robust to outliers, but we want it to learn the "General Trend"
# so it can spot the bad apples later.
model = GradientBoostingRegressor(n_estimators=200, learning_rate=0.1, max_depth=3, random_state=42)
model.fit(X, y)

joblib.dump(model, 'esg_benchmark_model.pkl')
print("✅ Advanced AI Model (with Outlier Training) saved as 'esg_benchmark_model.pkl'")