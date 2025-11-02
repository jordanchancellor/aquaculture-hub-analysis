# ================================================================
# 02_full_pipeline.py
# National Aquaculture Suitability Analysis (U.S.)
# ================================================================
# Author: Jordan Chancellor
# Purpose: Combine regulatory, environmental, economic, and infrastructure
#          datasets into a composite Aquaculture Suitability Index
# ================================================================
# %%

import os
from pathlib import Path
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# ------------------------------------------------
# 1. File paths
# ------------------------------------------------
data_dir = Path("../data_raw")
out_dir = Path("../data_processed")
out_dir.mkdir(exist_ok=True)
# %%

# ------------------------------------------------
# 2. Load base spatial layer (U.S. states)
# ------------------------------------------------
states = gpd.read_file(data_dir / "us_states.geojson")
states = states.rename(columns={"NAME": "state", "name": "state"})
states = states[["state", "geometry"]]
states['state'] = states['state'].str.title().str.strip()
# %%

# ------------------------------------------------
# 3. Load NOAA regulatory accessibility data
# ------------------------------------------------
finfish = pd.read_csv(data_dir / "Report-State-by-State-Summary-of-Finfish-Aquaculture-Leasing-Permitting-Requirements-2021_parsed_scored.csv")
shellfish = pd.read_csv(data_dir / "Report-State-by-State-Summary-of-Shellfish-Aquaculture-Leasing-Permitting-Requirements-2021_parsed_scored.csv")
seaweed = pd.read_csv(data_dir / "Report-State-by-State-Summary-of-Seaweed-Aquaculture-Leasing-Permitting-Requirements-2021_parsed_scored.csv")

perm_df = pd.concat([
    finfish[["state", "regulatory_access_score"]],
    shellfish[["state", "regulatory_access_score"]],
    seaweed[["state", "regulatory_access_score"]]
])

perm_mean = perm_df.groupby("state", as_index=False)["regulatory_access_score"].mean()
perm_mean['perm_norm'] = (perm_mean['regulatory_access_score'] - perm_mean['regulatory_access_score'].min()) / \
                         (perm_mean['regulatory_access_score'].max() - perm_mean['regulatory_access_score'].min())
# %%
# ------------------------------------------------
# 4. Load industry / production data (USDA & ERS)
# ------------------------------------------------
prod_acres = pd.read_csv(data_dir / "aquaculture_production_acres.csv")
prod_value = pd.read_csv(data_dir / "aquaculture_product_value.csv")
prod_farms = pd.read_csv(data_dir / "aquaculture-farms-in-the-united-states-2023.csv")
prod_sales = pd.read_csv(data_dir / "aquaculture-sales-in-the-united-states-2023.csv")

for df in [prod_acres, prod_value, prod_farms, prod_sales]:
    # Standardize column names
    df.columns = [c.lower().strip() for c in df.columns]
    
    # Ensure there is a 'state' column
    if "state" not in df.columns:
        df.rename(columns={df.columns[0]: "state"}, inplace=True)
    
    # Convert all numeric columns to floats and normalize safely
    for c in df.columns:
        if c != "state":
            df[c] = pd.to_numeric(df[c], errors='coerce')  # convert non-numeric to NaN
            # Handle case where min=max to avoid division by zero
            if df[c].max() != df[c].min():
                df[c + "_norm"] = (df[c] - df[c].min()) / (df[c].max() - df[c].min())
            else:
                df[c + "_norm"] = 0  # or 1, depending on how you want to handle this
# %%
# ------------------------------------------------
# 5. Load education / workforce data (IPEDS)
# ------------------------------------------------
programs = pd.read_csv(data_dir / "aquaculture_programs.csv")
if "state" in programs.columns:
    program_density = programs.groupby("state", as_index=False).size()
    program_density.columns = ["state", "program_count"]
else:
    program_density = pd.DataFrame(columns=["state", "program_count"])

program_density['program_norm'] = (program_density['program_count'] - program_density['program_count'].min()) / \
                                  (program_density['program_count'].max() - program_density['program_count'].min())
# %%

# ------------------------------------------------
# 6. Environmental quality (NFHAP)
# ------------------------------------------------
nfhap = gpd.read_file(data_dir / "nfhap_coastal_final_Pwm.shp")
nfhap = nfhap.assign(STATES=nfhap['STATES'].str.split())
nfhap = nfhap.explode('STATES', ignore_index=True)

state_env = nfhap.groupby('STATES', as_index=False)['NFHAP_SCOR'].mean()

us_state_abbrev = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming'
}

state_env['state'] = state_env['STATES'].map(us_state_abbrev)
state_env.rename(columns={'NFHAP_SCOR': 'EnvQualityIndex'}, inplace=True)
state_env['EnvQuality_norm'] = (state_env['EnvQualityIndex'] - state_env['EnvQualityIndex'].min()) / \
                               (state_env['EnvQualityIndex'].max() - state_env['EnvQualityIndex'].min())
