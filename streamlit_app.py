import pandas as pd
#pd.options.display.float_format = '{:.2f}'.format
import numpy as np
from streamlit_folium import st_folium
import altair as alt
import folium
import branca
from geopy.geocoders import Nominatim
#import config
import streamlit as st
#from PIL import Image
# from streamlit_extras.add_vertical_space import add_vertical_space
#from st_aggrid import AgGrid, GridOptionsBuilder
#from st_aggrid.shared import GridUpdateMode
from datetime import datetime
import requests
import boto3
import json

import utility_functions

# Load API keys from JSON file
#with open('config.json') as file:
#    config = json.load(file)

# Access the API keys
#aws_access_key_id = config['aws_access_key_id']
#aws_secret_access_key = config['aws_secret_access_key']

# change this for running streamlit on cloud
aws_access_key_id = st.secrets["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = st.secrets["AWS_SECRET_ACCESS_KEY"]

padding = 5
st.set_page_config(page_title="Electric Vehicles", layout="wide", page_icon="📍")

#title
st.title(":blue[  Estimation of Charging Costs of Electric Vehicles]")

def remote_css(url):
    st.markdown(f'<link href="{url}" rel="stylesheet">', unsafe_allow_html=True)    

def icon(icon_name):
    st.markdown(f'<i class="material-icons">{icon_name}</i>', unsafe_allow_html=True)

#local_css("style.css")
remote_css('https://fonts.googleapis.com/icon?family=Material+Icons')

icon("electric_car")

#markdown
st.markdown("""
    Electric vehicles have gained a lot of popularity in recent years due to their eco-friendliness, low emissions, and reduced reliance on fossil fuels. However, one of the most important factors that determine the feasibility and affordability of electric vehicles is their energy costs. This project predicts energy costs of electric vehicles using factors such as vehicle make/model, its battery capacities, travel distances and local electricity prices.
""")
     
st.markdown(
"""
Quick Info:
- Select the vehicle you are interested in from the drop down list
- Select the closest city where you intend to drive the vehicle
- Select the expected annual miles you intend to drive
- Select the number of years you intend to use the vehicle
- Color of icon: green: super rating > 5, orange: greater than 3 and less than 5, red: less than 3
- Click on the icon will pop up a display table with more info regarding the restaurant
"""
)

@st.cache_data(persist=True)

# filename includes the prefix on the S3 bucket
def load_data(filename):
    session = boto3.session.Session( 
    aws_access_key_id= aws_access_key_id, 
    aws_secret_access_key= aws_secret_access_key,  
    region_name='us-east-1'
    )

    s3_client = session.client('s3')
    bucket_name = 'tdi-capstone-lb'
    response = s3_client.get_object(Bucket=bucket_name, Key=filename)
    if filename[-4:] == '.csv':
        data = pd.read_csv(response['Body'])
    elif filename[-4:] == 'json':
        json_data = response['Body'].read().decode('utf-8')
        data = json.loads(json_data)
        
    return data

# read the data
df_cities = load_data('data/cities_geocoded.csv')
df_vehicles = load_data('data/electric_vehicles.csv')
city_coordinates = df_cities['geoloc']
dict_vehicles = df_vehicles.set_index(['make'])['model'].to_dict()
st.write(
    f"{dict_vehicles}"
)
city_choices = list(df_cities["city_state"])
city_choices.insert(0, "Select a City")
vehicle_choices = list(zip(df_vehicles['make'], df_vehicles['model']))
vehicle_choices.insert(0, "Select a Vehicle")

"""
vehicle_choices = list(df_vehicles['make'].unique())
vehicle_choices.insert(0, "Select a Make")
#current_models = list(df_vehicles[df_vehicles['make'] == vehicle_choices]['model'].unique())
model_choices = list(df_vehicles['model'].unique())
model_choices.insert(0, "Select a Make First")
"""

with st.sidebar.form(key="my_form"):
    selectbox_city = st.selectbox("Choose a City", city_choices)
    selectbox_vehicle = st.selectbox("Choose a Vehicle Make", vehicle_choices)
    """
    if selectbox_vehicle == 'Select a Make':
        pass
        #selectbox_model = st.selectbox("Choose a Vehicle Model", "Select a Make First")
    else:        
        current_models = dict_vehicles[selectbox_vehicle]
        selectbox_model = st.selectbox("Choose a Vehicle Model", current_models)
    """
    
    numberinput_threshold = st.number_input(
        """Select Miles Estimated to Drive Annually""",
        value=12000,
        min_value=1000,
        max_value=50000,
        step=100,
        format="%i",
    )

    st.markdown(
        '<p class="small-font">Results Limited to top 5 per State in overall US</p>',
        unsafe_allow_html=True,
    )
    pressed = st.form_submit_button("Estimate Vehicle Costs")















