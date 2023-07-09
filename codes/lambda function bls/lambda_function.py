import bs4
import regex as re
import itertools
import requests
import numpy as np
import pandas as pd
from geopy.geocoders import Nominatim
from datetime import datetime
import json
import boto3
import os
import pmdarima as pm
from pmdarima.model_selection import train_test_split
from pmdarima.pipeline import Pipeline
from pmdarima.preprocessing import BoxCoxEndogTransformer
import pickle


def lambda_handler(event, context):
    def load_data(filename):
        s3 = boto3.client('s3',
            region_name='us-east-1'
        )
        bucket_name = 'tdi-capstone-lb'

        response = s3.get_object(Bucket=bucket_name, Key=filename)
        if filename[-4:] == '.csv':
            data = pd.read_csv(response['Body'])
        elif filename[-4:] == 'json':
            json_data = response['Body'].read().decode('utf-8')
            data = json.loads(json_data)
        elif filename[-4:] == '.pkl':
            pkl_data = response['Body'].read()
            data = pickle.loads(pkl_data)      
        return data
    
    def unload_data(data, filename):
        s3 = boto3.client('s3',
            region_name='us-east-1'
        )
        bucket_name = "tdi-capstone-lb"
        if filename[-4:] == '.csv':
            csv_data = data.to_csv(index=False)
            bytes_data = csv_data.encode()
        elif filename[-4:] == '.pkl':
            bytes_data = pickle.dumps(data)

        response = s3.put_object(Body=bytes_data, Bucket=bucket_name, Key=filename)
    
    try:
        #Connect to S3
        filename="data/cities_series.csv"
        cities = load_data(filename)

    except (KeyError) as e:
        print(f"Unable to read from S3, got error {e}")
        raise e

    seriesIds = cities["seriesId"]
    api_key = os.environ.get('api_key')
    current_year = datetime.now().year
    current_month = datetime.now().strftime('%m')
    
    if api_key:
        # Use the API key in your code
        def extract_from_blsgov(api_key, seriesIds,  endyear = datetime.now().year, startyear = (datetime.now().year-19)):
            """ This function extracts timeseries data from bls.gov given 
            the user's api_key, the list of seriesIds, and the start / end dates for which we want to extract the data.
            Every seriesId is a dataset in the bls.gov database.
            I did not find any seriesId / Series Title / Survey Name mapping on the website. I found out though, that seriesIds
            starting with "APU" are consumer prices.
            For example: 
            Series Title	:	Electricity per KWH in New York-Newark-Jersey City, NY-NJ-PA, average price, not seasonally adjusted
            Series ID	:	APUS12A72610
            Survey Name	:	CPI Average Price Data, U.S. city average (AP)
            Measure Data Type	:	Electricity per KWH
            Area	:	New York-Newark-Jersey City, NY-NJ-PA
            Item	:	Electricity per KWH

            We will have to manually find the seriesIds for the information we want to extract.
            """

            headers = {'Content-type': 'application/json', 'registrationkey': api_key}
            data1 = json.dumps({"seriesid": list(seriesIds),"startyear": startyear, "endyear": endyear, 'registrationkey': api_key})
            series_output = []
            output = pd.DataFrame()
            try:
                p = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=data1, headers=headers)
                json_data = json.loads(p.text)
                
                series_output = []
                for j in json_data['Results']['series']:
                    for x in j['data']:
                        x['seriesId'] = j['seriesID']
                        del x['footnotes']
                        series_output.append(x)
                output = pd.concat([output, pd.DataFrame(series_output)])
            except:
                pass
            return series_output

        bls_series = pd.DataFrame()
        # bls.gov only gives up to 20 years of data within one request. 
        n = 3 # multiple of 20 years for which we would like to extract data from bls.gov. Reasonable is 60 years, i.e. n = 3
        for i in range(n):
            endyear = current_year - 20 * i
            startyear = endyear - 19
            current_series = extract_from_blsgov(api_key, seriesIds, endyear, startyear)
            bls_series = pd.concat([bls_series, pd.DataFrame(current_series)])

        bls_series.drop("latest", axis = 1, inplace = True)
        file_path_name = "data/series_data1.csv" # where we want to save the extracted data, with the
        unload_data(bls_series, file_path_name)

        #### Geocode Cities
        def geocode_cities(address):
            geolocator = Nominatim(user_agent='my_geocoder')  # Initialize geocoder
            location = geolocator.geocode(address)  # Geocode the city
            return location.latitude, location.longitude

        cities['city_state'] = cities['city'] + ", " + cities['state']
        cities['geoloc'] = cities['city_state'].apply(lambda x: geocode_cities(x))
        cities['Latitude'] = cities['geoloc'].apply(lambda x: (x[0]))
        cities['Longitude'] = cities['geoloc'].apply(lambda x: (x[1]))

        df = pd.merge(cities, bls_series, on = "seriesId")
        df['periodNum'] = df['period'].apply(lambda x: x[-2:]) # Only keep the 2 digit month numbers

        # Create date column as integer for later sorting and operations
        df['year'] = df['year'].astype(str)
        df['periodNum'] = df['periodNum'].astype(str)
        df['date'] = pd.concat([df['year'], df['periodNum']], axis=1).apply(''.join, axis=1).astype(int)
        df = df.sort_values(['city'], ascending = True)
        df = df.sort_values(['date'], ascending = True)

        # Calculate average price for each region and date
        region_avg_prices = df.groupby(['region', 'date'])['value'].mean().reset_index()

        region_avg_prices_dict = region_avg_prices.set_index(['region', 'date'])['value'].to_dict()

        # This has the unique date ranges and also, I will use this later to construct missing records
        date_range=df[['year', 'period', 'periodName', 'periodNum', 'date']].drop_duplicates()

        # Construct city - region mapping
        cities_dict = cities.set_index('city')['region'].to_dict()

        def impute_missing_prices():
            """
            This function imputes missing average prices for (city, year_month) combination.
            It creates a row of a dataframe for each missing (city, year_month) and 
            assigns a value of average electricity price for
            the region (one of the 5 US regions) the city belongs to for that year_month, to the record.
            We need this information for consistent time series forecasting.
            """
            desired_order = list(df.columns)
            electricity_data = pd.DataFrame()
            # Iterate over cities and dates to check for missing records
            for city in cities['city']:
                for date in date_range['date']:
                    # Check if the record already exists for the city and date
                    if ((df['city'] == city) & (df['date'] == date)).any():
                        continue
                    else:
                        # If the record does not exist, create a new record
                        region = cities_dict[city]
                        avg_price = region_avg_prices_dict[(region, date)]

                        current_city = cities[cities['city'] == city].reset_index()
                        current_date = date_range[date_range['date'] == date].reset_index()
                        current_date['value'] = avg_price
                        new_record = pd.concat([current_city, current_date], axis = 1).drop("index", axis = 1)

                        # Append the new record to the dataset
                        electricity_data = pd.concat([electricity_data, new_record], ignore_index=True)

            return electricity_data[desired_order]

        electricity_data = impute_missing_prices()

        # Combine Imputed records to the original data
        dff = pd.concat([df, electricity_data], ignore_index=True)

        def forecast_prices(city, y):
            #define the filepath and year_month when the forecasting is carried out
            current_year = datetime.now().year
            current_month = datetime.now().strftime('%m')
            y_m = str(current_year) + "_" +  current_month

            # split data, to capture the price fluctuations in the past year, I gave very few points to test
            train, test = train_test_split(y, train_size=(len(y))-4)

            # Define and fit the pipeline
            pipeline = Pipeline([
                ('boxcox', BoxCoxEndogTransformer(lmbda2=1e-6)),  # lmbda2 avoids negative values
                ('arima', pm.AutoARIMA(seasonal=True, m=12,
                                    suppress_warnings=True,
                                    trace=False))
            ])

            pmdarima_model = pipeline.fit(train)
            filepath = 'models/'
            pkl_filename = filepath + 'pmdarima_model_' + city + y_m + '.pkl'
            unload_data(pmdarima_model, pkl_filename)

        for city in cities['city']:
            dffb = dff[dff['city'] == city]
            y = dffb.sort_values('date')['value']
            try:
                forecast_prices(city, y)
            except:
                pass

        filepath = 'models/'
        filepath2 = 'predictions/'

        current_year = datetime.now().year
        current_month = datetime.now().strftime('%m')
        y_m = str(current_year) + "_" +  current_month

        for city in cities['city']:
            pkl_filename = filepath + 'pmdarima_model_' + city + y_m + '.pkl'

            dffb = dff[dff['city'] == city]
            y = dffb.sort_values('date')['value']

            forecasts = load_data(pkl_filename).predict(n_periods=300)
            forecast_filename = filepath2 + 'prediction_' + city + y_m + '.csv'
            forecasts = pd.DataFrame(forecasts, columns = ['price'])
            unload_data(forecasts, forecast_filename)

        unload_data(dff, "data/city_prices_imputed.csv")
        unload_data(cities, "data/cities_geocoded.csv")

    else:
        # Handle the case when the API key is not set
        print("API Key not found.")

