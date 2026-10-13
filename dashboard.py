import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv
import numpy as np
import math


# Unlock the vault
load_dotenv()

# Streamlit uses specific commands to render text on the web page
st.set_page_config(page_title="Intelligent Gainesville Gas", layout="wide")
st.title("Gainesville Fuel & Opportunity Cost Optimizer")


# --- Live Benchmark Ingestion ---
# Data Tank || get request || converting the response to dictionary || Securely creating protected key
# Technically the API Key should be hidden but since this is a public key it can also act as a fallback value
api_key = os.getenv("EIA_API_KEY", "DEMO_KEY")
url = f"https://api.eia.gov/v2/petroleum/pri/gnd/data/?api_key={api_key}&frequency=weekly&data[0]=value&facets[series][]=EMM_EPM0_PTE_SFL_DPG&sort[0][column]=period&sort[0][direction]=desc&length=10"
# If the API isnt responding 4.07 will act as a sensible guess
benchmarkPriceRegular = 4.07 
# We use try to start parsing data
try:
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        raw_val = response.json()['response']['data'][0]['value']
        benchmarkPriceRegular = float(raw_val)
except Exception as e:
    # TODO: Fix silent failure. 'pass' hides network and parsing errors.
    # We should log the error and set a fallback benchmark_price here.
    pass

st.caption(f"State Benchmark Anchor (EIA): **${benchmarkPriceRegular:.2f}/gal**")


# --- Static GeoLocations of Stations & Market Simulation ---
# Saving are direclty assoisiated to what a typical member would get from that brand
#. the @ line is a steamlit quirk, instead of running each time a user interacts the @ tells it to freeze on current results to improve memory and keep it fast
@st.cache_data
def get_station_network(base_price):
    stations = [
        {"name": "Wawa (Archer Rd)", "lat": 29.6346, "lon": -82.3562, "offset": -0.05, "requires_membership": False},
        {"name": "Gate (Archer Rd)", "lat": 29.6358, "lon": -82.3721, "offset": 0.02, "requires_membership": False},
        {"name": "RaceTrac (13th St)", "lat": 29.6267, "lon": -82.3391, "offset": -0.08, "requires_membership": False},
        {"name": "Circle K (34th St)", "lat": 29.6198, "lon": -82.3728, "offset": 0.04, "requires_membership": False},
        {"name": "Sam's Club (Butler Plaza)", "lat": 29.6193, "lon": -82.3812, "offset": -0.22, "requires_membership": True},
        {"name": "Shell (Newberry Rd)", "lat": 29.6528, "lon": -82.4243, "offset": 0.09, "requires_membership": False},
    ]
    df = pd.DataFrame(stations)
    # Price is anchored to state benchmark with a station-specific spread
    df["price"] = (base_price + df["offset"]).round(2)
    return df

df_stations = get_station_network(benchmarkPriceRegular)


# --- Haversine Distance Function ---
def haversine(lat1, lon1, lat2, lon2):
    r = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


# --- Trip & VEHICLE TELEMETRY ---
st.sidebar.header("Trip & Vehicle Telemetry")
origin_choice = st.sidebar.selectbox(
    "Current Origin",
    ["UF Campus (Reitz Union)", "Midtown", "Oaks Mall", "Sorority Row"]
)

origin_coords = {
    "UF Campus (Reitz Union)": (29.6465, -82.3477),
    "Midtown": (29.6523, -82.3440),
    "Oaks Mall": (29.6558, -82.4277),
    "Sorority Row": (29.6428, -82.3382)
}
user_lat, user_lon = origin_coords[origin_choice]

vehicle_mpg = st.sidebar.number_input("Vehicle Fuel Economy (MPG)", min_value=10.0, max_value=60.0, value=25.0, step=1.0)
gallons_needed = st.sidebar.slider("Gallons Needed", min_value=1.0, max_value=30.0, value=12.0, step=0.5)
has_membership = st.sidebar.checkbox("I have a Sam's Club / Wholesale Membership", value=True)

# Filter out membership stations if user doesn't have one
eligible_stations = df_stations.copy()
if not has_membership:
    eligible_stations = eligible_stations[~eligible_stations["requires_membership"]]

# --- Opportunity Cost Engine ---
# Driving cost considers the round trip (2x distance)
eligible_stations["one_way_miles"] = eligible_stations.apply(
    lambda row: round(haversine(user_lat, user_lon, row["lat"], row["lon"]), 2), axis=1
)
eligible_stations["round_trip_miles"] = eligible_stations["one_way_miles"] * 2

# Fuel burned = (round trip miles / MPG) * benchmark price
eligible_stations["drive_cost"] = (
    (eligible_stations["round_trip_miles"] / vehicle_mpg) * benchmarkPriceRegular
).round(2)

# Fuel purchase cost at pump
eligible_stations["pump_total"] = (eligible_stations["price"] * gallons_needed).round(2)

# Total Net Out-of-Pocket Expense
eligible_stations["net_total_cost"] = (eligible_stations["pump_total"] + eligible_stations["drive_cost"]).round(2)

# Sort by absolute lowest net cost
ranked_df = eligible_stations.sort_values(by="net_total_cost").reset_index(drop=True)

best_station = ranked_df.iloc[0]
nearest_station = eligible_stations.sort_values(by="one_way_miles").iloc[0]

# --- Presentation ---
st.subheader("Optimal Dispatch Recommendation")
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric(
        label="Top Recommendation",
        value=best_station["name"],
        delta=f"${best_station['price']:.2f}/gal"
    )
with col_b:
    st.metric(
        label="Net Effective Cost (Pump + Drive)",
        value=f"${best_station['net_total_cost']:.2f}",
        delta=f"{best_station['one_way_miles']} mi away"
    )
with col_c:
    # Compare optimal vs nearest
    savings_vs_nearest = nearest_station["net_total_cost"] - best_station["net_total_cost"]
    st.metric(
        label="Net Savings vs Nearest Station",
        value=f"${savings_vs_nearest:.2f}",
        delta="Profitable Trip" if savings_vs_nearest > 0 else "Stay Local",
        delta_color="normal" if savings_vs_nearest > 0 else "off"
    )

# --- 7. COMPARISON TABLE & MAP ---
st.divider()
st.subheader("Economic Trade-off Matrix")

display_df = ranked_df[[
    "name", "price", "one_way_miles", "drive_cost", "pump_total", "net_total_cost"
]].rename(columns={
    "name": "Station",
    "price": "Pump Price ($/gal)",
    "one_way_miles": "Distance (mi)",
    "drive_cost": "Trip Cost ($)",
    "pump_total": "Gas Subtotal ($)",
    "net_total_cost": "Net Cost ($)"
})

st.dataframe(
    display_df,
    column_config={
        "Pump Price ($/gal)": st.column_config.NumberColumn(format="$%.2f"),
        "Distance (mi)": st.column_config.NumberColumn(format="%.1f mi"),
        "Trip Cost ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Gas Subtotal ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Net Cost ($)": st.column_config.NumberColumn(format="$%.2f"),
    },
    hide_index=True,
    use_container_width=True
)

st.subheader("Gainesville Station Geospatial Layout")
map_data = ranked_df[["lat", "lon"]].rename(columns={"lat": "latitude", "lon": "longitude"})
st.map(map_data)