import pandas as pd
#pd.options.display.float_format = '{:.2f}'.format
import numpy as np
from streamlit_folium import st_folium, folium_static
import altair as alt
import folium
import branca
#from geopy.geocoders import Nominatim
import streamlit as st
#from PIL import Image
from datetime import datetime
#import requests
import boto3
import json
#import jinja2
import pmdarima
#import plost
#import matplotlib.pyplot as plt
#import plotly.express as px

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
- Colors of the map markers: red: for the selected city, blue: for the non-selected city
- A click on a marker will pop up a display with the total cost for that city and the selected vehicle.
- The chart in the bottom shows monthly costs for the selected city and vehicle. 
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
    
    
#st.write(
#    f"{vehicle_data} "
#    )

city_choices = list(city["city_state"] for city in city_data)
city_choices.insert(0, "Select a City")

vehicle_choices = [(vehicle['make'], vehicle['model']) for vehicle in vehicle_data]                    
vehicle_choices.insert(0, "Select a Vehicle")

with st.sidebar.form(key="my_form"):
    selected_city = st.selectbox("Choose a City", city_choices)
    #selected_vehicle = st.selectbox("Choose a Vehicle", vehicle_choices)
    selected_vehicle = st.multiselect("Choose a Vehicle", vehicle_choices, max_selections = 4, default  = "Select a Vehicle")
    
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

expander = st.sidebar.expander("What is this project about?")
expander.write(
    """
Electric vehicles have gained a lot of popularity in recent years due to their eco-friendliness, low emissions, and reduced reliance on fossil fuels. However, one of the most important factors that determine the feasibility and affordability of electric vehicles is their energy costs. This app estimates energy costs of electric vehicles using factors such as **vehicle make/model, battery capacities, travel distances and local electricity prices.** It extracts historical electricity prices from bls.gov and predicts the future prices with time series analysis. Then it uses the predicted prices and vehicle battery information to estimate the charging costs.
"""
)

for i in selected_vehicle:
    st.write(
        f"{i} "
        )

#selected_vehicle = [vehicle for vehicle in vehicle_data if (vehicle["make"] == selected_option[0]) and (vehicle["model"] == selected_option[1] for selected_option in selected_vehicle)]

selected_vehicle = [vehicle for vehicle in vehicle_data if (vehicle['make'], vehicle['model']) in selected_vehicle]

if selected_vehicle:
    with st.expander("Expand to See the Selected Vehicle Information"):
        vdf = pd.DataFrame(selected_vehicle)
        # Iterate over the DataFrame rows and show images
        col1, col2 = st.columns([1, 13])
        with col1:
            st.markdown('###### :green[Image]')
        for index, row in vdf.iterrows():
            with col1:
                image_url = row['img1_url']
                st.image(image_url, caption=f"Image {index+1}")
        with col2:
            st.write(vdf)
            #st.write(row['make'], row['model'], row['make'], row['make'], )

    
selected_city = [city for city in city_data if city["city_state"] == selected_city]

def predict_KWH(city, n_periods):
    """ this function predicts $ prices for a consumer per KWH of electricity purchased in a given city
        models for each city have been trained using pmdarima backage in pythin. The trained models were saved on an s3 bucket.
    """
    current_year = datetime.now().year
    current_month = datetime.now().strftime('%m')
    y_m = str(current_year) + "_" +  current_month
    filepath = "models/"
    pkl_filename = filepath + 'pmdarima_model_' + city + y_m + '.pkl'
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
    # Step 4: consider charging efficiency and real energy used: more energy is used to charge the battery and drive in various conditions
    battery = battery * 1.3
    # Step 5: monthly KWH to keep the car running
    monthly_KWH = monthly_charges * battery
    # Step 6: monthy costs
    monthly_dollars = monthly_KWH * forecasts
    return monthly_dollars

