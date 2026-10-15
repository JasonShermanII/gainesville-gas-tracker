import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv
import numpy as np
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
import datetime
import altair as alt



# Unlock the vault
load_dotenv()

# Streamlit uses specific commands to render text on the web page
st.set_page_config(page_title="Intelligent Gainesville Gas", layout="wide")
st.title("Gainesville Fuel & Opportunity Cost Optimizer")


# ==========================================
# 1. LIVE BENCHMARK INGESTION
# ==========================================
# Data Tank || get request || converting the response to dictionary || Securely creating protected key
# Technically the API Key should be hidden but since this is a public key it can also act as a fallback value
@st.cache_data(ttl=3600)  # Cache the data for 1 hour to prevent 429 rate limits
def fetch_eia_benchmark():
    api_key = os.getenv("EIA_API_KEY", "DEMO_KEY")
    url = f"https://api.eia.gov/v2/petroleum/pri/gnd/data/?api_key={api_key}&frequency=weekly&data[0]=value&facets[series][]=EMM_EPM0_PTE_SFL_DPG&sort[0][column]=period&sort[0][direction]=desc&length=10"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            raw_val = response.json()['response']['data'][0]['value']
            return float(raw_val), "Live EIA Data"
        else:
            return 4.07, f"EIA API Blocked ({response.status_code}) - Fallback Enabled"
    except Exception as e:
        return 4.07, "Connection Failed - Fallback Enabled"

# Unpack the cached results
benchmarkPriceRegular, api_status_msg = fetch_eia_benchmark()

st.caption(f"State Benchmark Anchor (EIA): **${benchmarkPriceRegular:.2f}/gal** ({api_status_msg})")



# ==========================================
# 2. FUNCTION DEFINITIONS 
# ==========================================
# Saving are direclty assoisiated to what a typical member would get from that brand
#. the @ line is a steamlit quirk, instead of running each time a user interacts the @ tells it to freeze on current results to improve memory and keep it fast
import datetime # Ensure this is at the top of the file

# Base Offset is the steryotyped tred "Oh station x is typically expensive" this is to give a more realistic simulated market.
@st.cache_data
def get_station_network(base_price):
    stations = [
        {"name": "Wawa (Archer Rd)", "lat": 29.6074, "lon": -82.3861, "base_offset": 0.05, "brand": "Wawa Rewards", "discount": 0.05, "club_only": False},
        {"name": "Wawa (NW 13th St)", "lat": 29.6734, "lon": -82.3390, "base_offset": 0.06, "brand": "Wawa Rewards", "discount": 0.05, "club_only": False},
        {"name": "Gate (Archer Rd)", "lat": 29.6358, "lon": -82.3721, "base_offset": 0.08, "brand": "My GATE Rewards", "discount": 0.03, "club_only": False},
        {"name": "Gate (NW 13th St)", "lat": 29.6803, "lon": -82.3390, "base_offset": 0.09, "brand": "My GATE Rewards", "discount": 0.03, "club_only": False},
        {"name": "Circle K (SW 34th St)", "lat": 29.6195, "lon": -82.3728, "base_offset": 0.04, "brand": "Inner Circle", "discount": 0.04, "club_only": False},
        {"name": "Circle K (SW 13th St)", "lat": 29.6152, "lon": -82.3391, "base_offset": 0.04, "brand": "Inner Circle", "discount": 0.04, "club_only": False},
        {"name": "Circle K (Williston Rd)", "lat": 29.5930, "lon": -82.3725, "base_offset": 0.05, "brand": "Inner Circle", "discount": 0.04, "club_only": False},
        {"name": "Chevron (SW Williston Rd)", "lat": 29.5936, "lon": -82.3725, "base_offset": 0.11, "brand": "Chevron Rewards", "discount": 0.03, "club_only": False},
        {"name": "Sam's Club (Butler Plaza)", "lat": 29.6193, "lon": -82.3812, "base_offset": -0.20, "brand": "Sam's Club", "discount": 0.0, "club_only": True},
        {"name": "Shell (W Newberry Rd)", "lat": 29.6533, "lon": -82.3827, "base_offset": 0.12, "brand": "Fuel Rewards (Shell)", "discount": 0.05, "club_only": False},
        {"name": "Texaco (NW 34th Blvd)", "lat": 29.6980, "lon": -82.3720, "base_offset": 0.10, "brand": "Texaco Rewards", "discount": 0.03, "club_only": False},
        {"name": "Texaco (SW 13th St)", "lat": 29.6335, "lon": -82.3391, "base_offset": 0.09, "brand": "Texaco Rewards", "discount": 0.03, "club_only": False},
        {"name": "Exxon (SW Archer Rd)", "lat": 29.6025, "lon": -82.3875, "base_offset": 0.08, "brand": "Exxon Mobil Rewards+", "discount": 0.03, "club_only": False},
        {"name": "Sunoco (SW 20th Ave)", "lat": 29.6338, "lon": -82.3926, "base_offset": 0.07, "brand": "Sunoco Go Rewards", "discount": 0.03, "club_only": False},
        {"name": "Sunoco (NW 13th St)", "lat": 29.6922, "lon": -82.3390, "base_offset": 0.08, "brand": "Sunoco Go Rewards", "discount": 0.03, "club_only": False}
    ]
    df = pd.DataFrame(stations)
    
    # Seed the random volatility so prices are stable for the day, but change tomorrow
    today_seed = datetime.date.today().toordinal()
    np.random.seed(today_seed)
    df["volatility"] = np.random.uniform(-0.06, 0.06, len(df))
    
    # Calculate Dual-Tier Pricing
    df["standard_price"] = (base_price + df["base_offset"] + df["volatility"]).round(2)
    df["member_price"] = (df["standard_price"] - df["discount"]).round(2)
    
    return df

