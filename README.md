
- ESP32 collects sensor data
- Backend processes / simulates AQI
- Frontend displays health-relevant insights

(Current version uses **controlled AQI ranges** for demo purposes.)

---

## 🛠️ Tech Stack

### Hardware
- ESP32
- Air quality sensor (e.g. MQ / SDS011 / CCS811 – configurable)

### Software
- HTML + Tailwind CSS (Frontend)
- JavaScript (Live updates)
- Flask (Backend – optional / future)
- REST API architecture

---

## 📊 AQI Logic (Current Version)

For demonstration:

| Parameter  | Range        |
|----------|--------------|
| Base PPM | 885 – 900    |
| AQI      | 265 – 270    |
| Category | Unhealthy    |

> ⚠️ Note:  
> AQI values are currently **simulated** to validate UI and system flow.  
> Real AQI calculation using EPA breakpoints is planned.

---

## 📂 Project Structure