# Call the KWH functions for each selected vehicle and city
if selected_vehicle:
    for city in city_data:
        city['forecasts'] = {}
        city['monthly_dollars'] = {}
        city['cost'] = {}
        for vehicle in selected_vehicle:
            # battery is the battery capacity in KWH of the vehicle
            battery = vehicle['battery']
            # strip the 'km' from vehicle driving range to keep the number only
            driving_range = float(vehicle['erange_real'][:-3])
        
            tmp_forecast = predict_KWH(city['city'], selected_years*12)
            tmp_dollars = calculate_KWH_costs(tmp_forecast, battery, driving_range, selected_miles)
            tmp_cost = sum(tmp_dollars)
            
            city['forecasts'][(vehicle['make'], vehicle['model'])] = tmp_forecast
            city['monthly_dollars'][(vehicle['make'], vehicle['model'])] = tmp_dollars
            city['cost'][(vehicle['make'], vehicle['model'])] = tmp_cost
            #st.write(
            #    f"{city} "
            #  )
    
# Render a map
# credit to https://www.kaggle.com/code/dabaker/fancy-folium
def fancy_html(city_state, total_dollars):
    """ fancy_html draws a popup with city name and total cost, used for the map"""
    Name = city_state
    Total_Cost = total_dollars
                                            
    left_col_colour = "#B2DFDB"
    right_col_colour = "#E0F2F1"
    
    table_rows_with_cost = "" 
    if isinstance(total_dollars, dict):
        for key, value in total_dollars.items():
            
            tbrow = """
               <tr>
                <td style="background-color: """+ left_col_colour +""";"><span style="color: #ffffff;">{}""".format(key) + """</span></td>
                <td style="width: 200px;background-color: """+ right_col_colour +""";">{}</td>""".format(value) + """
              </tr>
            """
            table_rows_with_cost = table_rows_with_cost + tbrow

   
    html = """<!DOCTYPE html>
    <html>

    <head>
     <h4 style="margin-bottom:0"; width="300px">Total Cost for {}</h4>""".format(city_state) + """
    </head>
    
     <table style="height: 126px; width: 300px;">
      <tbody> """ + table_rows_with_cost + """
         
      </tbody>
     </table>
    </html>
    """
    return html

if not selected_city:
    location=[city_data[10]['Latitude'], city_data[10]['Longitude']] # Denver seems to be close to the center of the US map
    color = 'blue'
else:
    location=[selected_city[0]['Latitude'], selected_city[0]['Longitude']]   
map_obj = folium.Map(location=location, zoom_start=4)

for city in city_data:
    if selected_vehicle:
        
        for vehicle in selected_vehicle:
            city['cost'][(vehicle['make'], vehicle['model'])] = "${:,.2f}".format(city['cost'][(vehicle['make'], vehicle['model'])])
        
    if selected_city:
        if city['city_state'] == selected_city[0]['city_state']:
            color = 'red'        
        else:
            color = 'blue'
    
    html = fancy_html(city['city_state'], city['cost'])
    iframe = branca.element.IFrame(html=html,width=300,height=280)
    popup = folium.Popup(iframe,parse_html=True)
    
    folium.Marker(
        [city['Latitude'], city['Longitude']],
          popup=popup,
          icon=folium.Icon(color=color, icon='info-sign'),
          tooltip=city['city_state']).add_to(map_obj)

#st_folium(map_obj, width=725) #too interactive for this application
folium_static(map_obj)
# Add space between the map and the next object
st.markdown("<br>", unsafe_allow_html=True)

# Draw a chart with monthly estimated costs
if selected_city and selected_vehicle:
    df = pd.DataFrame(selected_city[0]['monthly_dollars'], columns=['Cost'])  
    df.reset_index(level=0, inplace=True)
    df.rename(columns = {'index': 'Month'}, inplace = True)
    
    # Chart title
    title = f"Estimated Charging Costs per Month for {selected_vehicle[0]['make']}, {selected_vehicle[0]['model']} in {selected_city[0]['city_state']}"
    
    chart = alt.Chart(df).mark_line().encode(
    #x='index:Q',
    #y='0:Q',
    #alt.X('index').axis().title('Month'),
    #alt.Y('0').axis(format='$').title('USD')
    
    x=alt.X('Month:Q', axis=alt.Axis(title='Month')),
    y=alt.Y('Cost:Q', axis=alt.Axis(title='Monthly Cost, USD'))
    ).properties(
    width='container'
).properties(
    title={
        "text": title,
        "align": "center",
        "anchor": "middle"
    }
)

    chart = chart.configure_axis(
    labelExpr='format(datum.value, ".0f")'
)
    st.altair_chart(chart, use_container_width=True)
    #st.write(chart)
