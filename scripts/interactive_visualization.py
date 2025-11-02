# %%

import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip, GeoJsonPopup
from pathlib import Path

# Directories
data_dir = Path("../data_raw")
out_dir = Path("../data_processed")

# Load processed suitability data
merged = gpd.read_file(out_dir / "aquaculture_suitability_full.gpkg")

# Load infrastructure / CZMA / sanctuary layers
ports = gpd.read_file(data_dir / "ne_10m_ports.shp").to_crs(merged.crs)
czma = gpd.read_file(data_dir / "CoastalZoneManagementAct.gpkg").to_crs(merged.crs)
sanctuaries = gpd.read_file(data_dir / "NationalMarineSanctuary.gpkg").to_crs(merged.crs)
# %%

# Create base map
m = folium.Map(location=[39.5, -98.35], zoom_start=4, tiles="cartodbpositron")

# -----------------------------
# 1. Choropleth layer: Suitability Index
# -----------------------------
folium.Choropleth(
    geo_data=merged,
    name="Suitability Index",
    data=merged,
    columns=["state", "SuitabilityIndex"],
    key_on="feature.properties.state",
    fill_color="YlGnBu",
    fill_opacity=0.7,
    line_opacity=0.5,
    legend_name="Aquaculture Suitability Index"
).add_to(m)

# Hover tooltip for states
tooltip_fields = ["state", "SuitabilityIndex",
                  "EnvQuality_norm", "perm_norm",
                  "total_sales_$1000_norm", "program_norm",
                  "OpenCoast_norm", "port_norm"]

tooltip = GeoJsonTooltip(
    fields=tooltip_fields,
    aliases=["State:", "Suitability Index:",
             "Environmental Quality:", "Regulatory Score:",
             "Product Value:", "Program Density:",
             "Open Coast Area:", "Port Accessibility:"],
    localize=True,
    sticky=True,
    labels=True,
    style=("background-color: white; color: #333; font-family: Arial; font-size: 12px; padding: 5px;")
)

folium.GeoJson(
    merged,
    style_function=lambda x: {"fillColor": "#transparent", "color": "black", "weight": 0.5},
    tooltip=tooltip
).add_to(m)

# -----------------------------
# 2. Ports as clickable markers
# -----------------------------
for _, row in ports.iterrows():
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=4,
        color="red",
        fill=True,
        fill_opacity=0.7,
        popup=folium.Popup(f"Port: {row.get('name', 'Unknown')}", parse_html=True)
    ).add_to(m)

# -----------------------------
# 3. CZMA boundaries (transparent overlay)
# -----------------------------
folium.GeoJson(
    czma,
    name="CZMA Boundaries",
    style_function=lambda x: {"fillColor": "#1f77b4", "color": "#1f77b4", "weight": 1, "fillOpacity": 0.1},
    tooltip=GeoJsonTooltip(fields=["CZMADomain"], aliases=["CZMA Domain:"])
).add_to(m)

# -----------------------------
# 4. Marine Sanctuaries overlay
# -----------------------------
folium.GeoJson(
    sanctuaries,
    name="Marine Sanctuaries",
    style_function=lambda x: {"fillColor": "#ff7f0e", "color": "#ff7f0e", "weight": 1, "fillOpacity": 0.2},
    tooltip=GeoJsonTooltip(fields=["siteName"], aliases=["Sanctuary:"])
).add_to(m)

# -----------------------------
# Layer control
# -----------------------------
folium.LayerControl().add_to(m)

# -----------------------------
# Save interactive map
# -----------------------------
m.save(out_dir / "aquaculture_suitability_dashboard.html")
print("Interactive dashboard saved as aquaculture_suitability_dashboard.html")

# %%