# --- OSRM Routing Engine ---
# This @ saves it to remeber all available routes and load them instantiously rather than calculate every time
# Each location takes a longer period on first load up but after that its much faster
@st.cache_data(show_spinner=False)
# --- OSRM Routing Engine ---
@st.cache_data(show_spinner=False)
def get_real_drive_data(lat1, lon1, lat2, lon2):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    try:
        res = requests.get(url, timeout=5)
        data = res.json()
        if data.get("code") == "Ok":
            # Data is given in meters need to convert to miles
            miles = data["routes"][0]["distance"] / 1609.34
            mins = data["routes"][0]["duration"] / 60
            route_geometry = data["routes"][0]["geometry"]
            return round(miles, 2), round(mins), route_geometry
    except Exception:
        pass
    return None, None, None



# --- FOLIUM Minimap Renderer ---
# Note the new 'all_stations_df' parameter
def draw_minimap(user_lat, user_lon, station_lat, station_lon, geometry, station_name, all_stations_df):
    mid_lat = (user_lat + station_lat) / 2
    mid_lon = (user_lon + station_lon) / 2

    # TODO: Carto is very cool and has a lot of free features for projects and students BUT openstreetmap was an easier plug and go map. I want to try other projects with that.
    # Swapped to OpenStreetMap for a clean, watermark-free experience
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=13, tiles="OpenStreetMap")
    
    # Drop blue pin for user
    folium.Marker([user_lat, user_lon], tooltip="Your Location", icon=folium.Icon(color="blue", icon="user")).add_to(m)
    
    # Drop RED pins for every station on the board
    for index, row in all_stations_df.iterrows():
        if row["name"] != station_name:
            folium.Marker(
                [row["lat"], row["lon"]], 
                tooltip=f"{row['name']} - ${row['price']:.2f}", 
                icon=folium.Icon(color="red", icon="gas-pump", prefix="fa")
            ).add_to(m)
            
    # Drop GREEN pin for the recommended winner (drawn last so it sits on top)
    folium.Marker([station_lat, station_lon], tooltip=f"WINNER: {station_name}", icon=folium.Icon(color="green", icon="star")).add_to(m)
    
    # Draw the physical route line
    if geometry:
        folium.GeoJson(geometry, style_function=lambda x: {'color': '#3388ff', 'weight': 5, 'opacity': 0.8}).add_to(m)
        
    return m


