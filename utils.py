import os
import time
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import API_URL, APPLICATION_KEY, API_KEY, MAC, DATA_FOLDER, START_DATE, PAGE_TITLE, TIMEZONE

def update_data():
    os.makedirs(DATA_FOLDER, exist_ok=True)
    start_date = datetime.strptime(START_DATE, "%Y-%m-%d")
    start_date = start_date.replace(tzinfo=ZoneInfo(TIMEZONE))
    end_date = datetime.now(ZoneInfo(TIMEZONE)) # today - timedelta(days=1) # yesterday
    end_date_str = end_date.strftime("%Y-%m-%d")
    for date in pd.date_range(start=start_date, end=end_date):
        date_str = date.strftime("%Y-%m-%d")
        filepath = os.path.join(DATA_FOLDER, f"{date_str}.json")

        #print(date, end_date)
        if date_str == end_date_str:
            download_this_one = True
        elif os.path.exists(filepath):
            download_this_one = False
        else:
            download_this_one = True
        
        if not download_this_one:
            #print(f"{date_str} already exists, skipping.")
            date += timedelta(days=1)
            continue

        print(f"download for {date_str}...")
        params = {
            "application_key": APPLICATION_KEY,
            "api_key": API_KEY,
            "mac": MAC,
            "start_date": f"{date_str} 00:00:00",
            "end_date": f"{date_str} 23:59:59",
            "temp_unitid": 1, # celsius
            "wind_speed_unitid": 7, # km/h
            "rainfall_unitid": 12, # mm
            "pressure_unitid": 3, # hPa
            "solar_irradiance_unitid": 16, # W/m²
            "cycle_type": "5min",
            "call_back": "outdoor,rainfall,pressure,wind,solar_and_uvi"
        }
        try:
            response = requests.get(API_URL, params=params)
            response.raise_for_status()  # error if status is not 200
            #data = response.json()
            # save to a file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Data saved in {filepath}")
        except Exception as e:
            print(f"Error for {date_str}: {e}")
        
        # Move to the next day
        date += timedelta(days=1)
        # wait a bit to avoid hitting the API too hard
        time.sleep(20)

    print("Data is now up to date.")
    return end_date.strftime("%Y-%m-%d")

def celsius_to_color(temp):
    reference_points = {
        ( 40, 60) : '#8c0b00ff',
        ( 35, 40) : '#ff3300ff',
        ( 30, 35) : '#ff6600ff',
        ( 25, 30) : '#ff9933ff',
        ( 20, 25) : '#ffcc00ff',
        ( 15, 20) : '#ffff66ff',
        ( 10, 15) : '#ccff00ff',
        (  5, 10) : '#00ff99ff',
        (  0,  5) : '#00ffccff',
        ( -5,  0) : '#00ccffff',
        (-10, -5) : '#0099ccff',
        (-15,-10) : '#0036a3ff',
        (-20,-15) : '#0000ffff',
        (-25,-20) : '#000080ff',
        (-60,-25) : '#480080ff', 
    }
    if temp != temp:  # NaN check
        # rgb white
        return '#ffffff'
    
    if temp > 60 or temp < -60:
        # rgb white
        return '#ffffffff'

    for key in reference_points:
        if key[0] <= temp < key[1]:
            return reference_points[key]
    
    return '#ffffffff'

def rain_mm_to_color(rain_mm):
    reference_points = {
        ( 0, 0.1) :     ('#ffffffff', 'black'),
        ( 0.1, 1) :     ('#00ccffff', 'black'),
        ( 1, 5) :       ('#359cd8ff', 'black'),
        ( 5, 10) :      ('#2a70caff', 'black'),
        ( 10, 20) :     ('#213fc5ff', 'white'),
        ( 20, 50) :     ('#001e80ff', 'white'),
        ( 50, 100) :    ('#260080ff', 'white'), 
        (100, 10000) :  ('#8208a7ff', 'white'),
    }

    # nan check
    if rain_mm != rain_mm:
        return '#ffffffff', 'black'
    
    if rain_mm < 0:
        return '#ffffffff', 'black'
    
    for key in reference_points:
        if key[0] <= rain_mm < key[1]:
            return reference_points[key]
    
    return '#ffffffff', 'black'

