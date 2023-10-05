#!/usr/bin/env python
# coding: utf-8

# In[57]:

import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
from geopy.geocoders import Here
import folium
import base64
from urllib.parse import quote
import io
import dash_leaflet as dl
import dash_leaflet.express as dlx

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# Define the app layout
app.layout = html.Div([
    html.H1("Geocoding App"),
    
    # Input for API key
    dcc.Input(
    id='api-key',
    type='text',
    placeholder='Enter Here API Key',
    autoComplete='off'  # Add this line to disable autocomplete
    ),
    
    # File upload confirmation message
    html.Div(id='file-upload-status', style={'margin': '10px'}),
    
    # File upload component
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload File', id='upload-button'),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),

    # Button to run the geocoder
    html.Button('Run Geocoder', id='run-geocoder'),

    # Button to visualize results on a map
    html.Button('Visualize on World Map', id='show-map-button', disabled=True),
    
    # Addresses count message
    html.Div(id='address-count-message', style={'color': 'blue'}),

    # Download button for the geocoded CSV
    html.A(
        html.Button('Download Geocoded CSV', id='download-button'),
        id='download-link',
        download='geocoded_data.csv',
        href='',
        target='_blank'
    ),

    # Error message
    dcc.Markdown(id='error-message', style={'color': 'red'}),

    # Hidden Div to store geocoded data for map display
    html.Div(id='geocoded-data', style={'display': 'none'}),

    # Div to display the map
    dl.Map(
        id='map',
        style={'width': '100%', 'height': '400px'},
        center=[0, 0],
        zoom=1,  # Set an initial zoom level
        children=[
            dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
            dl.LayerGroup(id="layer-group-id"),
        ]
    )
])

# Geocode address function
def geocode_address(api_key, address):
    try:
        geolocator = Here(apikey=api_key)
        location = geolocator.geocode(address)
        if location:
            return [location.latitude, location.longitude]
        else:
            return None
    except Exception as e:
        print(f"Error geocoding address {address}: {str(e)}")
        return None

