import requests
import pandas as pd
import random


# this is all a logically outline template finished product should be over on the dashboard side. this is a terminal test

# A free URL that returns dummy JSON data
url = "https://jsonplaceholder.typicode.com/posts"

# WE send a GET request to the waiter
response = requests.get(url)

# Check if the server successfully gave us the data
#print(response.status_code)

# Parse the JSON payload into a Python dictionary
data = response.json()

# Convert the raw JSON list into a structured table (DataFrame)
df = pd.DataFrame(data)

# Print just the first 5 rows so we don't flood the terminal // .head() peaks at just the first 5 rows // filtered just restricts the sought after data points
filtered_df = df[['title','body']]
# Creating random dummy gas prices to help handle real data later on
filtered_df['Price'] = [round(random.uniform(2.20, 4.10),2) for _ in range(len(filtered_df))]

# Prints out the DataFrame
print(filtered_df.head())

# Calculating the cheapest price in the DF
cheapest_price = filtered_df['Price'].head().min()
# Finding the station name of the cheapest price // this will also capture all stations equal to the cheapest price and not stop if just 1 is
cheapest_station = filtered_df[filtered_df['Price'] == cheapest_price]


# cheapest_station is a dataframe, so using .iloc (integer location) we can extract specifc vales
station_name = cheapest_station['title'].iloc[0]
satation_price = cheapest_station['Price'].iloc[0]



# Out put test
#   print(f"Station {cheapest_station} has gas currently at ${cheapest_price}")
#   print(cheapest_station)
print(f'The cheapest gas is at {station_name} for ${satation_price}')