def whm2_to_color(whm2):
    reference_points = {
        100 : "#d3d3d3ff",
        200 : "#e7e7e7ff",
        400 : '#ffe6d5ff',
        800 : '#ffccaaff',
        1600 : '#ffb380ff',
        2400 : '#ff9955ff',
        3200 : '#ff7f2aff',
        4000 : '#ff6600ff',
        4800 : '#d45500ff',
        5600 : '#aa4400ff',
        6400 : '#552200ff',
        10000 : '#2b1100ff',
    }
    if whm2 != whm2:  # NaN check
        return '#ffffffff', 'black'
    if whm2 < 0:
        return '#ffffffff', 'black'
    for key in reference_points:
        if whm2 < key:
            color_hex = reference_points[key]
            brightness = (int(color_hex[1:3], 16)*0.299 + int(color_hex[3:5], 16)*0.587 + int(color_hex[5:7], 16)*0.114) / 255
            text_color = 'black' if brightness > 0.5 else 'white'
            return color_hex, text_color

def wind_to_symbol(wind_directions, wind_strengths):
    # ⇗⇘⇙⇓⇒⇑⇐⇖
    symbols = {
        (337.5, 22.5):  'N',    # ⇑
        (22.5, 67.5):   'NE',     # ⇗
        (67.5, 112.5):  'E',    # →
        (112.5, 157.5): 'SE',   # ⇘
        (157.5, 202.5): 'S',   # ⇓
        (202.5, 247.5): 'SW',   # ⇙
        (247.5, 292.5): 'W',   # ⇐
        (292.5, 337.5): 'NW',   # ⇖
    }
    directions_counts = {}
    for k in symbols:
        directions_counts[symbols[k]] = 0
    for dir, strength in zip(wind_directions, wind_strengths):
        for key in symbols:
            if key[0] <= dir < key[1]:
                directions_counts[symbols[key]] += strength
                break
    most_frequent_direction = max(directions_counts, key=directions_counts.get)
    return most_frequent_direction

def live_html():
    content = "soon live here"
    content += f"<br>Last update : {datetime.now(ZoneInfo(TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}"
    return content

def days_table():
    available_days = os.listdir(DATA_FOLDER)
    available_days = [f[:-5] for f in available_days if f.endswith(".json")]
    available_days.sort(reverse=True)
    df = pd.DataFrame(
        columns=["Date", 
                 "completness", 
                 "Tmin", "Tmoy", "Tmax", 
                 "pluie", 
                 "watt-heure/m²", 
                 #"direction du vent", 
                 "vent moyen (km/h)", 
                 "rafale max (km/h)"], 
        index=available_days
    )
    df["Date"] = df.index
    full_data = full_data_df()
    print(full_data.columns)
    for date in df["Date"]:
        try:
            day_df = full_data[full_data["date"] == date]
            #print(day_df)
            # add length in complteness column
            df.loc[df["Date"] == date, "completness"] = day_df.shape[0]
            tmin = day_df["temperature"].min()
            tmoy = day_df["temperature"].mean()
            tmax = day_df["temperature"].max()
            rain_24h_at_00h = None
            hour_first_point = day_df["datetime"].iloc[0][-5:]
            date_day_before = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            if hour_first_point == "00:00":
                # replace the total of rain rates by the 24h total since it is more accurate
                rain_24h_at_00h = day_df["24_hours"].iloc[0]
                print(f"Using 24h rain at 00:00 for {date} : {rain_24h_at_00h}mm")
                df.loc[df["Date"] == date_day_before, "pluie"] = rain_24h_at_00h
            rain_this_day = day_df["rain_rate"].sum()
            rain_this_day = rain_this_day * (5 / 60.0) # convert from mm in 5min to mm in 1h
            solar_wh_per_m2 = int(day_df["solar"].sum() * (5 / 60.0)) # convert from W/m² in 5min to Wh/m² in 1h
            average_wind_speed = day_df["wind_speed"].mean()
            max_gust = int(day_df["wind_gust"].max())


            df.loc[df["Date"] == date, "Tmin"] = tmin
            df.loc[df["Date"] == date, "Tmoy"] = tmoy
            df.loc[df["Date"] == date, "Tmax"] = tmax
            if df.loc[df["Date"] == date, "pluie"].isna().all(): # only update if the 24h rain at 00:00 has not been used
                df.loc[df["Date"] == date, "pluie"] = rain_this_day
            df.loc[df["Date"] == date, "watt-heure/m²"] = solar_wh_per_m2
            df.loc[df["Date"] == date, "vent moyen (km/h)"] = average_wind_speed
            df.loc[df["Date"] == date, "rafale max (km/h)"] = max_gust

            #temperatures = list(data["outdoor"]["temperature"]["list"].values())
            #temperatures = [float(t) for t in temperatures]
            #rain_24h_at_00h = list(data['rainfall']['24_hours']['list'].values())[0]
            #rain_24h_at_00h = float(rain_24h_at_00h)
            ## TODO check if the 24h rainfall at 00h is correct, if not take the last 'daily' of the current day
            #last_daily_rain = float(list(data['rainfall']['daily']['list'].values())[-1])
            #solar_instants = list(data['solar_and_uvi']['solar']['list'].values())
            #solar_instants = [float(s) for s in solar_instants]
            #solar_wh_per_m2 = [v * (5 / 60.0) for v in solar_instants]
            #solar_wh_per_m2 = int(sum(solar_wh_per_m2))
            #wind_directions = list(data['wind']['10_minute_average_wind_direction']['list'].values())
            #wind_directions = [float(w) for w in wind_directions]
            #wind_strengths = list(data['wind']['wind_speed']['list'].values())
            #wind_strengths = [float(w) for w in wind_strengths]
            #gusts = list(data['wind']['wind_gust']['list'].values())
            #gusts = [float(g) for g in gusts]
            #df.loc[df["Date"] == date_previous_day, "pluie"] = rain_24h_at_00h
            #df.loc[df["Date"] == date, "watt-heure/m²"] = solar_wh_per_m2
            #if date == available_days[0]: # if it's the most recent day, 
            #    df.loc[df["Date"] == date, "pluie"] = last_daily_rain
            #wind_dir_symbol = wind_to_symbol(wind_directions, wind_strengths)
            #df.loc[df["Date"] == date, "direction du vent"] = wind_dir_symbol
            #df.loc[df["Date"] == date, "rafale max (km/h)"] = int(max(gusts))
        except Exception as e:
            print(f"Error processing data for {date}: {e}", full_data)
        date_day_before = date
    return df

