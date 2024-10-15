# Like PyDeck, Folium is a graphing library to visualize geographic data
# To install folium, run one of the following commands:
# Option 1: pip install folium
# Option 2: conda install -c conda-forge folium

# Import Libraries
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium # Plots folium map to the Streamlit app

# Import data as Pandas DataFrame
ca_aqi_df = pd.read_csv('CA_Cities_AQI.csv')

# # Create a base map centered in California
map = folium.Map(location = [36.7783, -119.4179], 
                 zoom_start = 6)

# Add markers to the map for each city in California
for index, row in ca_aqi_df.iterrows():
  folium.Marker(
    location = [row['Latitude'], row['Longitude']],
    icon = folium.Icon(color = "darkred"),
    popup = folium.Popup(
      f"""
      City: {row['City']}<br>
      AQI: {row['AQI']}<br>
      Category: {row['AQI Category']}
      """, 
      max_width = 250)
  ).add_to(map)

# NOTE: iterrows() loops through each row of the DataFrame and 
# access both the index of the row and the data in the row

# Streamlit app display
st.title("California Cities AQI Map")
st.write("This map shows the AQI (Air Quality Index) values of major cities in California along with their categories.")
st_folium(map, width = 700, height = 500)