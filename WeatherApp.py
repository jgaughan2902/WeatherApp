import requests
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import streamlit as st
import plotly.express as px

# Geocode City Conversion to Lat/Lon
@st.cache_data(ttl = 3600)
def geocode_city(city_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q" : city_name,
        "format" : "json",
        "limit" : 1,
        "countrycodes" : "us"
    }
    
    headers = {"User-Agent" : "MyWeatherApp (joshgaughan2902@gmail.com)"}

    time.sleep(1)

    response = requests.get(url, params = params, headers = headers, timeout = 10)

    if response.status_code != 200:
        return None, None, None
    
    try:
        results = response.json()
    except ValueError:
        return None, None, None

    results = response.json()

    if results:
        lat = float(results[0]["lat"])
        lon = float(results[0]["lon"])
        display_name = results[0]["display_name"]
        return lat, lon, display_name
    else:
        return None, None, None

# Time and Data Reformatting   
def format_time(iso_string):
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%m/%d/%y %I%p").lower()

def format_time_range(start_iso, end_iso):
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)

    date_str = start.strftime("%m/%d/%y")
    start_str = start.strftime("%I%p").lower()
    end_str = end.strftime("%I%p").lower()

    return f"{date_str} {start_str} to {end_str}"

def format_period(period):
    name = period["name"]
    time_range = format_time_range(period["startTime"], period["endTime"])
    return time_range

# Time Zone Conversion
def format_utc_timestamp(utc_string, timezone_str):
    dt = datetime.fromisoformat(utc_string.replace("Z", "+00:00"))
    dt_local = dt.astimezone(ZoneInfo(timezone_str))

    date_str = "/".join(str(int(p)) for p in dt_local.strftime("%m/%d/%y").split("/"))

    if dt_local.minute == 0:
        time_str = dt_local.strftime("%I%p").strip("0").lower()
    else:
        time_str = dt_local.strftime("%I:%M%p").strip("0").lower()

    return f"{date_str} @ {time_str}"

def c_to_f(c):
    return round((c * 9/5) + 32, 1) if c is not None else None

def ms_to_mph(ms):
    return round(ms * 2.237, 1) if ms is not None else None

def deg_to_cardinal(deg):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    ix = round(deg / 22.5)
    return dirs[ix % 16]

# Get Coordinates
@st.cache_data(ttl = 3600)
def get_point_data(lat, lon):
    url = f"https://api.weather.gov/points/{lat},{lon}"
    return requests.get(url, headers = {"User-Agent" : "MyWeatherApp (joshgaughan2902@gmail.com)"}).json()

# Get Station Identification
@st.cache_data(ttl = 3600)
def get_station_id(obs):
    stations = requests.get(obs, headers = {"User-Agent" : "MyWeatherApp (joshgaughan2902@gmail.com)"}).json()
    return stations["features"][0]["properties"]["stationIdentifier"]

# Get Current Conditions
@st.cache_data(ttl = 600)
def get_current_conditions(station_id):
    url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
    return requests.get(url, headers = {"User-Agent" : "MyWeatherApp (joshgaughan2902@gmail.com)"}).json()

# Get Hourly Forecast
@st.cache_data(ttl = 1800)
def get_hourly_forecast(url):
    return requests.get(url, headers = {"User-Agent" : "MyWeatherApp (joshgaughan2902@gmail.com)"}).json()

# Get 7 Day Forecast
@st.cache_data(ttl = 3600)
def get_7day_forecast(url):
    return requests.get(url, headers = {"User-Agent" : "MyWeatherApp (joshgaughan2902@gmail.com)"}).json()
##############################################

st.title("Your Weather Forecast")

st.subheader("Enter your City/Town Below")
city_input = st.text_input("", placeholder = "e.g. Chicago, IL")

lat, lon, display_name = None, None, None

if city_input:
    lat, lon, display_name = geocode_city(city_input)

    if lat:
        pass
    else:
        st.error("City/Town Not Found. Try Again!")

if lat and lon:
    data = get_point_data(lat, lon)
    properties = data["properties"]

    timezone_str = properties["timeZone"]
    seven_day_url = properties["forecast"]
    hourly_url = properties["forecastHourly"]
    obs = properties["observationStations"]

    st.subheader("Current Conditions")

    # Current Conditions
    station_id = get_station_id(obs)

    current = get_current_conditions(station_id)

    properties = current["properties"]

    station_list = []
    time_list = []
    temp_list = []
    humid_list = []
    wind_speed_list = []
    wind_gust_list = []
    wind_direction_list = []
    df_current = pd.DataFrame()

    station_list.append(properties["stationName"])
    time_list.append(format_utc_timestamp(properties["timestamp"], timezone_str))
    temp_list.append(c_to_f(properties["temperature"]["value"]))
    humid_list.append(properties["relativeHumidity"]["value"])
    wind_speed_list.append(properties["windSpeed"]["value"])
    wind_gust_list.append(properties["windGust"]["value"])
    wind_direction_list.append(deg_to_cardinal(properties["windDirection"]["value"]))

    df_current["Station Name"] = station_list
    df_current["Last Updated"] = time_list
    df_current["Temperature in °F"] = temp_list
    df_current["Humidity (%)"] = humid_list
    df_current["Wind Speed (mph)"] = wind_speed_list

    df_current["Wind Gusts (mph)"] = [
        "No Registered Gusts" if v is None else v
        for v in wind_gust_list
    ]
        
    df_current["Wind Direction (from)"] = wind_direction_list

    st.dataframe(df_current, 
                 row_height = 50, 
                 hide_index = True)

    st.subheader("Hourly Forecast")

    # Hourly Forecast Table
    hourly_forecast = get_hourly_forecast(hourly_url)
    periods = hourly_forecast["properties"]["periods"]

    time_list = []
    temp_list = []
    humid_list = []
    wind_list = []
    df_hourly = pd.DataFrame()

    for period in periods:
        time_list.append(format_time(period["startTime"]))
        temp_list.append(period["temperature"])
        humid_list.append(period["relativeHumidity"]["value"])
        wind_list.append(period["windSpeed"])

    df_hourly["Time"] = time_list
    df_hourly["Temperature (°F)"] = temp_list
    df_hourly["Humidity (%)"] = humid_list
    df_hourly["Wind Speed (mph)"] = wind_list

    fig = px.line(
        df_hourly, x = "Time", y = "Temperature (°F)"
    )
    fig.update_xaxes(nticks = 10)
    st.plotly_chart(fig)

    st.dataframe(df_hourly, 
                 row_height = 30, 
                 hide_index = True)

    st.subheader("7 Day Forecast")

    # Seven Day Forecast Table
    forecast = get_7day_forecast(seven_day_url)
    periods = forecast["properties"]["periods"]

    name_list = []
    period_list = []
    temp_list = []
    desc_list = []
    df_forecast = pd.DataFrame()

    for period in periods:
        name_list.append(period["name"])
        period_list.append(format_period(period))
        temp_list.append(period["temperature"])
        desc_list.append(period["shortForecast"])

    df_forecast["Day"] = name_list
    df_forecast["Period"] = period_list
    df_forecast["Temperature (mph)"] = temp_list
    df_forecast["Short Description"] = desc_list

    st.dataframe(df_forecast, 
                 row_height = 70, 
                 hide_index = True)