def days_html():

    df = days_table()

    styled_df = df.style
    styled_df = styled_df.map(lambda x: f'background-color: {celsius_to_color(x)}; color: black;', subset=['Tmin'])
    styled_df = styled_df.map(lambda x: f'background-color: {celsius_to_color(x)}; color: black;', subset=['Tmoy'])
    styled_df = styled_df.map(lambda x: f'background-color: {celsius_to_color(x)}; color: black;', subset=['Tmax'])
    #styled_df = styled_df.map(lambda x: f'background-color: {TODO(x)}; color: black;', subset=['rafale max'])
    styled_df = styled_df.map(lambda x: f'background-color: {rain_mm_to_color(x)[0]}; color: {rain_mm_to_color(x)[1]};', subset=['pluie'])
    styled_df = styled_df.map(lambda x: f'background-color: {whm2_to_color(x)[0]}; color: {whm2_to_color(x)[1]};', subset=['watt-heure/m²'])
    
    round_dict = {
        'Tmin': '{:.1f}',
        'Tmoy': '{:.1f}',
        'Tmax': '{:.1f}',
        'rafale max': '{:.0f}',
        'pluie': '{:.1f}',
        'vent moyen (km/h)': '{:.1f}',
    }
    
    table_styles = [
        {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]},
        {'selector': 'th', 'props': [
            ('background-color', "#B1B1B1"), 
            ('color', 'black'), 
            ('padding', '8px'),
            ('position', 'sticky'),
            ('top', '0'),
            ('z-index', '10')  # keep header above other cells when scrolling
        ]},
        {'selector': 'td', 'props': [('padding', '4px 8px'), ('border-bottom', '1px solid #ddd')]},
    ]
    days_html_table = styled_df.format(round_dict).set_table_styles(table_styles).hide(axis='index').to_html()
    return days_html_table

def months_html():
    return ""

