from flask import Flask,render_template,url_for,redirect,request,jsonify
import requests
import random
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

app=Flask(__name__)

API_KEY = "db0a478238658cf3e859edc0e4be2753"
LAT, LON = "28.6139", "77.2090" 
BASE_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

@app.route("/update", methods=["POST"])
def update():
    data = request.json

    db.collection("air_quality").add({
        "aqi": data["aqi"],
        "pm25": data["pm25"],
        "pm10": data["pm10"],
        "voc": data["voc"],
        "timestamp": datetime.utcnow()
    })

    return {"status": "saved"}

from datetime import timedelta

@app.route("/api/history")
def history():
    since = datetime.utcnow() - timedelta(hours=24)

    docs = (
        db.collection("air_quality")
        .where("timestamp", ">=", since)
        .order_by("timestamp")
        .stream()
    )

    result = []
    for d in docs:
        r = d.to_dict()
        result.append({
            "time": r["timestamp"].strftime("%H:%M"),
            "pm25": r["pm25"],
            "pm10": r["pm10"],
            "aqi": r["aqi"]
        })

    return result




# app.py (add these helper functions)

def get_aqi_level(aqi: float | int) -> str:
    """
    Convert a numeric AQI value into a textual category.
    Uses common breakpoints (0-500).
    """
    try:
        aqi = float(aqi)
    except (TypeError, ValueError):
        return "Unknown"

    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    if aqi <= 500:
        return "Hazardous"
    return "Unknown"

def get_aqi_color(level: str) -> str:
    """
    Map textual AQI level to a color hex string.
    Level should be one of: Good, Moderate, Unhealthy, Very Unhealthy, Hazardous.
    """
    if not level:
        return "#9ca3af"  # neutral gray

    level = str(level).strip().lower()
    mapping = {
        "good": "#16a34a",           # green
        "moderate": "#f59e0b",       # amber/yellow
        "unhealthy": "#ef4444",      # red
        "very unhealthy": "#8b5cf6", # purple
        "very_unhealthy": "#8b5cf6", # alternative key
        "hazardous": "#7f1d1d",      # maroon/dark red
        "unknown": "#9ca3af"
    }
    return mapping.get(level, "#9ca3af")

def get_aqi_color_from_value(aqi_value) -> str:
    """Convenience: numeric AQI -> category -> hex color"""
    level = get_aqi_level(aqi_value)
    return get_aqi_color(level)


# def get_latest_sensor_data():
#     return {
#         "aqi": random.randint(50, 200),
#         "pm25": random.randint(10, 150),
#         "pm10": random.randint(20, 250),
#         "voc": random.randint(50, 400),
#         "temp": random.randint(20, 35),
#         "humidity": random.randint(20, 90),
#         "timestamp": datetime.now().strftime("%H:%M:%S"),
#         "level": "Unhealthy"  # temporary value
#     }

def calculate_aqi(C, breakpoints):
    """
    Generic AQI calculation using US EPA formula.
    """
    if C is None:
        return None

    for Clow, Chigh, Ilow, Ihigh in breakpoints:
        if Clow <= C <= Chigh:
            return round(
                ((Ihigh - Ilow) / (Chigh - Clow)) * (C - Clow) + Ilow
            )

    return None


def get_real_aqi(pm25, pm10):
    """
    Calculate real AQI using US EPA standard.
    Final AQI = max(AQI_PM2.5, AQI_PM10)
    """
    # PM2.5 breakpoints (µg/m³, 24-hr)
    PM25_BREAKPOINTS = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]

    # PM10 breakpoints (µg/m³, 24-hr)
    PM10_BREAKPOINTS = [
        (0, 54, 0, 50),
        (55, 154, 51, 100),
        (155, 254, 101, 150),
        (255, 354, 151, 200),
        (355, 424, 201, 300),
        (425, 504, 301, 400),
        (505, 604, 401, 500),
    ]


    aqi_pm25 = calculate_aqi(pm25, PM25_BREAKPOINTS)
    aqi_pm10 = calculate_aqi(pm10, PM10_BREAKPOINTS)

    values = [v for v in [aqi_pm25, aqi_pm10] if v is not None]
    return max(values) if values else None




