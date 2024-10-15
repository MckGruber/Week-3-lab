import geopy.geocoders
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium # Plots folium map to the Streamlit app
import requests as req
from enum import IntEnum
import geopy

class Category(IntEnum):
  GOOD = 1,
  MODERATE = 2,
  UNHEALTHY_SENSITIVE_GROUPS = 3
  UNHEALTHY = 4
  VERY_UNHEALTHY = 5,
  HAZARDOUS = 6,
  UNAVAILIBLE = 7

class ZipCode:
  def __init__(self, zip_code: str):
    self.code = zip_code
    print(zip_code)



class _APIResponceInner:
  def __init__(self, json: dict):
    if json != []:
      print(json)
      self.date_observed: str = json["DateObserved"]
      self.hour_observed: int = json["HourObserved"]
      self.local_time_zone: str = json["LocalTimeZone"]
      self.reporting_area: str = json["ReportingArea"]
      self.state_code: str = json["StateCode"]
      self.latitue: float = json["Latitude"]
      self.longitude: float = json["Longitude"]
      self.parameter_name: str = json["ParameterName"]
      self.aqi: int = json["AQI"]
      category = json["Category"]
      self.category_number: int = category["Number"]
      self.category_name: str = category["Name"]
      self.location = [self.latitue, self.longitude]


    
class APIResponce:
  def __init__(self, responce: req.Response):
    self.__raw__ = responce
    self.status_code = responce.status_code
    if self.ok():    
      json = list(responce.json())
      inner: list[_APIResponceInner] = []
      for resp in json:
        inner.append(_APIResponceInner(resp))
      self.inner = inner
      if self.inner != []:
        self.location = self.inner[0].location
      else:
        self.location =  []
    
  def __str__(self):
    return f"""
    {self.__raw__}
    """


  def ok(self) -> bool:
    if self.status_code == 200 and self.__raw__.json() != []:
      return True
    else:
      return False
    
  def build_pop_up(self) -> tuple[folium.Popup, str | None]:
    # popup= folium.Popup(
        #   f"""
        #   City: {resp.reporting_area}<br>
        #   AQI: {resp.aqi}<br>
        #   Category: {resp.category_name}
        #   """,
        #   max_width=250
      # )
    params: dict[tuple[str, int]] = {}
    for data in self.inner:
      if data.parameter_name in params:
        (category_name, category_number) = params[data.parameter_name]
        if data.category_number != 7 and data.category_number > category_number:
          category_number = data.category_number
          category_name = data.category_name
        params[data.parameter_name] = (
          category_name,
          category_number,
          data.parameter_name,
        )
      else:
        params[data.parameter_name] = (
          data.category_name,
          data.category_number,
          data.parameter_name,
        )
    max: tuple[int, str] = ("", 7)
    for key in params.keys():
      param_num = int(params[key][1])
      max_num = int(max[1])
      if param_num != 7 and (param_num > max_num or max_num == 7):
        max = params[key]

    color = None
    match max[1]:
      case 1:
        color = "Green"
      case 2:
        color = "Yellow"
      case 3:
        color = "Orange"
      case 4:
        color = "Red"
      case 5:
        color = "Purple"
      case 6:
        color = "Maroon"
      case _:
        color = None
    
    return (
      folium.Popup(
        f"""
          Location: {self.location}
          Data: {params}
        """,
        max_width=250
      ),
      color,
    )
    



@st.cache_data
def load_zip() -> list[ZipCode]:
  df = pd.read_csv("california_zip_codes.csv")
  output = []
  for _, code in df.iterrows():
    output.append(ZipCode(code["ZIP Code"]))
  return output


def get_zip(api_key: str, location: ZipCode, distance: int): 
  if type(location) == int:
    zip = location
  else:
    zip = location.code
  BASE_URL = "https://www.airnowapi.org/aq/observation/zipCode/current/"
  params = {
    "format": "application/json",
    "zipCode": zip,
    "distance": distance,
    "API_KEY": api_key
  }
  return APIResponce(req.get(BASE_URL, params=params))

def get_loc(api_key: str, location: tuple[float, float], distance: int) -> APIResponce:
  BASE_URL = "https://www.airnowapi.org//aq/observation/latLong/current/"
  params = {
    "format": "application/json",
    "latitude": location[0],
    "longitude": location[1],
    "distance": distance,
    "API_KEY": api_key
  }
  return APIResponce(req.get(BASE_URL, params=params))