# ==========================================
# 3. SIDEBAR: TRIP & VEHICLE TELEMETRY
# ==========================================
st.sidebar.header("Trip & Vehicle Telemetry")

# The Origin Mode Selector
origin_mode = st.sidebar.radio(
    "Origin Source",
    ["Campus Presets", "Live GPS", "Custom Coordinates"],
    horizontal=True
)

if origin_mode == "Live GPS":
    st.sidebar.caption("Click the crosshairs below to grant browser GPS access.")
    with st.sidebar:
        loc = streamlit_geolocation()
    if loc and loc.get('latitude') and loc.get('longitude'):
        user_lat, user_lon = loc['latitude'], loc['longitude']
        st.sidebar.success(f"Locked: {user_lat:.4f}, {user_lon:.4f}")
    else:
        st.sidebar.warning("Waiting for GPS signal... Defaulting to Reitz Union.")
        user_lat, user_lon = 29.6465, -82.3477

elif origin_mode == "Campus Presets":
    presets = {
        "Garage 5 / Commuter Lot": (29.6385, -82.3615),
        "Southwest Recreation Center": (29.6378, -82.3685),
        "Reitz Union": (29.6465, -82.3477),
        "Library West / Plaza": (29.6515, -82.3429),
        "Sorority Row": (29.6445, -82.3392)
    }
    preset_choice = st.sidebar.selectbox("Select Staging Point", list(presets.keys()))
    user_lat, user_lon = presets[preset_choice]
    st.sidebar.info(f"Origin Set: {preset_choice}")

else:  # Custom Coordinates
    col_lat, col_lon = st.sidebar.columns(2)
    user_lat = col_lat.number_input("Latitude", value=29.6465, format="%.4f")
    user_lon = col_lon.number_input("Longitude", value=-82.3477, format="%.4f")

st.sidebar.divider()

vehicle_mpg = st.sidebar.number_input("Vehicle Fuel Economy (MPG)", min_value=10.0, max_value=60.0, value=25.0, step=1.0)
gallons_needed = st.sidebar.slider("Gallons Needed", min_value=1.0, max_value=30.0, value=12.0, step=0.5)

reward_promotions = st.sidebar.multiselect(
    "Active Reward Programs / Memberships", 
    ["Sam's Club", "Wawa Rewards", "My GATE Rewards", "Inner Circle", "Fuel Rewards", "Sunoco Go Rewards", "Texaco Rewards", "Chevron Rewards"]
)



# ==========================================
# 4. OPPORTUNITY COST ENGINE (MATH & ROUTING)
# ==========================================
# Generate base stations
df_stations = get_station_network(benchmarkPriceRegular)

# Define eligible_stations right here so the loop below has access to it:
# Create a fresh copy to manipulate
eligible_stations = df_stations.copy()

# Determine the exact price for this specific user
def get_user_price(row):
    # If it's a wholesale club and user doesn't have the card, add $99 penalty
    # so it stays on the map/table but can never win the top recommendation
    if row["club_only"] and row["brand"] not in reward_promotions:
        return row["standard_price"] + 99.0
    if row["brand"] in reward_promotions:
        return row["member_price"]
    return row["standard_price"]

eligible_stations["price"] = eligible_stations.apply(get_user_price, axis=1)

# Format the pump price column for display (hides the $99 penalty from the UI table)
eligible_stations["display_price"] = eligible_stations.apply(
    lambda x: "Membership Required" if x["price"] > 50 else f"${x['price']:.2f}", axis=1
)

# We have to fetch the real road distance and the street geometry for each station
route_geometries = []
actual_miles = []
actual_mins = []