def get_latest_sensor_data():
    try:
        # --- Air Pollution API ---
        aqi_url = (
            f"http://api.openweathermap.org/data/2.5/air_pollution"
            f"?lat={LAT}&lon={LON}&appid={API_KEY}"
        )
        aqi_res = requests.get(aqi_url, timeout=5).json()

        pollution = aqi_res["list"][0]
        components = pollution["components"]

        pm25 = components.get("pm2_5")
        pm10 = components.get("pm10")
        voc = components.get("nh3")  # proxy

        # 🔥 REAL AQI (US EPA FORMULA)
        real_aqi = get_real_aqi(pm25, pm10)

        # --- Weather API ---
        weather_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
        )
        weather_res = requests.get(weather_url, timeout=5).json()

        return {
            "city": weather_res["name"],
            "country": weather_res["sys"]["country"],
            "aqi": real_aqi,
            "pm25": pm25,
            "pm10": pm10,
            "voc": voc,
            "temp": weather_res["main"]["temp"],
            "humidity": weather_res["main"]["humidity"],
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

    except Exception as e:
        print("AQI error:", e)
        return {
            "city": "Unknown",
            "country": "Unknown",
            "aqi": None,
            "pm25": None,
            "pm10": None,
            "voc": None,
            "temp": None,
            "humidity": None,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }




def get_forecast():
    return {
        "aqi": 95,
        "level": "Moderate"
    }

def choose_precaution(level):
    level = level.lower()

    if level == "good":
        return "It’s a great day to go outside!"
    if level == "moderate":
        return "Air quality is acceptable; sensitive individuals should take care."
    if level == "unhealthy":
        return "Wear an N95 mask outdoors and limit outdoor exposure."
    if level == "very unhealthy":
        return "Avoid going outside and keep doors/windows closed."
    if level == "hazardous":
        return "Stay indoors. Outdoor exposure is extremely dangerous."

    return "Air quality data unavailable."

def get_history_data():
    now = datetime.now()
    history = []

    for i in range(24):
        history.append({
            "timestamp": now - timedelta(hours=24 - i),
            "pm25": random.randint(10, 180),
            "pm10": random.randint(20, 250)
        })

    return history

def get_device_status():
    return {
        "status": "online",
        "lastSeen": datetime.now().strftime("%H:%M:%S"),
        "signalStrength": -65,
        "battery": 78,
        "sensorStatus": {
            "pm": True,
            "voc": True,
            "dht": True
        }
    }

def get_forecast_6h():
    now = datetime.now()
    forecast = []

    base_aqi = random.randint(50, 150)

    for i in range(6):
        forecast.append({
            "timestamp": now + timedelta(hours=i),
            "aqi": base_aqi + random.randint(-20, 20)
        })

    return forecast



# @app.route("/")

#     # temp commentout lines for testing the api key 
# # def home():
#         # dashboard = get_latest_sensor_data()
#         # device = get_device_status()
#         # history = get_history_data()
#         # forecast = get_forecast_6h()

#         # Format history timestamps
#         # for h in history:
#         #     h["time"] = h["timestamp"].strftime("%H:%M")

#         # trend = "Rising" if forecast[-1]["aqi"] > forecast[0]["aqi"] else "Falling"

        
#         # city = "Bhopal"  
#         # params = {
#         #     "key": API_KEY,
#         #     "q": city,
#         #     "aqi": "yes"
#         # }

# #     weather_res = requests.get("https://api.weatherapi.com/v1/current.json", params=params).json()

# #     weather = {
# #         "city": weather_res["location"]["name"],
# #         "country": weather_res["location"]["country"],
# #         "temp_c": weather_res["current"]["temp_c"],
# #         "condition": weather_res["current"]["condition"]["text"],
# #         "icon": weather_res["current"]["condition"]["icon"]
# #     }

#         # return render_template(
#         #     "home.html"
#             # data=dashboard,
#             # status=device,
#             # data_history=history,
#             # forecast=forecast,
#             # next_hour_aqi=forecast[0]["aqi"],
#             # trend=trend,

#             # 🔥 REQUIRED (your missing piece)
#             # weather=weather
                #)
@app.route("/")
def home():
    # ===== SAFE LOCAL DATA (NO EXTERNAL API) =====
    dashboard = get_latest_sensor_data()
    device = get_device_status()
    history = get_history_data()
    forecast = get_forecast_6h()

    # Format history timestamps
    for h in history:
        h["time"] = h["timestamp"].strftime("%H:%M")

    # Forecast trend
    trend = "Rising" if forecast[-1]["aqi"] > forecast[0]["aqi"] else "Falling"

    # ===== LOCAL WEATHER FALLBACK (NO API CALL) =====
    weather = {
        "city": "Delhi",
        "country": "India",
        "temp_c": dashboard["temp"],
        "condition": "Clear",
        "icon": "https://openweathermap.org/img/wn/01d@2x.png"
    }

    return render_template(
        "home.html",
        data=dashboard,
        status=device,
        data_history=history,
        forecast=forecast,
        next_hour_aqi=forecast[0]["aqi"],
        trend=trend,
        weather=weather
    )

# @app.route("/")
# def home():

#     # ===== PLACEHOLDERS (SAFE) =====
#     dashboard = get_latest_sensor_data()
#     device = get_device_status()
#     history = get_history_data()
#     forecast = get_forecast_6h()

#     for h in history:
#         h["time"] = h["timestamp"].strftime("%H:%M")

#     trend = "Rising" if forecast[-1]["aqi"] > forecast[0]["aqi"] else "Falling"


#     # ===== WEATHER API =====
#     city = "Bhopal"
#     params = {
#         "key": API_KEY,
#         "q": city,
#         "aqi": "yes"
#     }

#     # weather_res = requests.get(
#     #     "https://api.openweathermap.org/data/2.5/air_pollution",
#     #     params=params
#     # ).json()

#     # weather = {
#     #     "city": weather_res["location"]["name"],
#     #     "country": weather_res["location"]["country"],
#     #     "temp_c": weather_res["current"]["temp_c"],
#     #     "condition": weather_res["current"]["condition"]["text"],
#     #     "icon": weather_res["current"]["condition"]["icon"]
#     # }

#     return render_template(
#         "home.html",
#         data=dashboard,
#         status=device,
#         data_history=history,
#         forecast=forecast,
        
#         trend=trend,
#         # weather=weather
#     )

        
def dashboard():
    # 1. Get Air Pollution Data
    aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={LAT}&lon={LON}&appid={API_KEY}"
    aqi_res = requests.get(aqi_url).json()
    
    # 2. Get Current Weather Data (for Temp, Humidity, Icon)
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
    weather_res = requests.get(weather_url).json()

    # Mapping OpenWeather 1-5 scale to Colors and Descriptions
    # 1=Good, 2=Fair, 3=Moderate, 4=Poor, 5=Very Poor
    aqi_map = {
        1: {"level": "Good", "color": "#22c55e", "precaution": "Air quality is satisfactory. Enjoy outdoor activities!"},
        2: {"level": "Fair", "color": "#eab308", "precaution": "Acceptable air quality; sensitive people should limit exertion."},
        3: {"level": "Moderate", "color": "#f97316", "precaution": "Moderate pollution. Sensitive groups should stay indoors."},
        4: {"level": "Poor", "color": "#ef4444", "precaution": "Unhealthy air. Wear a mask if going outside."},
        5: {"level": "Very Poor", "color": "#a855f7", "precaution": "Hazardous! Avoid all outdoor physical activities."}
    }

    raw_aqi = aqi_res['list'][0]['main']['aqi']
    aqi_info = aqi_map.get(raw_aqi)

    # Prepare data for Template
    context = {
        "aqi_color": aqi_info['color'],
        "precaution": aqi_info['precaution'],
        "data": {
            "aqi": raw_aqi,
            "level": aqi_info['level'],
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "pm25": aqi_res['list'][0]['components']['pm2_5'],
            "pm10": aqi_res['list'][0]['components']['pm10'],
            "voc": aqi_res['list'][0]['components'].get('nh3', 'N/A'), # OWM doesn't give 'VOC', using NH3 as proxy
            "temp": weather_res['main']['temp'],
            "humidity": weather_res['main']['humidity']
        },
        "weather": {
            "city": weather_res['name'],
            "country": weather_res['sys']['country'],
            "temp_c": weather_res['main']['temp'],
            "condition": weather_res['weather'][0]['description'].title(),
            "icon": f"https://openweathermap.org/img/wn/{weather_res['weather'][0]['icon']}@2x.png"
        }
    }

    return render_template('Dashboard.html', **context)


@app.route("/api/live")
def live():
    return {
        "aqi": 87,
        "pm25": 34,
        "pm10": 78,
        "voc": 102,
        "time": "2025-11-20 14:20"
    }

@app.route("/api/predict")
def predict():
    return {
        "predicted_aqi": 120,
        "summary": "AQI expected to rise. Avoid going out."
    }

@app.route("/Awareness")
def awareness():
    return render_template("Awareness.html")

# @app.route("/Dashboard")

# def dashboard():
#     data = get_latest_sensor_data()  # your function
#     next_hour = get_forecast()

#     # If data already contains textual level, use it; otherwise derive from numeric aqi
#     data_level = data.get("level") if data.get("level") else get_aqi_level(data.get("aqi"))
#     precaution = choose_precaution(data_level)  # implement or use a static mapping

#     aqi_color = get_aqi_color(data_level)
#     forecast_color = get_aqi_color_from_value(next_hour.get("aqi")) if next_hour and next_hour.get("aqi") is not None else "#9ca3af"

#     return render_template(
#         "Dashboard.html",
#         data=data,
#         next_hour=next_hour,
#         aqi_color=aqi_color,
#         forecast_color=forecast_color,
#         precaution=precaution
        

#     )
@app.route("/settings")
def settings_page():
    return render_template("settings.html")

# @app.route("/dashboard")
# def dashboard():

#     city = request.args.get("city", "Bhopal")  # default for testing

#     params = {
#         "key": API_KEY,
#         "q": city,
#         "aqi": "yes"
#     }

#     response = requests.get(BASE_URL, params=params)
#     data = response.json()

#     # ---- Extract AQI ----
#     aqi = int(data["current"]["air_quality"]["pm2_5"])   # Using PM2.5 as AQI approximation

#     # ---- Determine AQI Level ----
#     if aqi <= 50:
#         level = "Good"
#         aqi_color = "#4CAF50"
#         precaution = "No precautions needed."
#     elif aqi <= 100:
#         level = "Moderate"
#         aqi_color = "#FFEB3B"
#         precaution = "Sensitive individuals should reduce outdoor activity."
#     elif aqi <= 150:
#         level = "Unhealthy for sensitive groups"
#         aqi_color = "#FF9800"
#         precaution = "Limit prolonged outdoor exertion."
#     else:
#         level = "Unhealthy"
#         aqi_color = "#F44336"
#         precaution = "Avoid outdoor activities."

#     # ---- Forecast dummy (WeatherAPI free tier has limited AQI forecast) ----
#     next_hour = {
#         "aqi": aqi + 5,
#         "level": level
#     }
#     forecast_color = aqi_color

#     # ---- Build final dictionary that matches your HTML ----
#     final_data = {
#         "timestamp": data["location"]["localtime"],
#         "aqi": aqi,
#         "level": level,
#         "pm25": data["current"]["air_quality"]["pm2_5"],
#         "pm10": data["current"]["air_quality"]["pm10"],
#         "voc": data["current"]["air_quality"].get("co", 0),
#         "temp": data["current"]["temp_c"],
#         "humidity": data["current"]["humidity"],
#     }

#     return render_template(
#         "dashboard.html",
#         data=final_data,
#         precaution=precaution,
#         next_hour=next_hour,
#         aqi_color=aqi_color,
#         forecast_color=forecast_color
#     )
latest_esp32_data = {}

@app.route("/update", methods=["POST"])
def update_from_esp32():
    global latest_esp32_data

    print("----- NEW REQUEST -----")
    print("Raw data:", request.data)
    print("JSON:", request.get_json())
    print("------------------------")

    latest_esp32_data = request.get_json()
    return {"status": "ok"}

@app.route("/api/trends")
def api_trends():
    return jsonify([
        {"time": "10:00", "pm25": 65, "pm10": 92},
        {"time": "11:00", "pm25": 70, "pm10": 98},
        {"time": "12:00", "pm25": 80, "pm10": 110}
    ])


@app.route("/api/esp32")
def api_esp32():
    return latest_esp32_data


@app.route("/esp32")
def esp32_page():
    return render_template("esp32.html")


@app.route("/DeviceStatus")
def device_status():
    status = {


        
        "status": "online",
        "lastSeen": "12:45 PM",
        "signalStrength": -55,
        "battery": 78,
        "sensorStatus": {
            "pm": True,
            "voc": False,
            "dht": True
        }
    }
    return render_template("DeviceStatus.html", status=device_status)

@app.route("/Trends")
def trends_page():
    history = get_history_data()

    formatted = []
    for d in history:
        formatted.append({
            "time": d["timestamp"].strftime("%H:%M"),
            "pm25": d["pm25"],
            "pm10": d["pm10"]
        })

    return render_template("Trends.html", data=formatted)

@app.route("/forecast")
def forecast_page():

    forecast_points = get_forecast_6h()   # your function → returns list of dicts

    formatted = []
    for p in forecast_points:
        formatted.append({
            "time": p["timestamp"].strftime("%H:%M"),
            "aqi": p["aqi"]
        })

    # Trend comparison
    trend = "Rising" if formatted[-1]["aqi"] > formatted[0]["aqi"] else "Falling"

    return render_template(
        "forecast.html",
        forecast=formatted,
        next_hour_aqi=formatted[0]["aqi"],
        trend=trend
    )



# Serve the settings page
@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/weather")
def get_weather():
    city = request.args.get("city")

    if not city:
        return "City parameter is required"

    params = {"key": API_KEY, "q": city, "aqi": "no"}
    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        return "API request failed"

    data = response.json()

    weather = {
        "city": data["location"]["name"],
        "country": data["location"]["country"],
        "temp_c": data["current"]["temp_c"],
        "condition": data["current"]["condition"]["text"],
        "icon": data["current"]["condition"]["icon"]
    }

    return render_template("Dashboard.html", weather=weather)


if __name__=="__main__":

    test_vals = [10, 55, 120, 250, 420, None, "abc"]
    for t in test_vals:
        print(t, get_aqi_level(t), get_aqi_color_from_value(t))

    app.run(host="0.0.0.0",port=5000,debug=True)