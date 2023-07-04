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


def remote_css(url):
    st.markdown(f'<link href="{url}" rel="stylesheet">', unsafe_allow_html=True)    

def icon(icon_name):
    st.markdown(f'<i class="material-icons">{icon_name}</i>', unsafe_allow_html=True)

#local_css("style.css")
remote_css('https://fonts.googleapis.com/icon?family=Material+Icons')

#icon("search")

padding = 5
st.set_page_config(page_title="Electric Vehicles", layout="wide", page_icon="📍")

#title
st.title(":blue[  Estimation of Charging Costs of Electric Vehicles]")
icon("electric_car"
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
df_vehicles = load_data('data/electric_vehicles.json')

