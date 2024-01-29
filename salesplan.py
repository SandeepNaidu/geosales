import streamlit as st
import folium
import geopandas as gpd
from shapely.geometry import Point, Polygon
from streamlit_folium import folium_static
import requests
from geopy.distance import geodesic


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

# Function to get place names within a geofence (this is a placeholder)
def get_places_within_radius(lat, lon, radius, existing_places):
    # Constructing the Overpass QL query
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
    
    # Sending the request and parsing the response
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    
    new_places = []
    center_point = (lat, lon)
    for element in data['elements']:
        place_name = element.get('tags', {}).get('name', 'Unknown')
        if place_name not in existing_places:
            place_coords = (element['lat'], element['lon'])
            distance = geodesic(center_point, place_coords).kilometers
            new_places.append((place_name, round(distance, 2)))
            existing_places.add(place_name)
    
    return new_places

def styled_html(text, color, size):
    return f"<span style='color: {color}; font-size: {size};'>{text}</span>"

def display_places_with_style(places_data):
    for radius, places in places_data.items():
        places.sort(key=lambda x: x[1])

        # Use HTML for headers
        radius_header = styled_html(f"Places within {radius} km radius", "blue", "20px")
        st.markdown(radius_header, unsafe_allow_html=True)

        with st.expander("See places", expanded=True):
            cols = st.columns(4)
            per_column = len(places) // 4 + (len(places) % 4 > 0)

            for i, column in enumerate(cols):
                with column:
                    for place in places[i * per_column:(i + 1) * per_column]:
                        # Style each place name
                        place_text = styled_html(f"{place[0]} ({place[1]} km)", "green", "15px")
                        st.markdown(place_text, unsafe_allow_html=True)



# Streamlit App Layout
st.title("Geofencing Visualization Tool")

# User input for latitude and longitude
lat = st.number_input('Latitude', value=16.56467, format="%.5f")
lon = st.number_input('Longitude', value=78.11582, format="%.5f")

# User input for radius list
radius_input = st.text_input('Enter radii (in km) separated by commas', '5,15,30,50')
radius_list = [int(r.strip()) for r in radius_input.split(',')]

# Initialize map
m = folium.Map(location=[lat, lon], zoom_start=10)

# Create and add circles to the map
circles = create_circles(lat, lon, radius_list)
for circle in circles:
    circle.add_to(m)

existing_places = set()  # To keep track of places already processed

# Collect data for all radii
places_data = {}
existing_places = set()
for radius in radius_list:
    places_within_radius = get_places_within_radius(lat, lon, radius, existing_places)
    places_data[radius] = places_within_radius

display_places_with_style(places_data)

# Display the map
folium_static(m)


