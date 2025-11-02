import pandas as pd
import re
import sys
import numpy as np

CSV_INPUT = sys.argv[1]
CSV_OUTPUT = CSV_INPUT.rsplit(".csv", 1)[0] + "_scored.csv"

# Weights for each category
WEIGHTS = {
    "laws_norm": 0.2,
    "fees_norm": 0.4,
    "time_norm": 0.4
}

df = pd.read_csv(CSV_INPUT)

# --- Convert fields to numeric ---

def parse_laws(value):
    if pd.isna(value):
        return None
    value_str = str(value).strip().lower()
    if value_str == "yes":
        return 1
    elif value_str == "no":
        return 0
    else:
        return None

def parse_fees(value):
    if pd.isna(value) or str(value).strip().upper() in ["N/A", "No"]:
        return None
    
    # Convert to string, split by newlines, extract numbers
    nums = re.findall(r"\d+", str(value))
    nums_int = [int(n) for n in nums]
    return sum(nums_int) if nums_int else 0

def parse_timeframe(value):
    if pd.isna(value) or str(value).strip().upper() == "N/A":
        return None
    months_total = 0
    for match in re.findall(r"(\d+(?:\.\d+)?)\s*(years|year|months|month)", str(value), flags=re.IGNORECASE):
        num, unit = match
        num = float(num)
        if "year" in unit.lower():
            months_total += num * 12
        else:
            months_total += num
    return months_total if months_total > 0 else None

# Apply parsing
df["laws_numeric"] = df["aquaculture leasing/permitting law(s)"].apply(parse_laws)
df["fees_numeric"] = df["Application Fees"].apply(parse_fees)
df["time_numeric"] = df["Lease Review/Approval Timeframe"].apply(parse_timeframe)

# Normalize function
def normalize(series):
    valid = series.dropna()
    if valid.empty:
        return series
    min_val = valid.min()
    max_val = valid.max()
    if min_val == max_val:
        return series.apply(lambda x: 1 if pd.notna(x) else np.nan)
    return series.apply(lambda x: (x - min_val) / (max_val - min_val) if pd.notna(x) else np.nan)

# --- Normalize ---
df["laws_norm"] = df["laws_numeric"]  # 0 or 1
df["fees_norm"] = normalize(df["fees_numeric"])
df["time_norm"] = normalize(df["time_numeric"])

# --- Compute weighted score ---
def compute_score(row):
    # If all values are missing, return N/A
    if pd.isna(row["laws_norm"]) and pd.isna(row["fees_norm"]) and pd.isna(row["time_norm"]):
        return "N/A"
    
    score = 0
    total_weight = 0
    for col, weight in WEIGHTS.items():
        val = row.get(col)
        if pd.notna(val):
            score += val * weight
            total_weight += weight
    if total_weight == 0:
        return "N/A"
    return score / total_weight

df["regulatory_access_score"] = df.apply(compute_score, axis=1)

df.to_csv(CSV_OUTPUT, index=False)
print(f"✅ Processed '{CSV_INPUT}', saved scored data to '{CSV_OUTPUT}'")
