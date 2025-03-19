import streamlit as st
import pandas as pd
import requests
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import streamlit_ext as ste
# Extract the last update date from the data



sheet_url = "https://docs.google.com/spreadsheets/d/1-r0gE0J4HMAOOd0e-sLI_3xbJNtLXFPxUjAh-XlM3OI/edit?usp=sharing"
sheet_id = sheet_url.split("/")[5]
url_sheet = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Sheet1"

@st.cache_data
def load_data(url):
    return pd.read_csv(url)

df = load_data(url_sheet)
total_graduates = len(df)
#Convert 'Submitted at' column to datetime format
df['Submitted at'] = pd.to_datetime(df['Submitted at'], errors='coerce')

last_update_date = df['Submitted at'].max().strftime('%m/%d/%Y')

st.title("SAMC GME Graduate Data Map")
st.write(f"""
         This map shows the locations of all the GME graduates from SAMC and their whereabouts after graduation. The data is sourced from the SAMC GME Office and is updated every year. Extraction method from Google Sheet and Geo Encoding is done using Python. The data is then visualized using Folium and Streamlit. Developed by: Phillip Kim, MD | Last updated: {last_update_date}
         """
         )

@st.cache_data
def extract_lat_long_via_address(address_or_zipcode):
    lat, lng = None, None
    api_key = st.secrets['GOOGLE_GEO_API_KEY']
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    endpoint = f"{base_url}?address={address_or_zipcode}&key={api_key}"
    r = requests.get(endpoint)
    if r.status_code not in range(200, 299):
        return None, None
    try:
        results = r.json()['results'][0]
        lat = results['geometry']['location']['lat']
        lng = results['geometry']['location']['lng']
    except Exception as e:
        print(f"Error processing address '{address_or_zipcode}': {e}")
    return lat, lng

df['lat'] = df['Employer Full Address PLEASE keep in format include comma (ADDRESS, CITY, STATE, ZIP)'].apply(lambda x: extract_lat_long_via_address(x)[0])
df['lng'] = df['Employer Full Address PLEASE keep in format include comma (ADDRESS, CITY, STATE, ZIP)'].apply(lambda x: extract_lat_long_via_address(x)[1])

missing_coordinate = df[df['lat'].isna() & df['lng'].isna()]
 #drop NaN and reset index to avoid indexing errors
df.dropna(subset=["lat", "lng"], inplace=True)
df.reset_index(drop=True, inplace=True)

df['Graduate Full Name'] = df['Graduate Full Name'].str.strip()
df['Graduate Full Name'] = df['Graduate Full Name'].str.title()
df['Employer Name/Fellowship Program'] = df['Employer Name/Fellowship Program'].str.title()

def popup_html(row):
    i = row
    grad_name=df['Graduate Full Name'].iloc[i]
    grad_year=df['Which class year?'].iloc[i]
    grad_dept=df['Which Graduating Department'].iloc[i]
    grad_employer=df['Employer Name/Fellowship Program'].iloc[i]
    grad_work_setting=df['Work Setting'].iloc[i]
    grad_url_image = df['Resident GME Headshot image'].iloc[i]
    grad_image_html = f'<center><img src={grad_url_image} alt="logo" width=100 height=100></center>'

    
    left_col_color = "#3e95b5"
    right_col_color = "#f2f9ff"

    html = f"""
        <!DOCTYPE html>
        <html>
        {grad_image_html} 
        <center><h4 style="margin-bottom:5"; width="200px">{grad_name}</h4></center>

        <center>
        <table style="height: 126px; width: 305px;">
        
        <tbody>
        <tr>
        <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> Year Graduated </span></td>
        <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{grad_year}</td>
        </tr>
        
        <tr>
        <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> Department </span></td>
        <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{grad_dept}</td>
        </tr>
        
        <tr>
        <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> Employer </span></td>
        <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{grad_employer}</td>
        </tr>
        
        <tr>
        <td style="background-color: {left_col_color}; padding: 5px"><span style="color: #ffffff;"> Work Setting </span></td>
        <td style="width: 150px;background-color: {right_col_color}; padding: 5px">{grad_work_setting}</td>
        </tr>
        </tbody>
        </table>
        </center>
        </html>
        """ 
    return html

