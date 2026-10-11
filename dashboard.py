import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv

# Unlock the vault
load_dotenv()

# Streamlit uses specific commands to render text on the web page
st.title("Florida Gas Price Tracker")
st.write("Live data from the U.S. Energy Information Administration (EIA)")



# Data Tank || get request || converting the response to dictionary || Securely creating protected key
api_key = os.getenv("EIA_API_KEY")
url = f"https://api.eia.gov/v2/petroleum/pri/gnd/data/?api_key={api_key}&frequency=weekly&data[0]=value&facets[series][]=EMM_EPM0_PTE_SFL_DPG&sort[0][column]=period&sort[0][direction]=desc&length=10"
response = requests.get(url)
data = response.json()


# Move through the nested data to get the pure list we want (opens the response "folder" then the data "folder" which is where the data is)
series_data = data['response']['data']


# Convert to a DataFrame keeping only the data and price columns || forcing 'values' to be floats not strings (fixed the mean() type error)
df = pd.DataFrame(series_data)
df['value'] = df['value'].astype(float)
filtered_df = df[['period','value']]


# Calculating prices available & Average gas price  
lowestPrice = filtered_df['value'].min()
highestPrice = filtered_df['value'].max()
meanPrice = filtered_df['value'].mean()

# Make filtered_df a rendered interative table with streamlit || formatting it to say the price collumn is currency and in so formatting it this way
# AKA the Display Case
st.dataframe(
    filtered_df,
    column_config={
        "period": "Date",
        "value": st.column_config.NumberColumn("Price", format="$%.2f")
    }
)

# Creating Columns to vertically arrange the metric cards in streamlit
col1, col2, col3 = st.columns(3)
# Mettric Card in streamlit is desigined to show off important numbers || placing them into the columns made above
with col1:
    st.metric(label="Lowest Weekly Average", value=f"${lowestPrice:.2f}")
with col2:
    st.metric(label="Mean Over Period", value=f"${meanPrice:.2f}")
with col3:    
    st.metric(label="Highest Weekly Average", value=f"${highestPrice:.2f}")


