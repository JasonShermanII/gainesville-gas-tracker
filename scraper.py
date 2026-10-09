import requests
import pandas as pd

# The updated APIv2 endpoint for Florida Regular Gas Prices (sorted newest to oldest)
url = "https://api.eia.gov/v2/petroleum/pri/gnd/data/?api_key=DEMO_KEY&frequency=weekly&data[0]=value&facets[series][]=EMM_EPM0_PTE_SFL_DPG&sort[0][column]=period&sort[0][direction]=desc&length=10"

response = requests.get(url)

# Print the status code to prove we aren't getting blocked anymore
print(f"Status Code: {response.status_code}")

# Parse the JSON and dig into the new v2 structure
data = response.json()
series_data = data['response']['data']

# Build the DataFrame and filter for just the Date and Price columns
df = pd.DataFrame(series_data)
print(df[['period', 'value']].head())