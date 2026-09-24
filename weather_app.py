"""Simple weather app: pick a city, see today's temperature and a 7-day forecast."""

import tkinter as tk
from tkinter import messagebox, ttk

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 10

DEFAULT_CITIES = [
    "London",
    "New York",
    "Tokyo",
    "Paris",
    "Sydney",
    "Mumbai",
    "Cairo",
    "Toronto",
]

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def describe_weather_code(code):
    return WEATHER_CODES.get(code, "Unknown")


def geocode_city(name):
    """Return (name, country, latitude, longitude) for the best match, or None."""
    response = requests.get(
        GEOCODE_URL,
        params={"name": name, "count": 1, "language": "en", "format": "json"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    results = response.json().get("results")
    if not results:
        return None
    match = results[0]
    return match["name"], match.get("country", ""), match["latitude"], match["longitude"]


def fetch_forecast(latitude, longitude):
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "forecast_days": 7,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Weather App")
        self.geometry("520x520")
        self.minsize(480, 480)

        self._build_layout()

    def _build_layout(self):
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="City:").pack(side="left")

        self.city_var = tk.StringVar(value=DEFAULT_CITIES[0])
        self.city_combo = ttk.Combobox(
            top_frame, textvariable=self.city_var, values=DEFAULT_CITIES
        )
        self.city_combo.pack(side="left", fill="x", expand=True, padx=8)
        self.city_combo.bind("<Return>", lambda _event: self.on_search())

        ttk.Button(top_frame, text="Search", command=self.on_search).pack(side="left")

        self.status_var = tk.StringVar(value="Pick a city and press Search.")
        ttk.Label(self, textvariable=self.status_var, padding=(10, 0)).pack(fill="x")

        # Today's summary
        today_frame = ttk.LabelFrame(self, text="Today", padding=10)
        today_frame.pack(fill="x", padx=10, pady=10)

        self.today_location_var = tk.StringVar(value="-")
        self.today_temp_var = tk.StringVar(value="-")
        self.today_desc_var = tk.StringVar(value="-")

        ttk.Label(today_frame, textvariable=self.today_location_var, font=("", 12, "bold")).pack(anchor="w")
        ttk.Label(today_frame, textvariable=self.today_temp_var, font=("", 24, "bold")).pack(anchor="w")
        ttk.Label(today_frame, textvariable=self.today_desc_var).pack(anchor="w")

        # 7-day forecast
        week_frame = ttk.LabelFrame(self, text="Next 7 Days", padding=10)
        week_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        columns = ("day", "condition", "high", "low")
        self.forecast_tree = ttk.Treeview(week_frame, columns=columns, show="headings", height=7)
        self.forecast_tree.heading("day", text="Day")
        self.forecast_tree.heading("condition", text="Condition")
        self.forecast_tree.heading("high", text="High")
        self.forecast_tree.heading("low", text="Low")
        self.forecast_tree.column("day", width=90, anchor="w")
        self.forecast_tree.column("condition", width=180, anchor="w")
        self.forecast_tree.column("high", width=70, anchor="center")
        self.forecast_tree.column("low", width=70, anchor="center")
        self.forecast_tree.pack(fill="both", expand=True)

    def on_search(self):
        city = self.city_var.get().strip()
        if not city:
            messagebox.showwarning("Missing city", "Please enter or select a city.")
            return

        self.status_var.set(f"Looking up {city}...")
        self.update_idletasks()

        try:
            location = geocode_city(city)
            if location is None:
                self.status_var.set(f"No results found for '{city}'.")
                return

            name, country, lat, lon = location
            data = fetch_forecast(lat, lon)
        except requests.RequestException as exc:
            self.status_var.set("Network error while fetching weather.")
            messagebox.showerror("Request failed", str(exc))
            return

        self._show_today(name, country, data)
        self._show_week(data)
        self.status_var.set(f"Showing weather for {name}, {country}.")

    def _show_today(self, name, country, data):
        current = data.get("current", {})
        temperature = current.get("temperature_2m")
        weather_code = current.get("weather_code")

        self.today_location_var.set(f"{name}, {country}")
        self.today_temp_var.set(f"{temperature}°C" if temperature is not None else "-")
        self.today_desc_var.set(describe_weather_code(weather_code))

    def _show_week(self, data):
        self.forecast_tree.delete(*self.forecast_tree.get_children())

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        codes = daily.get("weather_code", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])

        for date_str, code, high, low in zip(dates, codes, highs, lows):
            day_label = self._format_day(date_str)
            self.forecast_tree.insert(
                "", "end", values=(day_label, describe_weather_code(code), f"{high}°C", f"{low}°C")
            )

    @staticmethod
    def _format_day(date_str):
        import datetime

        try:
            date = datetime.date.fromisoformat(date_str)
            return DAY_NAMES[date.weekday()]
        except ValueError:
            return date_str


if __name__ == "__main__":
    WeatherApp().mainloop()