# %%
# ------------------------------------------------
# 7. Marine protected areas & coastal zone overlap (robust)
# ------------------------------------------------
# Load layers
czma = gpd.read_file(data_dir / "CoastalZoneManagementAct.gpkg").to_crs(states.crs)
sanctuaries = gpd.read_file(data_dir / "NationalMarineSanctuary.gpkg").to_crs(states.crs)

# Attach state info via spatial join
czma = gpd.sjoin(czma, states[['state', 'geometry']], how='left', predicate='intersects')
sanctuaries = gpd.sjoin(sanctuaries, states[['state', 'geometry']], how='left', predicate='intersects')

# Compute area in km²
czma['czma_area_km2'] = czma.geometry.area / 1e6
sanctuaries['sanctuary_area_km2'] = sanctuaries.geometry.area / 1e6

# Aggregate area per state
czma_area_state = czma.groupby('state', as_index=False)['czma_area_km2'].sum()
sanctuary_area_state = sanctuaries.groupby('state', as_index=False)['sanctuary_area_km2'].sum()

# Compute open coastal area = CZMA area - sanctuary area
open_coast = czma_area_state.merge(sanctuary_area_state, on='state', how='left')
open_coast['sanctuary_area_km2'] = open_coast['sanctuary_area_km2'].fillna(0)
open_coast['OpenCoast_km2'] = open_coast['czma_area_km2'] - open_coast['sanctuary_area_km2']

# Normalize OpenCoast
if open_coast['OpenCoast_km2'].max() != open_coast['OpenCoast_km2'].min():
    open_coast['OpenCoast_norm'] = (
        open_coast['OpenCoast_km2'] - open_coast['OpenCoast_km2'].min()
    ) / (
        open_coast['OpenCoast_km2'].max() - open_coast['OpenCoast_km2'].min()
    )
else:
    open_coast['OpenCoast_norm'] = 0

# Keep only relevant columns for merging
open_coast = open_coast[['state', 'OpenCoast_km2', 'OpenCoast_norm']]

# %%

# ------------------------------------------------
# 8. Port accessibility (infrastructure)
# ------------------------------------------------
ports = gpd.read_file(data_dir / "ne_10m_ports.shp").to_crs(states.crs)
ports_in_states = gpd.sjoin(ports, states, how='inner', predicate='within')
port_counts = ports_in_states.groupby('state', as_index=False).size()
port_counts.columns = ['state', 'port_count']
port_counts['port_norm'] = (port_counts['port_count'] - port_counts['port_count'].min()) / \
                           (port_counts['port_count'].max() - port_counts['port_count'].min())
# %%

# ------------------------------------------------
# 9. Merge all datasets
# ------------------------------------------------
merged = (
    states
    .merge(state_env[['state', 'EnvQuality_norm']], on='state', how='left')
    .merge(perm_mean[['state', 'perm_norm']], on='state', how='left')
    .merge(prod_farms[['state', 'number of aquaculture farms (2023)_norm']], on='state', how='left')
    .merge(prod_value[['state', 'total_sales_$1000_norm']], on='state', how='left')
    .merge(prod_acres[['state', 'total_acres_saltwater_norm']], on='state', how='left')
    .merge(program_density[['state', 'program_norm']], on='state', how='left')
    .merge(open_coast[['state', 'OpenCoast_norm']], on='state', how='left')
    .merge(port_counts[['state', 'port_norm']], on='state', how='left')
)
# %%

# ------------------------------------------------
# 10. Compute composite Aquaculture Suitability Index
# ------------------------------------------------
merged['SuitabilityIndex'] = (
    0.25 * merged['EnvQuality_norm'] +
    0.20 * merged['perm_norm'] +
    0.20 * merged['total_sales_$1000_norm'] +
    0.15 * merged['program_norm'] +
    0.10 * merged['OpenCoast_norm'] +
    0.10 * merged['port_norm']
)
# %%

# ------------------------------------------------
# 11. Save outputs
# ------------------------------------------------
merged.to_file(out_dir / "aquaculture_suitability_full.gpkg", driver="GPKG")
merged.drop(columns='geometry').to_csv(out_dir / "aquaculture_suitability_full.csv", index=False)
# %%

# ------------------------------------------------
# 12. Quick visualization
# ------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 8))
merged.plot(
    column='SuitabilityIndex',
    cmap='YlGnBu',
    legend=True,
    edgecolor='gray',
    linewidth=0.5,
    ax=ax
)
ax.set_title("Composite Aquaculture Suitability Index by State", fontsize=14)
ax.axis('off')
plt.tight_layout()
plt.show()
# %%
