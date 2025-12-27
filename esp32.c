#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <WiFi.h>
#include <HTTPClient.h>

// LCD
LiquidCrystal_I2C lcd(0x27, 16, 2);

// WiFi credentials
const char* ssid = "poco m6 pro";
const char* password = "9926286156";

// Flask server endpoint
String serverURL = "http://10.119.115.225:5000/update";

const int MQ135_PIN = 34;

// pollutant struct
struct Pollutant {
  const char* name;
  float factor;
  float weight;
};

Pollutant pollutants[] = {
  {"NH3", 0.50, 1.0},
  {"NOx", 0.80, 1.0},
  {"Benz", 0.20, 0.8},
  {"Alc", 0.60, 0.8},
  {"CO2", 1.00, 1.5},
  {"CO",  0.70, 1.2},
  {"Smoke", 1.20, 1.4}
};

const int POLLUTANT_COUNT = sizeof(pollutants)/sizeof(pollutants[0]);

int ppmToSubIndex(float ppm) {
  if (ppm <= 200.0) return (int)((ppm / 200.0) * 50.0);
  else if (ppm <= 400.0) return (int)(51 + ((ppm - 200) / 200) * 49);
  else if (ppm <= 800.0) return (int)(101 + ((ppm - 400) / 400) * 99);
  else if (ppm <= 1200.0) return (int)(201 + ((ppm - 800) / 400) * 99);
  else if (ppm <= 2000.0) return (int)(301 + ((ppm - 1200) / 800) * 99);
  else return 500;
}

const char* subIndexToCategory(int idx) {
  if (idx <= 50) return "Good";
  else if (idx <= 100) return "Moderate";
  else if (idx <= 200) return "Unhealthy-S";
  else if (idx <= 300) return "Unhealthy";
  else if (idx <= 400) return "VeryBad";
  else return "Hazardous";
}

void setup() {
  Serial.begin(115200);

  // LCD
  lcd.init();
  lcd.backlight();
  lcd.print("AQI Monitor");
  delay(1500);
  lcd.clear();

  // WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
}

void loop() {
  int raw = analogRead(MQ135_PIN);
  float voltage = raw * 3.3 / 4095.0;
  float base_ppm = (raw / 4095.0) * 1000 + 400;

  int subIdx[POLLUTANT_COUNT];
  float estPPM[POLLUTANT_COUNT];
  float weighted = 0, totalW = 0;
  int maxIdx = 0;

  for (int i = 0; i < POLLUTANT_COUNT; i++) {
    estPPM[i] = base_ppm * pollutants[i].factor;
    subIdx[i] = ppmToSubIndex(estPPM[i]);
    weighted += subIdx[i] * pollutants[i].weight;
    totalW += pollutants[i].weight;
    if (subIdx[i] > maxIdx) maxIdx = subIdx[i];
  }

  int weightedAQI = weighted / totalW;
  const char* cat = subIndexToCategory(maxIdx);

  // --------------------
  // POST to Flask server
  // --------------------
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");

    String jsonPayload = "{";
    jsonPayload += "\"raw\":" + String(raw) + ",";
    jsonPayload += "\"voltage\":" + String(voltage, 3) + ",";
    jsonPayload += "\"base_ppm\":" + String(base_ppm, 1) + ",";
    jsonPayload += "\"aqi\":" + String(maxIdx) + ",";
    jsonPayload += "\"category\":\"" + String(cat) + "\"";
    jsonPayload += "}";

    int code = http.POST(jsonPayload);
    Serial.print("POST status: ");
    Serial.println(code);

    http.end();
  }

  // LCD display
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("AQI:");
  lcd.print(maxIdx);
  lcd.print(" ");
  lcd.print(cat);

  lcd.setCursor(0,1);
  lcd.print("VOC:");
  lcd.print((int)base_ppm);

  delay(2000);
}
