import streamlit as st
import folium
import geopandas as gpd
from shapely.geometry import Point, Polygon
from streamlit_folium import folium_static
import requests
from geopy.distance import geodesic
import pandas as pd

# Assuming you have your Google API Key
google_api_key = "AIzaSyDpFk_tDUpOGVcGfkuI835XlCSmH3PZzoc"  # Replace with your actual Google API Key

# Function to create concentric circles
def create_circles(lat, lon, radius_list):
    circles = []
    for radius in radius_list:
        circle = folium.Circle(
            radius=radius * 1000,
            location=[lat, lon],
            color='blue',
            fill=True,
            fill_opacity=0.4
        )
        circles.append(circle)
    return circles

# Function to get route distance using Google Maps Directions API
def get_route_distance(lat1, lon1, lat2, lon2, api_key):
    endpoint = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{lat1},{lon1}",
        "destination": f"{lat2},{lon2}",
        "key": api_key,
    }
    response = requests.get(endpoint, params=params)
    directions = response.json()
    if directions["routes"]:
        # Initialize shortest_distance with a very high value
        shortest_distance = float('inf')
        for route in directions["routes"]:
            distance = route["legs"][0]["distance"]["value"]  # Distance in meters
            if distance < shortest_distance:
                shortest_distance = distance
        return shortest_distance / 1000  # Convert to kilometers and return
    else:
        return None

# Function to get place names within a geofence
def get_places_within_radius(lat, lon, radius, existing_places):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["place"="village"](around:{radius*1000},{lat},{lon});
      node["place"="town"](around:{radius*1000},{lat},{lon});
      node["place"="city"](around:{radius*1000},{lat},{lon});
    );
    out;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    new_places = []
    center_point = (lat, lon)
    for element in data['elements']:
        place_name = element.get('tags', {}).get('name', 'Unknown')
        place_coords = (element['lat'], element['lon'])
        if place_name not in existing_places:
            # Use Google Maps API for distance
            distance = get_route_distance(lat, lon, place_coords[0], place_coords[1], google_api_key)
            if distance is not None:  # Check if distance was successfully fetched
                new_places.append((place_name, round(distance, 2), place_coords))
                existing_places.add(place_name)
    return new_places

def styled_html(text, color, size):
    return f"<span style='color: {color}; font-size: {size};'>{text}</span>"

def display_places_with_style(places_data):
    for radius, places in places_data.items():
        places.sort(key=lambda x: x[1])
        radius_header = styled_html(f"Places within {radius} km radius", "blue", "20px")
        st.markdown(radius_header, unsafe_allow_html=True)
        with st.expander("See places", expanded=True):
            cols = st.columns(4)
            per_column = len(places) // 4 + (len(places) % 4 > 0)
            for i, column in enumerate(cols):
                with column:
                    for place in places[i * per_column:(i + 1) * per_column]:
                        place_text = styled_html(f"{place[0]} ({place[1]} km)", "green", "15px")
                        st.markdown(place_text, unsafe_allow_html=True)

def get_marker_color(radius):
    if radius <= 5:
        return 'green'
    elif radius <= 15:
        return 'blue'
    elif radius <= 30:
        return 'orange'
    else:
        return 'red'

def generate_csv_data(places_data):
    csv_data = []
    for radius, places in places_data.items():
        for place, distance, (place_lat, place_lon) in places:
            google_maps_link = f"https://www.google.com/maps?q={place_lat},{place_lon}"
            csv_data.append([place, distance, place_lat, place_lon])
    return pd.DataFrame(csv_data, columns=['Place Name', 'Distance (km)', 'Latitude','Longitude'])




# Streamlit App Layout
st.title("Geofencing Visualization Tool")

# Sidebar for input controls
with st.sidebar:
    st.title("Input Controls")
    lat = st.number_input('Latitude', value=16.56467, format="%.5f")
    lon = st.number_input('Longitude', value=78.11582, format="%.5f")
    radius_input = st.text_input('Enter radii (in km) separated by commas', '5,15,30,50')
    update_button = st.button('Update Map')

radius_list = [int(r.strip()) for r in radius_input.split(',')]
places_data = {}

firsttime = True

if firsttime or update_button:
    firsttime=False
    # Initialize map
    m = folium.Map(location=[lat, lon], zoom_start=10)

    # Create and add circles to the map
    circles = create_circles(lat, lon, radius_list)
    for circle in circles:
        circle.add_to(m)

    existing_places = set()  # To keep track of places already processed

    # Collect data for all radii
    existing_places = set()
    for radius in radius_list:
        places_within_radius = get_places_within_radius(lat, lon, radius, existing_places)
        places_data[radius] = places_within_radius


    # Add circle markers for each place
    for radius, places in places_data.items():
        marker_color = get_marker_color(radius)
        for place, distance, (place_lat, place_lon) in places:
            folium.CircleMarker(
                location=[place_lat, place_lon],
                radius=3,  # Small fixed radius for the marker
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.7,
                popup=f"{place} ({distance} km)"
            ).add_to(m)

    # Display the places
    display_places_with_style(places_data)

    # Display the map
    folium_static(m)

    # Button to download CSV
    with st.sidebar:
        df_to_export = generate_csv_data(places_data)
        st.download_button(
            label="Download CSV",
            data=df_to_export.to_csv(index=False).encode('utf-8'),
            file_name='geofenced_places.csv',
            mime='text/csv'
        )