for index, row in eligible_stations.iterrows():
    miles, mins, geo = get_real_drive_data(user_lat, user_lon, row["lat"], row["lon"])
    
    # If the API fails, fallback to an arbitrary high number so it doesn't break
    actual_miles.append(miles if miles else 99.9)
    actual_mins.append(mins if mins else 99)
    route_geometries.append(geo)

eligible_stations["one_way_miles"] = actual_miles
eligible_stations["drive_time_mins"] = actual_mins
eligible_stations["geometry"] = route_geometries

# --- The missing math & Sorting logic ---
# Calculate fuel burned driving (round trip)
eligible_stations["round_trip_miles"] = eligible_stations["one_way_miles"] * 2

# Fixed: using benchmarkPriceRegular instead of benchmark_price
eligible_stations["drive_cost"] = (
    (eligible_stations["round_trip_miles"] / vehicle_mpg) * benchmarkPriceRegular
).round(2)

# Calculate cost of the gas itself
eligible_stations["pump_total"] = (eligible_stations["price"] * gallons_needed).round(2)

# Total Net Cost = Gas + Drive Cost
eligible_stations["net_total_cost"] = (eligible_stations["pump_total"] + eligible_stations["drive_cost"]).round(2)

# Sort the DataFrame from cheapest to most expensive
ranked_df = eligible_stations.sort_values(by="net_total_cost").reset_index(drop=True)

# Define the winners so the UI can use them
best_station = ranked_df.iloc[0]
nearest_station = eligible_stations.sort_values(by="one_way_miles").iloc[0]


# ==========================================
# 5. PRESENTATION & UI RENDERING
# ==========================================
st.subheader("Optimal Dispatch Recommendation")
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric(
        label="Top Recommendation",
        value=best_station["name"],
        delta=f"{best_station['display_price']}/gal"
    )
with col_b:
    st.metric(
        label="Net Effective Cost (Pump + Drive)",
        value=f"${best_station['net_total_cost']:.2f}",
        delta=f"{best_station['drive_time_mins']} min drive ({best_station['one_way_miles']} mi)"
    )
with col_c:
    savings_vs_nearest = nearest_station["net_total_cost"] - best_station["net_total_cost"]
    st.metric(
        label="Net Savings vs Nearest Station",
        value=f"${savings_vs_nearest:.2f}",
        delta="Profitable Trip" if savings_vs_nearest > 0 else "Stay Local",
        delta_color="normal" if savings_vs_nearest > 0 else "off"
    )

# --- Route Breakdown Expander ---
with st.expander("🚘 View Trip Logistics Breakdown"):
    st.write(f"**Target:** {best_station['name']}")
    st.write(f"**One-Way Distance:** {best_station['one_way_miles']} miles ({best_station['drive_time_mins']} minutes)")
    st.write(f"**Fuel Burned on Trip:** ${(best_station['round_trip_miles'] / vehicle_mpg) * benchmarkPriceRegular:.2f} (Round-Trip)")
    st.write(f"**Total at Pump:** {gallons_needed} gal × {best_station['display_price']} = ${best_station['pump_total']:.2f}")

# --- Loss Aversion Upsell (Sam's Club logic) ---
# If Sam's Club isn't the winner, and they don't have a membership, show what they left on the table
sams_club_data = ranked_df[ranked_df["name"] == "Sam's Club (Butler Plaza)"].iloc[0]
if "Sam's Club" not in reward_promotions and best_station["name"] != "Sam's Club (Butler Plaza)":
    # Calculate what Sam's WOULD have cost without the $99 penalty
    real_sams_price = sams_club_data["standard_price"]
    sams_pump_total = real_sams_price * gallons_needed
    sams_net_total = sams_pump_total + sams_club_data["drive_cost"]
    missed_savings = best_station["net_total_cost"] - sams_net_total
    
    if missed_savings > 0:
        st.info(f"💡 **Opportunity Cost Alert:** A Sam's Club membership would have saved you **${missed_savings:.2f}** on this exact trip.")