def add_marker_to_feture_group(resp: APIResponce, feature_group: folium.FeatureGroup, distance: int) -> list:
  failed_resp = []
  if resp.ok():
    if resp.ok():
      (popup, color) = resp.build_pop_up()
      folium.Marker(
        location= resp.location,
        icon = folium.Icon(color="darkred"),
        popup=popup,

        # popup= folium.Popup(
        #   f"""
        #   City: {resp.reporting_area}<br>
        #   AQI: {resp.aqi}<br>
        #   Category: {resp.category_name}
        #   """,
        #   max_width=250
        # )
      ).add_to(feature_group)
      folium.Circle(
        resp.location,
        int(distance * 1609.34), 
        color = color, 
        fill = True
      ).add_to(feature_group)
    else:
      failed_resp.append(
        {
          "headers": resp.__raw__.headers,
          "body": resp.__raw__.json(),
        }
      )

def flatten_list(list_to_flatten: list) -> list:
  output = []
  if list_to_flatten != []:
    for item in list_to_flatten:
      if type(item) == list:
        if item != []:
          flist = flatten_list(item)
          for i in flist:
            output.append(i)
      else:
        output.append(item)
  return output

@st.cache_data
def get_california_resources(api_key: str, distance: int)-> list[APIResponce]:
  output= []
  zip_list = load_zip()
  for zip in zip_list:
    resp: APIResponce = get_zip(api_key=api_key, location=zip, distance=distance)
    if resp.ok():
      output.append(resp)
  return output


@st.cache_resource
def build_map(user_api_key: str, distance: int, user_zip_code: int | None):
  map = folium.Map(location = [36.7783, -119.4179], zoom_start=6)
  cal_fg = folium.FeatureGroup("Califonia Data").add_to(map)
  user_zip_fg = folium.FeatureGroup("User Zip Code").add_to(map)
  failed_resp = []
  ca = get_california_resources(api_key=user_api_key, distance=distance)
  print(ca)
  for resp in ca:
    add_marker_to_feture_group(resp, cal_fg, distance)
  if user_zip_code != None:
    resp = get_zip(user_zip_code, user_zip_code, distance)
    add_marker_to_feture_group(resp, user_zip_fg, distance)
  if flatten_list(failed_resp) == []:
    print(f"success build map")
    return map
  else:
    return failed_resp
  

def get_geocode(query: str) -> tuple[float, float] | None:
  BASE_URL = 'https://nominatim.openstreetmap.org/search?'
  params = {
    "q": query,
    "format": "json",
    "addressdetails": 1,
    "limit": 1
  }
  headers = {
    'User-Agent': geopy.geocoders.options.default_user_agent
  }
  resp = req.get(BASE_URL, params=params, headers=headers)
  if resp.status_code != 200:
    return None
  else:
    json = resp.json()
    if json != []:
      return (json[0]["lat"], json[0]["lon"])
    else:
      return None
 
  

def build_geocode_map(map: folium.Map, address: str, distance: int, user_api_key: str) -> folium.Map | None:
  failed_responce = []
  geo_resp = get_geocode(address)
  if geo_resp != None:
    resp: APIResponce = get_loc(api_key=user_api_key, location=geo_resp, distance=distance)
    if type(resp) == APIResponce:
      geo_fg = folium.FeatureGroup("Address Lookup").add_to(map)
      failed_responce.append(add_marker_to_feture_group(resp, geo_fg, distance))
  if flatten_list(failed_responce) != []:
    print(f"failed geocode map: {flatten_list(failed_responce)}")
    st.write(failed_responce)
  else:
    return map





def build_api_map(user_api_key: str) -> folium.Map | None:
  distance = st.slider("Distance from city", min_value=0, value=25)
  user_zip_code = st.number_input("Enter Zip Code", max_value=99999, min_value=10000)
  address = st.text_input("Enter Adress")
  st.markdown("Powered by ")
  map = build_map(
    user_api_key=user_api_key, 
    distance=distance, 
    user_zip_code=user_zip_code
  )

  if type(map) == folium.Map:
    if address != None and address != "":
      print(f"address: {address}")
      map = build_geocode_map(map, address, distance, user_api_key)
    return map
  else:
    print("fialed build api map")
    st.write(map)
  

user_api_key = st.text_input("Enter API Key")


st.title("California Cities AQI Map")
st.write("This map shows the AQI (Air Quality Index) values of major cities in California along with their categories.")
if user_api_key != "":
  map = build_api_map(user_api_key)
  print(map)
  st_folium(map)
  
  
