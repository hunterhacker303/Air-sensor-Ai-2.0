from flask import Flask, render_template
import requests
from datetime import datetime

app = Flask(__name__)

API_KEY = 'YOUR_OPENWEATHERMAP_API_KEY'
LAT, LON = "28.6139", "77.2090" # Example: New Delhi. Change to your location.

@app.route('/')
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