# --- Comparison Table & Map ---
st.divider()
st.subheader("Gainesville Gas Market")
st.caption("Sorted intelligently by **Net Effective Cost** (Total at pump + Round-trip gas burned driving there).")

display_df = ranked_df[[
    "name", "display_price", "one_way_miles", "drive_cost", "pump_total", "net_total_cost"
]].rename(columns={
    "name": "Station",
    "display_price": "Pump Price",
    "one_way_miles": "Distance (mi)",
    "drive_cost": "Round-Trip Cost ($)",  # Renamed for absolute clarity
    "pump_total": "Gas Subtotal ($)",
    "net_total_cost": "Net Cost ($)"
})

st.dataframe(
    display_df,
    column_config={
        "Distance (mi)": st.column_config.NumberColumn(format="%.1f mi"),
        "Round-Trip Cost ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Gas Subtotal ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Net Cost ($)": st.column_config.NumberColumn(format="$%.2f"),
    },
    hide_index=True,
    use_container_width=True
)

st.subheader("Optimal Dispatch Route")
# Generate the Folium map object
minimap = draw_minimap(
    user_lat, user_lon, 
    best_station["lat"], best_station["lon"], 
    best_station["geometry"], 
    best_station["name"],
    ranked_df
)

# Render it in Streamlit
st_folium(minimap, width=800, height=500)



# ==========================================
# 6. 30-DAY HISTORICAL MARKET SIMULATION
# ==========================================
st.divider()
st.subheader("30-Day Market Volatility")

@st.cache_data
def generate_historical_trends(base_price, current_date):
    # We pull a subset of key stations so the graph remains clean and readable
    target_stations = {
        "Sam's Club (Butler Plaza)": -0.20,
        "Wawa (Archer Rd)": 0.05,
        "Circle K (SW 34th St)": 0.04,
        "Gate (Archer Rd)": 0.08,
        "Shell (W Newberry Rd)": 0.12
    }
    history = []
    
    # 30-day rolling window
    for i in range(30, -1, -1):
        target_date = current_date - datetime.timedelta(days=i)
        
        # Deterministic seed using the exact calendar day
        np.random.seed(target_date.toordinal())
        
        # Station volatility
        vol = np.random.uniform(-0.06, 0.06, len(target_stations))
        
        daily_prices = {"Date": target_date}
        for idx, (name, offset) in enumerate(target_stations.items()):
            # Public posted standard price
            daily_prices[name] = round(base_price + offset + vol[idx], 2)
            
        history.append(daily_prices)
        
    return pd.DataFrame(history)

# Passing today's date prevents stale caching and automatically advances the window
today_date = datetime.date.today()
df_history_raw = generate_historical_trends(benchmarkPriceRegular, today_date)

# Reshape data into long format for Altair visualization
df_melted = df_history_raw.melt(id_vars=["Date"], var_name="Station", value_name="Price")

# Calculate dynamic bounds so lines aren't flattened
min_p = float(df_melted["Price"].min()) - 0.05
max_p = float(df_melted["Price"].max()) + 0.05

chart = (
    alt.Chart(df_melted)
    .mark_line(point=True)
    .encode(
        x=alt.X("Date:T", title="Timeline", axis=alt.Axis(format="%b %d", labelAngle=-45)),
        y=alt.Y(
            "Price:Q", 
            title="Posted Street Price ($/gal)", 
            scale=alt.Scale(domain=[min_p, max_p]),
            axis=alt.Axis(format="$.2f", tickCount=8)
        ),
        color=alt.Color("Station:N", title="Brand / Location"),
        tooltip=[
            alt.Tooltip("Date:T", format="%Y-%m-%d"),
            alt.Tooltip("Station:N"),
            alt.Tooltip("Price:Q", format="$.2f")
        ]
    )
    .properties(height=380)
    .interactive()
)

st.altair_chart(chart, use_container_width=True)