@app.callback(
    [Output('run-geocoder', 'disabled'), Output('file-upload-status', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def enable_geocoder_button(uploaded_file_contents, filename):
    if uploaded_file_contents is not None:
        return False, f'File "{filename}" has been uploaded successfully.'
    return True, 'Drag and Drop or Select CSV File'

@app.callback(
    [Output('show-map-button', 'disabled'), Output('error-message', 'children')],
    [Input('run-geocoder', 'n_clicks')],
    [State('upload-data', 'contents'), State('api-key', 'value')]
)
def enable_map_button(n_clicks, uploaded_file_contents, api_key):
    if n_clicks is None or uploaded_file_contents is None or api_key is None:
        return True, ''

    content_type, content_string = uploaded_file_contents.split(',')
    decoded = base64.b64decode(content_string)

    # Read the uploaded CSV
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    # Check if the CSV contains the expected columns for both cases
    expected_columns_address = ['UniqueID', 'Address']
    expected_columns_street = ['UniqueID', 'Street', 'City', 'State', 'Country', 'PostalCode']

    if not (
        all(col in df.columns for col in expected_columns_address) or
        all(col in df.columns for col in expected_columns_street)
    ):
        return True, 'Error: CSV must contain either UniqueID and Address columns or UniqueID, Street, City, State, Country, and PostalCode columns.'

    if all(col in df.columns for col in expected_columns_address):
        # Combine address columns into a single address column
        df['Address'] = df['Address'].astype(str)
    else:
        # Combine street, city, state, country, and postal code columns into a single address column
        df['PostalCode'] = df['PostalCode'].astype(str)
        df['Address'] = df[['Street', 'City', 'State', 'Country', 'PostalCode']].agg(', '.join, axis=1)

    # Geocode addresses and store latitude and longitude
    df['LatLong'] = df['Address'].apply(lambda x: geocode_address(api_key, x))

    # Filter out rows with missing geocoding results
    df = df.dropna(subset=['LatLong'])

    if df.empty:
        return True, 'Error: No geocoding results found.'

    # Update the address count
    address_count = len(df)
    return False, f'Address Count: {str(address_count)}' if address_count > 0 else 'Error: No geocoding results found.'

@app.callback(
    [Output('geocoded-data', 'children'), Output('download-link', 'href')],
    [Input('show-map-button', 'n_clicks')],
    [State('upload-data', 'contents'), State('api-key', 'value')]
)
def update_output(n_clicks, uploaded_file_contents, api_key):
    if n_clicks is None or uploaded_file_contents is None or api_key is None:
        return '', ''

    content_type, content_string = uploaded_file_contents.split(',')
    decoded = base64.b64decode(content_string)

    # Read the uploaded CSV
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    
    # Check if the CSV contains the expected columns for both cases
    expected_columns_address = ['UniqueID', 'Address']
    expected_columns_street = ['UniqueID', 'Street', 'City', 'State', 'Country', 'PostalCode']

    if not (
        all(col in df.columns for col in expected_columns_address) or
        all(col in df.columns for col in expected_columns_street)
    ):
        return True, 'Error: CSV must contain either UniqueID and Address columns or UniqueID, Street, City, State, Country, and PostalCode columns.'

    if all(col in df.columns for col in expected_columns_address):
        # Combine address columns into a single address column
        df['Address'] = df['Address'].astype(str)
    else:
        # Combine street, city, state, country, and postal code columns into a single address column
        df['PostalCode'] = df['PostalCode'].astype(str)
        df['Address'] = df[['Street', 'City', 'State', 'Country', 'PostalCode']].agg(', '.join, axis=1)

    # Geocode addresses and store latitude and longitude
    df['LatLong'] = df['Address'].apply(lambda x: geocode_address(api_key, x))
    
    # Filter out rows with missing geocoding results
    df = df.dropna(subset=['LatLong'])

    # Calculate the center and zoom level based on geocoded results
    if not df.empty:
        center_lat = df['LatLong'].apply(lambda x: x[0]).mean()
        center_lon = df['LatLong'].apply(lambda x: x[1]).mean()
        zoom = 10  # You can adjust the initial zoom level here
    else:
        center_lat, center_lon, zoom = 0, 0, 1  # Default values if no results
    
    # Create a map centered on the calculated center with the specified zoom level
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
    
    # Plot markers for each location
    for _, row in df.iterrows():
        folium.Marker(location=row['LatLong'], popup=row['Address']).add_to(m)

    # Save the geocoded data to a CSV file with UniqueID, Address, Latitude, and Longitude
    geocoded_csv = df[['UniqueID', 'Address', 'LatLong']].copy()
    geocoded_csv['Latitude'], geocoded_csv['Longitude'] = zip(*geocoded_csv['LatLong'])
    geocoded_csv = geocoded_csv.drop('LatLong', axis=1)
    geocoded_csv.to_csv('geocoded_data.csv', index=False)
    
    # Return the geocoded data as JSON and CSV link
    return df.to_json(date_format='iso', orient='split'), f'data:text/csv;charset=utf-8,{quote(geocoded_csv.to_csv(index=False))}'

@app.callback(
    [Output('layer-group-id', 'children')],
    [Input('geocoded-data', 'children')]
)
def update_map_markers(geocoded_data):
    if not geocoded_data:
        return [[]]

    # Convert the JSON data to a DataFrame
    df = pd.read_json(geocoded_data, orient='split')

    # Create a list of markers for each location
    markers = []
    for _, row in df.iterrows():
        markers.append(
            dl.Marker(
                position=row['LatLong'],
                children=[
                    dl.Tooltip(row['Address']),
                    dl.Popup(row['Address'])
                ]
            )
        )

    return [markers]

if __name__ == '__main__':
    app.run_server(debug=True)


# In[ ]:




