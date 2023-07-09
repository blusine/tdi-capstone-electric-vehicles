import bs4
import requests
import pandas as pd
import boto3

def lambda_handler(event, context):
    """ This function scrapes electric vehicle database https://ev-database.org/ to exctract technical specifications of electric vehicles."""
    
    try:
        url = "https://ev-database.org/"
        response = requests.get(url)
        soup = bs4.BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print("Request error {e}")
        raise e
    
    try:
        spans = ['model', 'acceleration', 'topspeed', 'battery', 'erange_real', 'efficiency', 'fastcharge_speed', 'country_uk']
        columns = ['make', 'model', 'acceleration', 'topspeed', 'battery', 'range', 'efficiency', 'fastcharge_speed', 'country_uk']

        ev_df = pd.DataFrame()
        for sp in spans:
            s = soup.find_all('span', attrs={'class': sp})
            ss = pd.DataFrame([i.text for i in s], columns = [sp])
            ev_df = pd.concat([ev_df, pd.DataFrame(ss)], axis=1)

        df = pd.DataFrame([i.text.strip().split(" ")[0] for i in soup.find_all('a', attrs={'class': 'title'})], columns = ['make'])

        ev_df1 = pd.concat([df, ev_df], axis = 1)

        img_tags  = soup.find_all('img') #Find all
        img_tags = img_tags[1:] # the first one is the website logo, so throwing it away

        # urls of vehicle images
        img1_url = []
        for tag in img_tags:
            img1 = url[:-1] + tag.attrs['data-src-retina']
            img1_url.append(img1)

        div_tags = soup.find_all('div', attrs={'class': 'img'}) 

        # hrefs are links with detailed vehicle info
        hrefs = []
        for div_tag in div_tags:
            a_tags = div_tag.find_all('a')
            #print(a_tags)
            for a_tag in a_tags:
                href = url[:-1] + a_tag['href']
                print(href)
                hrefs.append(href)

        ev_df1['img1_url'] = img1_url
        ev_df1['hrefs'] = hrefs

    except Exception as e:
        print("Unknown error ocurred {e}")
        raise e
    
    try:
        #Connect to S3
        s3 = boto3.client('s3',
            region_name='us-east-1'
        )
        bucket_name = "tdi-capstone-lb"
        csv_data = ev_df1.to_csv(index=False)
        bytes_data = csv_data.encode()
        response = s3.put_object(Body=bytes_data, Bucket=bucket_name, Key="data/electric_vehicles.csv")
    except (KeyError) as e:
        print(f"Unable to upload data to S3, got error {e}")
        raise e
    
