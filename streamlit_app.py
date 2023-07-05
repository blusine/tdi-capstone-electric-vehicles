import pandas as pd
#pd.options.display.float_format = '{:.2f}'.format
import numpy as np
from streamlit_folium import st_folium, folium_static
import altair as alt
import folium
import branca
from geopy.geocoders import Nominatim
#import config
import streamlit as st
from PIL import Image
# from streamlit_extras.add_vertical_space import add_vertical_space
#from st_aggrid import AgGrid, GridOptionsBuilder
#from st_aggrid.shared import GridUpdateMode
from datetime import datetime
import requests
import boto3
import json
import jinja2
import pmdarima

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

# Create two columns to save space vertically
col1, col2 = st.columns([1, 20])
with col1:
    icon("electric_car")
with col2:
    st.markdown('##### :green[Directions]')
    

#markdown
#st.markdown("""
#    Electric vehicles have gained a lot of popularity in recent years due to their eco-friendliness, low emissions, and reduced reliance on #fossil fuels. However, one of the most important factors that determine the feasibility and affordability of electric vehicles is their #energy costs. This project predicts energy costs of electric vehicles using factors such as vehicle make/model, its battery capacities, #travel distances and local electricity prices.
#""")
     
st.markdown(
"""- Select the closest city where you intend to drive the vehicle
- Select the vehicle you are interested in from the drop down list
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
    elif filename[-4:] == '.pkl':
        import pickle
        pkl_data = response['Body'].read()
        data = pickle.loads(pkl_data)      
    return data

# read the data somehow the json data did not get parsed correctly, so I reading csv and converting to json again
city_data1 = load_data('data/cities_geocoded.csv')
city_data1 = city_data1.apply(lambda x: json.dumps(x.to_dict(), ensure_ascii=False), axis=1)
city_data1 = city_data1.to_list()
vehicle_data1 = load_data('data/electric_vehicles.csv')
vehicle_data1 = vehicle_data1.apply(lambda x: json.dumps(x.to_dict(), ensure_ascii=False), axis=1)
vehicle_data1 = vehicle_data1.to_list()

#Initialize data
city_data = []
for city in city_data1:
    city = json.loads(city)
    city["cost"] = " "
    city_data.append(city)
vehicle_data = []
for vehicle in vehicle_data1:
    vehicle = json.loads(vehicle)
    vehicle_data.append(vehicle)

#city_coordinates = list(city['geoloc'] for city in city_data)

city_choices = list(city["city_state"] for city in city_data)
city_choices.insert(0, "Select a City")
#vehicle_choices = list(zip(vehicle_data['make'], vehicle_data['model']))
vehicle_choices = [(vehicle['make'], vehicle['model']) for vehicle in vehicle_data]                    
vehicle_choices.insert(0, "Select a Vehicle")

#"""
#vehicle_choices = list(df_vehicles['make'].unique())
#vehicle_choices.insert(0, "Select a Make")
##current_models = list(df_vehicles[df_vehicles['make'] == vehicle_choices]['model'].unique())
#model_choices = list(df_vehicles['model'].unique())
#model_choices.insert(0, "Select a Make First")
#"""

with st.sidebar.form(key="my_form"):
    selected_city = st.selectbox("Choose a City", city_choices)
    selected_vehicle = st.selectbox("Choose a Vehicle", vehicle_choices)
    
    #"""
    #if selectbox_vehicle == 'Select a Make':
    #    pass
    #    #selectbox_model = st.selectbox("Choose a Vehicle Model", "Select a Make First")
    #else:        
    #    current_models = dict_vehicles[selectbox_vehicle]
    #    selectbox_model = st.selectbox("Choose a Vehicle Model", current_models)
    #"""
    
    selected_miles = st.number_input(
        """Select Miles You Estimate to Drive Annually""",
        value=12000,
        min_value=1000,
        max_value=50000,
        step=100,
        format="%i",
    )
    
    selected_years = st.slider('📝 Input Number of Years You Intend to Use the Vehicle:', 1 , 25) 

    pressed = st.form_submit_button("Estimate Vehicle Costs")

expander = st.sidebar.expander("What is the project about?")
expander.write(
    """
Electric vehicles have gained a lot of popularity in recent years due to their eco-friendliness, low emissions, and reduced reliance on fossil fuels. However, one of the most important factors that determine the feasibility and affordability of electric vehicles is their energy costs. This app estimates energy costs of electric vehicles using factors such as **vehicle make/model, battery capacities, travel distances and local electricity prices.**
"""
)
selected_vehicle = [vehicle for vehicle in vehicle_data if (vehicle["make"] == selected_vehicle[0]) and (vehicle["model"] == selected_vehicle[1])]

if selected_vehicle:
    st.write(
    f"{selected_vehicle[0]} "
    )

selected_city = [city for city in city_data if city["city_state"] == selected_city]
if selected_city:
    st.write(
    f"{selected_city[0]}"
    )

st.write(
f"{selected_miles, selected_years}"
)

def predict_KWH(city, n_periods):
    """ this function predicts $ prices for a consumer per KWH of electricity purchased in a given city
        models for each city have been trained using pmdarima backage in pythin. The trained models were saved on an s3 bucket.
    """
    current_year = datetime.now().year
    current_month = datetime.now().strftime('%m')
    y_m = str(current_year) + "_" +  current_month
    filepath = "models/"
    pkl_filename = filepath + 'pmdarima_model_' + city + y_m + '.pkl'
    st.write(f"{pkl_filename}")
    pkl_model = load_data(pkl_filename)
    forecasts = pkl_model.predict(n_periods=n_periods)
    return forecasts

def calculate_KWH_costs(forecasts, battery, driving_range, selected_miles):
    """ this function calculates electricity consumption costs for the vehicle, city, number of time periods and expected miles"""
    # Step 1: convert driving range to miles, driving range is how many miles the vehicle is expected to drive per battery charge
    driving_range = driving_range/1.6
    # Step 2: calculate expected average miles per month to be driven
    selected_miles = selected_miles / 12
    # Step 3: calculate # of monthly charges
    monthly_charges = selected_miles / driving_range
    # Step 4: consider charging efficiency: more energy is used to charge the battery
    battery = battery * 1.15
    # Step 5: monthly KWH to keep the car running
    monthly_KWH = monthly_charges * battery
    # Step 6: monthy costs
    monthly_dollars = monthly_KWH * forecasts
    return monthly_dollars

if selected_city:
    forecasts = predict_KWH(selected_city[0]['city'], selected_years*12)
    st.write(
    f"{forecasts}"
    )
    
if selected_vehicle and selected_city:
    # battery is the battery capacity in KWH of the vehicle
    battery = selected_vehicle[0]['battery']
    # strip the 'km' from vehicle driving range to keep the number only
    driving_range = float(selected_vehicle[0]['erange_real'][:-3])
    monthly_dollars = calculate_KWH_costs(forecasts, battery, driving_range, selected_miles)
    selected_city[0]['cost'] = sum(monthly_dollars)
    
    st.write(
    f"{monthly_dollars}"
    )

    st.write(
    f"{selected_city[0]['cost']}"
    )


# Render a map
# credit to https://www.kaggle.com/code/dabaker/fancy-folium
def fancy_html(city_state, total_dollars):
    """ fancy_html draws a popup with city name and total cost, used for the map"""
    Name = city_state
    Total_Cost = total_dollars
                                            
    left_col_colour = "#2A799C"
    right_col_colour = "#C5DCE7"
    
    html = """<!DOCTYPE html>
    <html>

    <head>
     <h4 style="margin-bottom:0"; width="300px">{}</h4>""".format(Name) + """
    </head>
    
     <table style="height: 126px; width: 300px;">
      <tbody>
    
        <tr>
        <td style="background-color: """+ left_col_colour +""";"><span style="color: #ffffff;">Total_Cost</span></td>
        <td style="width: 200px;background-color: """+ right_col_colour +""";">{}</td>""".format(Total_Cost) + """
        </tr>

      </tbody>
     </table>
    </html>
    """
    return html
#lats = [city['Latitude'] for city in city_data]
#longs = [city['Longitude'] for city in city_data]
#location = np.mean(lats), np.mean(longs)
        

#st.write(f"{city_data}")

        
#draw_map(city_data, 'red', map)
#st_data = st_folium(map_obj, width=725, feature_group_to_add=fg)
#st.markdown(map_obj._repr_html_(), unsafe_allow_html=True)


#st.write(f"{city_data}")
if not selected_city:
    location=[city_data[0]['Latitude'], city_data[0]['Longitude']]
else:
    location=[selected_city[0]['Latitude'], selected_city[0]['Longitude']]
    
map_obj = folium.Map(location=location, zoom_start=12)
    
for city in city_data:
    #st.write(f"{city}")
    currency = "${:,.2f}".format(city['cost'])
    html = fancy_html(city['city_state'], currency)
    iframe = branca.element.IFrame(html=html,width=300,height=280)
    popup = folium.Popup(iframe,parse_html=True)
    
    if not selected_city:
        color = 'blue'
    else:
        if city['city_state'] == selected_city[0]['city_state']:
            color = 'red'
    
    folium.Marker(
        [city['Latitude'], city['Longitude']],
          popup=popup,
          icon=folium.Icon(color=color, icon='car'),
          tooltip=city['city_state']).add_to(map_obj)
    
    
    #st_folium(map_obj, width=725)
    folium_static(map_obj)