def full_data_df():
    list_df_of_days = []
    for file in sorted(os.listdir(DATA_FOLDER)):
        if not file.endswith(".json"):
            continue
        path = os.path.join(DATA_FOLDER, file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                j = json.load(f)
        except:
            continue
        data = j['data']
        if type(data) != dict:
            print(f"Data in {file} is not a dict, skipping.", data)
            continue
        list_df_this_day = []
        for sensor in data.keys():
            for measure in data[sensor].keys():
                if "list" in data[sensor][measure]:
                    index = list(data[sensor][measure]["list"].keys())
                    values = list(data[sensor][measure]["list"].values())
                    #values = [float(v) for v in values]
                    units = [data[sensor][measure]["unit"]] * len(values)
                    df = pd.DataFrame(index=index, data={measure: values, f"{measure}_unit": units})
                    # replace '-' by nans in the df
                    df.replace('-', float('nan'), inplace=True)
                    # convert to float
                    df[measure] = pd.to_numeric(df[measure], errors='coerce')
                    list_df_this_day.append(df)
        df_this_day = pd.concat(list_df_this_day, axis=1)
        list_df_of_days.append(df_this_day)
    df = pd.concat(list_df_of_days, axis=0)
    df['datetime'] = [datetime.fromtimestamp(int(i), tz=ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S") for i in df.index]
    df['date'] = [d[:10] for d in df['datetime']]
    df['datetime'] = [d[:-3] for d in df['datetime'].astype(str)]
    return df

def records_table():
    df = full_data_df()

    records = []
    measure_focus, unit_focus = "temperature", list(df["temperature_unit"])[0]
    tmin, tmin_index = df[measure_focus].min(), df[measure_focus].idxmin()
    tmin_time = df.loc[tmin_index, "datetime"]
    tmax, tmax_index = df[measure_focus].max(), df[measure_focus].idxmax()
    tmax_time = df.loc[tmax_index, "datetime"]
    record_tmin = {'name': "Température min", 'value': tmin, 'unit': unit_focus, 'date' : tmin_time}
    record_tmax = {'name': "Température max", 'value': tmax, 'unit': unit_focus, 'date' : tmax_time}

    # group dy date, take the mean if float, keep the first if not float
    df_group_days = df.groupby("date").agg(lambda x: x.mean() if x.dtype in ['float64', 'int64'] else x.iloc[0])
    # TODO drop incomplete days

    tminjour, tminjour_index = df_group_days[measure_focus].min(), df_group_days[measure_focus].idxmin()
    tmaxjour, tmaxjour_index = df_group_days[measure_focus].max(), df_group_days[measure_focus].idxmax()
    record_coldest_day = {'name': "Jour le plus froid", 'value': f'{tminjour:.1f}', 'unit': unit_focus, 'date': tminjour_index}
    record_warmest_day = {'name': "Jour le plus chaud", 'value': f'{tmaxjour:.1f}', 'unit': unit_focus, 'date': tmaxjour_index}

    measure_focus, unit_focus = "absolute", list(df["absolute_unit"])[0]
    pressure_min, pressure_min_index = df[measure_focus].min(), df[measure_focus].idxmin()
    pressure_min_time = df.loc[pressure_min_index, "datetime"]
    record_pressure_min = {'name': "Pression min", 'value': pressure_min, 'unit': unit_focus, 'date' : pressure_min_time}
    pressure_max, pressure_max_index = df[measure_focus].max(), df[measure_focus].idxmax()
    pressure_max_time = df.loc[pressure_max_index, "datetime"]
    record_pressure_max = {'name': "Pression max", 'value': pressure_max, 'unit': unit_focus, 'date' : pressure_max_time}

    measure_focus, unit_focus = "wind_gust", list(df["wind_gust_unit"])[0]
    wind_gust_max, wind_gust_max_index = df[measure_focus].max(), df[measure_focus].idxmax()
    wind_gust_max_time = df.loc[wind_gust_max_index, "datetime"]
    record_wind_gust_max = {'name': "Rafale de vent max", 'value': wind_gust_max, 'unit': unit_focus, 'date' : wind_gust_max_time}

    measure_focus, unit_focus = "1_hour", list(df["1_hour_unit"])[0]
    rain_1h_max, rain_1h_max_index = df[measure_focus].max(), df[measure_focus].idxmax()
    rain_1h_max_time = df.loc[rain_1h_max_index, "datetime"]
    record_rain_1h_max = {'name': "Pluie max en 1h", 'value': rain_1h_max, 'unit': unit_focus, 'date' : rain_1h_max_time}

    measure_focus, unit_focus = "24_hours", list(df["24_hours_unit"])[0]
    rain_24h_max, rain_24h_max_index = df[measure_focus].max(), df[measure_focus].idxmax()
    rain_24h_max_time = df.loc[rain_24h_max_index, "datetime"]
    record_rain_24h_max = {'name': "Pluie max en 24h", 'value': rain_24h_max, 'unit': unit_focus, 'date' : rain_24h_max_time}

    ## 💧 Pluviométrie glissante
    #for h in [1, 12, 24, 48, 240, 480]:
    #    val, start, end = rolling_max_rain(h)
    #    label = f"Pluviométrie max {h if h<24 else int(h/24)}{'h' if h<24 else ' jours'}"
    #    add_record(label, val, "mm", start, end)
    ## 🌬️ Vent
    #add_record("Rafale max", df["wind_gust"].max(), "km/h", df["wind_gust"].idxmax())
    #mean1h, t1h = rolling_mean(df["wind_speed"], 1, "max")
    #add_record("Vent moyen max 1h", mean1h, "km/h", t1h, t1h + timedelta(hours=1))

    # TODO
    # nombre max de jours de gel par hiver
    # nombre min de jours de gel par hiver
    # secheresse la plus longue
    # suite de jours avec pluie la plus longue
    # nombre de jours avec plus de 1mm de pluie par an
    # plus longue gelée continue
    # gelée la plus tardive
    # gelée la plus précoce
    # nuit la plus chaude

    records.append(record_tmin)
    records.append(record_tmax)
    records.append(record_coldest_day)
    records.append(record_warmest_day)
    records.append(record_wind_gust_max)
    records.append(record_rain_1h_max)
    records.append(record_rain_24h_max)
    records.append(record_pressure_min)
    records.append(record_pressure_max)

    records_df = pd.DataFrame(records)
    return records_df

def records_html():
    #df = pd.read_csv("data/records.csv")
    df = records_table()
    content = df.to_string(index=False, header=False)
    print(df)
    html_content = f"<pre>{content}</pre>"
    return html_content


def frame_html(live_html, days_html, months_html, records_html):
    html_content = f"""<!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{PAGE_TITLE}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background-color: #f4f4f4;
            }}

            h1 {{
                text-align: center;
                margin-bottom: 5px;
                color: #333;
            }}

            /* GRILLE PRINCIPALE - Modifiez ici pour changer la disposition */
            .grille {{
                display: grid;
                /* Définir le nombre et la taille des colonnes */
                grid-template-columns: 1fr 1fr; /* 2 colonnes égales */
                /* Définir le nombre et la taille des lignes */
                grid-template-rows: 150px 350px 350px; /* 3 lignes de 300px */
                /* Espacement entre les cases */
                gap: 20px;
                max-width: 1400px;
                margin: 0 auto;
            }}

            /* STYLE DES CASES */
            .case {{
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}

            .case h2 {{
                margin-bottom: 15px;
                color: #555;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 10px;
            }}

            /* Case avec le live - occupe 2 colonnes */
            .case-live {{
                grid-column: span 2; /* Occupe 2 colonnes */
                overflow-x: auto; /* Permet le scroll horizontal si nécessaire */
            }}

            .case-days {{
                grid-row: span 2;
                overflow-x: auto; /* allow for horizontal scrolling if needed */
            }}

            /* STYLE DU TABLEAU */
            .climato-days {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}

            .climato-days th {{
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }}

            .climato-days td {{
                padding: 2px;
                border-bottom: 1px solid #ddd;
            }}

            .climato-days tr:hover {{
                background-color: #f5f5f5;
            }}

            /* Cases vides */
            .case-vide {{
                display: flex;
                align-items: center;
                justify-content: center;
                color: #999;
                font-style: italic;
            }}

            /* RESPONSIVE - adapt to small screens */
            @media (max-width: 768px) {{
                .grille {{
                    grid-template-columns: 1fr; /* 1 seule colonne sur mobile */
                    grid-template-rows: auto;
                }}

                .case-days {{
                    grid-column: span 1;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>{PAGE_TITLE}</h1>

        <div class="grille">
            <div class="case case-live">
                {live_html}
            </div>

            <div class="case case-days">
                {days_html}
            </div>

            <div class="case case-months">
                {months_html}
            </div>

            <div class="case case-records">
                {records_html}
            </div>

        </div>
    </body>
    </html>"""
    return html_content