#create a functiont to show and downloand map html data 
def show_map():
    m = folium.Map(location=[37.0902, -95.7129], zoom_start=4)
    # if the points are too close to each other, cluster them, create a cluster overlay with MarkerCluster, add to m
    marker_cluster = MarkerCluster().add_to(m)
    # draw the markers and assign popup and hover texts
    # add the markers the the cluster layers so that they are automatically cluster
    for i,r in df.iterrows():
        location = (r["lat"], r["lng"])
        if pd.notna(location[0]) and pd.notna(location[1]):
            # highlight different work settings with different colors 
            worksetting = df['Work Setting'].iloc[i]
            if worksetting == "Ambulatory":
                color = "green"
                tooltip = "Ambulatory"
            elif worksetting == "Hospital":
                color = "red"
                tooltip = "Hospital"
            elif worksetting == "Fellowship":
                color = "blue"
                tooltip = "Fellowship"
            else:
                color = "black"
                tooltip = "Other"
            
            folium.Marker(location=location, popup=popup_html(i), tooltip=tooltip, icon=folium.Icon(color=color, icon='user', prefix='fa')).add_to(marker_cluster)

    m.save("geo_graduates.html")
    folium_static(m, width=725)
    # with open("geo_applicants.html", "r") as file:
    #     st.markdown(file.read(), unsafe_allow_html=True)
    with open("geo_graduates.html", "rb") as file:
        btn = ste.download_button(
            label="Download file as HTML file",
            data=file,
            file_name="geo_graduates.html",
            mime='txt/html'
        )
        st.write("Use a browser to open the downloaded HTML file for offline viewing")
    
    # Display total graduates and respective departments
    
    st.subheader(f'🎓 Total Graduates: {total_graduates}')
    grad_dept_counts = df['Which Graduating Department'].value_counts()
    st.subheader('🪴 Graduates by Department')
    dept_mapping = {
        "EM": "Emergency Medicine",
        "IM": "Internal Medicine",
        "FM": "Family Medicine",
        # Add other department mappings as needed
    }

    dept_counts_str = ", ".join([f'**{dept_mapping.get(dept, dept)}**: {count}' for dept, count in grad_dept_counts.items()])
    st.markdown(dept_counts_str)

    # Define the bounding box for Central Valley, California
    central_valley_bbox = {
       "north": 38.5,  # Northern boundary near southern San Joaquin County
        "south": 34.5,  # Southern boundary near southern Kern County
        "west": -122.0, # Western boundary near the Coast Ranges
        "east": -118.5  # Eastern boundary near the Sierra Nevada foothills
        }
    

    def is_in_central_valley(lat, lng):
        return (central_valley_bbox["south"] <= lat <= central_valley_bbox["north"] and
                central_valley_bbox["west"] <= lng <= central_valley_bbox["east"])

    central_valley_graduates = df[df.apply(lambda row: is_in_central_valley(row['lat'], row['lng']), axis=1)]
    central_valley_count = len(central_valley_graduates)
    central_valley_percentage = (central_valley_count / total_graduates) * 100

    st.subheader(f'✅ Graduates in Central Valley, CA: {central_valley_count} ({central_valley_percentage:.2f}%)')
    # Display names of graduates whose addresses could not be geocoded
    if not missing_coordinate.empty:
        st.subheader('❌ Graduate(s) with Unlocatable Work Address')
        unlocatable_names = missing_coordinate['Graduate Full Name'].tolist()
        st.write(", ".join(unlocatable_names))
    # Display graduates by work setting
    st.subheader('🏢 Graduates by Work Setting')
    work_setting_counts = df['Work Setting'].value_counts()
    work_setting_percentages = (work_setting_counts / total_graduates) * 100
    work_setting_str = ", ".join([f'**{setting}**: {count} ({percentage:.2f}%)' for setting, count, percentage in zip(work_setting_counts.index, work_setting_counts, work_setting_percentages)])
    st.markdown(work_setting_str)


        
if __name__ == "__main__":
    show_map()
