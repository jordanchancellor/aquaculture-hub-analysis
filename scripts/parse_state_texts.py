import re
import pandas as pd
import sys

# ---- USER PARAMETERS ----
REPORT_TYPE = sys.argv[1].lower()  # 'algae', 'finfish', or 'shellfish'
TEXT_FILE = sys.argv[2]            # input txt file
OUTPUT_CSV = TEXT_FILE.rsplit(".txt", 1)[0] + "_parsed.csv"

# ---- Load text ----
with open(TEXT_FILE, "r", encoding="utf-8") as f:
    text = f.read()

# ---- Full list of US states ----
ALL_US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma",
    "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee",
    "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

# ---- Determine section header based on report type ----
if REPORT_TYPE == 'algae':
    SECTION_HEADER = r'Summary of the Status of Algae Culture'
elif REPORT_TYPE == 'finfish':
    SECTION_HEADER = r'Summary of the Status of Finfish Culture'
elif REPORT_TYPE == 'shellfish':
    SECTION_HEADER = r'Special Notes'
else:
    raise ValueError("REPORT_TYPE must be 'algae', 'finfish', or 'shellfish'")

# ---- Find state sections ----
# Escape spaces in state names for regex
escaped_states = [re.escape(s) for s in ALL_US_STATES]
pattern = r'(?<=\n)(' + '|'.join(escaped_states) + r')\n' + SECTION_HEADER
matches = list(re.finditer(pattern, text))

# Map state -> section text
sections = {}
for i, m in enumerate(matches):
    start = m.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    state_name = m.group(1)
    sections[state_name] = text[start:end].strip()

# ---- Parse each state ----
parsed_data = []

for state in ALL_US_STATES:
    content = sections.get(state, "")
    if not content:
        parsed_data.append({
            "state": state,
            "aquaculture leasing/permitting law(s)": "N/A",
            "Application Fees": "N/A",
            "Lease Review/Approval Timeframe": "N/A"
        })
        continue

    lines = content.splitlines()
    law_value = "N/A"
    fee_value = "N/A"
    timeframe_value = "N/A"

    # ---- Laws ----
    law_idx = next((i for i, l in enumerate(lines) if re.search(r'leasing/permitting law\(s\):', l, re.I)), None)
    if law_idx is not None and law_idx + 1 < len(lines):
        next_line = lines[law_idx + 1].strip().lower()
        if "have not been developed" in next_line:
            law_value = "NO"
        else:
            law_value = "YES"

    # ---- Application Fees ----
    fee_idx = next((i for i, l in enumerate(lines) if "Application Fees" in l), None)
    if fee_idx is not None:
        next_20 = lines[fee_idx + 1: fee_idx + 21]
        fee_numbers = []
        for line in next_20:
            nums = re.findall(r'\$(\d[\d,\.]*)', line)
            for n in nums:
                fee_numbers.append(float(n.replace(",", "")))
        fee_value = sum(fee_numbers) if fee_numbers else "No"

    # ---- Lease Review/Approval Timeframe ----
    timeframe_idx = next((i for i, l in enumerate(lines) if "Lease Review/Approval Timeframe" in l), None)
    if timeframe_idx is not None:
        next_10 = lines[timeframe_idx + 1: timeframe_idx + 11]
        time_matches = []
        for line in next_10:
            matches_ = re.findall(r'(\d+\.?\d*)\s*(years|months)', line, re.I)
            time_matches.extend([f"{num} {unit}" for num, unit in matches_])
        if time_matches:
            timeframe_value = "; ".join(time_matches)

    parsed_data.append({
        "state": state,
        "aquaculture leasing/permitting law(s)": law_value,
        "Application Fees": fee_value,
        "Lease Review/Approval Timeframe": timeframe_value
    })

# ---- Save CSV ----
df = pd.DataFrame(parsed_data)
df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Parsed all {len(df)} states. Saved to {OUTPUT_CSV}")
