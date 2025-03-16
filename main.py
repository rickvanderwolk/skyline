import time
import board
import neopixel
from random import randint, choice
import threading
import random
from math import floor
import requests
import datetime
import os
import json
import copy

MATRIX_WIDTH = 32
MATRIX_HEIGHT = 8
NUM_LEDS = MATRIX_WIDTH * MATRIX_HEIGHT
DATA_PIN = board.D18
SAFE_MAX_LEDS = int(NUM_LEDS * 0.25)
WEATHER_UPDATE_INTERVAL = 300
OPEN_WEATHER_API_BASE_URL = "https://api.openweathermap.org/data/2.5/weather?"
OPEN_WEATHER_API_CITY = "<your-city>"
OPEN_WEATHER_API_KEY = "<your-open-weather-api-key>"
CACHE_FILE = "weather_cache.json"

pixels = neopixel.NeoPixel(DATA_PIN, NUM_LEDS, auto_write=False, brightness=0.25)
current_effect_thread = None
current_effect_name = None
stop_event = threading.Event()
last_weather_update = 0

def get_led_index(x, y):
    if x % 2 == 0:
        return x * MATRIX_HEIGHT + y
    else:
        return x * MATRIX_HEIGHT + (MATRIX_HEIGHT - 1 - y)

def safe_led_limit(requested_leds):
    return min(SAFE_MAX_LEDS, max(0, requested_leds))

def fade_out_all(steps=50, delay=0.02):
    print("Fading out all LEDs...")
    for step in range(steps):
        for i in range(NUM_LEDS):
            r, g, b = pixels[i]
            pixels[i] = (int(r * (1 - step / steps)), int(g * (1 - step / steps)), int(b * (1 - step / steps)))
        pixels.show()
        time.sleep(delay)

def simulate_christmas(variables):
    min_leds = 5
    max_leds = safe_led_limit(15)
    active_leds = {}

    print(f"Simulating Christmas with min {min_leds}, max {max_leds} LEDs")

    while not stop_event.is_set():
        update_leds(active_leds, min_leds, max_leds, lambda: choice([(255, 0, 0), (0, 255, 0)]), batch_size=8)
        time.sleep(0.1)

def simulate_rain(variables):
    intensity = safe_led_limit(variables.get("intensity", 50))
    thunder_probability = variables.get("thunder_probability", 5)
    print(f"Simulating rain met intensity {intensity} en thunder_probability {thunder_probability}")

    raindrops = [
        (randint(0, MATRIX_WIDTH - 1), randint(0, MATRIX_HEIGHT - 1))
        for _ in range(intensity)
    ]

    while not stop_event.is_set():
        pixels.fill((0, 0, 0))

        new_raindrops = []
        for x, y in raindrops:
            if y + 1 < MATRIX_HEIGHT:
                index = get_led_index(x, y + 1)
                pixels[index] = (randint(0, 5), randint(0, 5), randint(50, 255))
                new_raindrops.append((x, y + 1))
            else:
                index = get_led_index(x, 0)
                pixels[index] = (randint(0, 5), randint(0, 5), randint(50, 255))
                new_raindrops.append((randint(0, MATRIX_WIDTH - 1), 0))

        raindrops = new_raindrops

        if variables.get("weather_condition") == "Thunder" and random.randint(1, 250) == 1:
            print("Thunderstorm flash!")
            for _ in range(random.randint(3, 7)):
                flash_leds = random.sample(range(NUM_LEDS), random.randint(int(NUM_LEDS * 0.5), NUM_LEDS))
                for i in range(NUM_LEDS):
                    if i in flash_leds:
                        pixels[i] = (255, 255, 255)
                    else:
                        pixels[i] = (0, 0, 0)
                pixels.show()
                time.sleep(random.uniform(0.05, 0.2))
                pixels.fill((0, 0, 0))
                pixels.show()
                time.sleep(random.uniform(0.1, 0.5))

        pixels.show()
        time.sleep(0.1)

def simulate_snow(variables):
    intensity = safe_led_limit(variables.get("intensity", 30))
    print(f"Simulating snow with intensity {intensity}")
    snowflakes = []
    active_columns = set()

    while not stop_event.is_set():
        if len(snowflakes) < intensity:
            x = randint(0, MATRIX_WIDTH - 1)
            if x not in active_columns:
                y = 0
                snowflakes.append((x, y))
                active_columns.add(x)

        new_snowflakes = []
        pixels.fill((0, 0, 0))

        for x, y in snowflakes:
            if y < MATRIX_HEIGHT - 1:
                index = get_led_index(x, y)
                pixels[index] = (255, 255, 255)
                new_snowflakes.append((x, y + 1))
            else:
                index = get_led_index(x, y)
                pixels[index] = (255, 255, 255)
                active_columns.discard(x)

        snowflakes = new_snowflakes
        pixels.show()
        time.sleep(0.2)

def simulate_fireworks(variables):
    intensity = safe_led_limit(variables.get("intensity", 30))
    max_leds = safe_led_limit(int(NUM_LEDS))
    active_leds = 0
    print(f"Simulating fireworks with intensity {intensity}")
    print(f"Simulating max leds {max_leds}")

    while not stop_event.is_set():
        active_leds = sum(1 for r, g, b in pixels if r > 0 or g > 0 or b > 0)

        for i in range(NUM_LEDS):
            r, g, b = pixels[i]
            if r > 0 or g > 0 or b > 0:
                active_leds -= 1
            pixels[i] = (max(0, r - 15), max(0, g - 20), max(0, b - 20))

        if active_leds < max_leds and random.randint(0, 100) < intensity:
            index = random.randint(0, NUM_LEDS - 1)
            if all(c == 0 for c in pixels[index]):
                hue = random.random()
                r, g, b = hsv_to_rgb(hue, 1.0, 255)
                pixels[index] = (int(r), int(g), int(b))
                active_leds += 1

        pixels.show()
        time.sleep(0.05)

def hsv_to_rgb(h, s, v):
    if s == 0.0:
        return (v, v, v)
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = int(v * (1.0 - s))
    q = int(v * (1.0 - s * f))
    t = int(v * (1.0 - s * (1.0 - f)))
    i %= 6
    if i == 0:
        return (v, t, p)
    if i == 1:
        return (q, v, p)
    if i == 2:
        return (p, v, t)
    if i == 3:
        return (p, q, v)
    if i == 4:
        return (t, p, v)
    if i == 5:
        return (v, p, q)

def simulate_lighting(variables):
    intensity = safe_led_limit(variables.get("intensity", 10))
    max_active_leds = variables.get("max_active_leds", 5)
    fade_speed = 0.5
    min_burn_time = 10
    max_burn_time = 30
    colors = variables.get("colors", [(255, 255, 255)])
    color_weights = variables.get("color_weights", [100 / len(colors)] * len(colors))

    if len(colors) != len(color_weights):
        raise ValueError("Each color must have a corresponding weight.")

    led_brightness = [0] * NUM_LEDS
    led_burn_times = [0] * NUM_LEDS
    led_states = ["off"] * NUM_LEDS
    led_colors = [(0, 0, 0)] * NUM_LEDS

    print(f"Simulating lighting with intensity {intensity}")
    print(f"Max active LEDs: {max_active_leds}")
    print(f"Available colors: {colors} with weights {color_weights}")

    while not stop_event.is_set():
        active_leds = sum(1 for state in led_states if state != "off")

        for i in range(NUM_LEDS):
            if led_states[i] == "fading_in":
                led_brightness[i] += fade_speed
                if led_brightness[i] >= 255:
                    led_brightness[i] = 255
                    led_states[i] = "burning"
                    led_burn_times[i] = random.randint(min_burn_time * 20, max_burn_time * 20)
            elif led_states[i] == "burning":
                if led_burn_times[i] > 0:
                    led_burn_times[i] -= 1
                else:
                    led_states[i] = "fading_out"
            elif led_states[i] == "fading_out":
                led_brightness[i] -= fade_speed
                if led_brightness[i] <= 0:
                    led_brightness[i] = 0
                    led_states[i] = "off"

            if led_states[i] != "off":
                base_color = led_colors[i]
                pixels[i] = (
                    int((base_color[0] / 255) * led_brightness[i]),
                    int((base_color[1] / 255) * led_brightness[i]),
                    int((base_color[2] / 255) * led_brightness[i]),
                )
            else:
                pixels[i] = (0, 0, 0)

        if active_leds < max_active_leds and random.randint(0, 100) < intensity:
            index = random.randint(0, NUM_LEDS - 1)
            if led_states[index] == "off":
                led_states[index] = "fading_in"
                led_brightness[index] = 0
                led_colors[index] = random.choices(colors, weights=color_weights, k=1)[0]

        pixels.show()
        time.sleep(0.05)

def simulate_christmas(variables):
    variables = {
        "intensity": 100,
        "max_active_leds": 7,
        "colors": [(255, 0, 0), (0, 255, 0)],
        "color_weights": [60, 40]
    }
    simulate_lighting(variables)

def simulate_night(variables):
    variables = {
        "intensity": 100,
        "max_active_leds": 5,
        "colors": [(0, 0, 20), (0, 0, 40), (0, 0, 100), (0, 0, 255), (50, 0, 50), (255, 255, 255)],
        "color_weights": [15, 15, 15, 20, 30, 5]
    }
    simulate_lighting(variables)

def simulate_day(variables):
    cloud_percentage = variables.get("cloud_percentage", 0)

    white_weight = max(0.01, cloud_percentage / 100)
    yellow_weight = max(0.01, 1.0 - white_weight)

    total_weight = white_weight + yellow_weight
    white_weight /= total_weight
    yellow_weight /= total_weight

    variables["max_active_leds"] = int(20 + (50 - 20) * (1 - cloud_percentage / 100))

    variables["intensity"] = 100
    variables["colors"] = [(255, 223, 0), (200, 200, 200)]
    variables["color_weights"] = [yellow_weight, white_weight]

    simulate_lighting(variables)

def simulate_sunrise(variables):
    percentage = variables.get("sunrise_percentage", 0)
    percentage = max(0.0, min(1.0, percentage))
    transition_row = floor((1.0 - percentage) * MATRIX_HEIGHT)

    for y in range(MATRIX_HEIGHT):
        for x in range(MATRIX_WIDTH):
            index = get_led_index(x, y)

            if y >= transition_row:
                r = 255
                g = 223
                b = 0
            else:
                r = 0
                g = 0
                b = 139

            pixels[index] = (r, g, b)

    pixels.show()
    time.sleep(0.1)

def simulate_sunset(variables):
    percentage = variables.get("sunset_percentage", 0)
    percentage = max(0.0, min(1.0, percentage))
    transition_row = floor(percentage * MATRIX_HEIGHT)

    for y in range(MATRIX_HEIGHT):
        for x in range(MATRIX_WIDTH):
            index = get_led_index(x, y)

            if y >= transition_row:
                r = 255
                g = 223
                b = 0
            else:
                r = 0
                g = 0
                b = 139

            pixels[index] = (r, g, b)

    pixels.show()
    time.sleep(0.1)

def variables_changed(current_vars, new_vars, keys_to_check):
    for key in keys_to_check:
        if current_vars.get(key) != new_vars.get(key):
            return True
    return False

def run_effect(effect_name, variables):
    global current_effect_thread, current_effect_name, current_variables, stop_event, pixels

    if current_effect_name != effect_name or variables_changed(current_variables, variables, ["brightness", "cloud_percentage", "sunrise_percentage", "sunset_percentage", "intensity", "weather_condition"]):
        print("--------------------------------------------")
        print(f"Switching to effect: {effect_name}")
        print("--------------------------------------------")
        print("Variables:")
        for key, value in variables.items():
            print(f"\t{key}: {value}")

        fadeOut = variables.get("fade_out", True)
        fadeOutSteps = variables.get("fade_out_steps", 50)
        fadeOutDelay = variables.get("fade_out_delay", 0.02)
        brightness = variables.get("brightness", 1.0)

        stop_event.set()
        if current_effect_thread:
            current_effect_thread.join()

        if fadeOut:
            fade_out_all(steps=fadeOutSteps, delay=fadeOutDelay)
        pixels.brightness = brightness

        stop_event.clear()
        current_effect_name = effect_name
        current_variables = copy.deepcopy(variables)
        effect_function = globals()[effect_name]
        current_effect_thread = threading.Thread(target=effect_function, args=(variables,))
        current_effect_thread.start()

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            try:
                cache = json.load(file)
                cache["data"]["weather_data_timestamp"] = datetime.datetime.fromisoformat(cache["data"]["weather_data_timestamp"])
                cache["data"]["sunrise"] = datetime.datetime.fromisoformat(cache["data"]["sunrise"])
                cache["data"]["sunset"] = datetime.datetime.fromisoformat(cache["data"]["sunset"])
                cache["weather_data_timestamp"] = datetime.datetime.fromisoformat(cache["weather_data_timestamp"])
                return cache
            except (json.JSONDecodeError, ValueError):
                return None
    return None

def save_cache(data, weather_data_timestamp):
    cache = {
        "data": {
            "weather_data_timestamp": data["weather_data_timestamp"].isoformat(),
            "sunrise": data["sunrise"].isoformat(),
            "sunset": data["sunset"].isoformat(),
            "weather_condition": data["weather_condition"],
            "cloud_percentage": data["cloud_percentage"]
        },
        "weather_data_timestamp": weather_data_timestamp.isoformat()
    }
    with open(CACHE_FILE, "w") as file:
        json.dump(cache, file)

def get_weather_data():
    cache = load_cache()
    weather_data_timestamp = datetime.datetime.now()

    if cache and (weather_data_timestamp - cache["weather_data_timestamp"]).total_seconds() < WEATHER_UPDATE_INTERVAL:
        print("Use cache")
        return cache["data"]

    print("Use API")
    url = OPEN_WEATHER_API_BASE_URL + "q=" + OPEN_WEATHER_API_CITY + "&appid=" + OPEN_WEATHER_API_KEY
    response = requests.get(url)

    if response.status_code == 200:
        weather_data = response.json()
        result = {
            "weather_data_timestamp": weather_data_timestamp,
            "sunrise": datetime.datetime.fromtimestamp(weather_data['sys']['sunrise']),
            "sunset": datetime.datetime.fromtimestamp(weather_data['sys']['sunset']),
            "weather_condition": weather_data['weather'][0]['main'],
            "cloud_percentage": weather_data['clouds']['all']
        }
        save_cache(result, weather_data_timestamp)
        return result
    else:
        raise RuntimeError(f"Unable to load weather data. Status code: {response.status_code}")

if __name__ == "__main__":
    while True:
        variables = get_weather_data()

        now = datetime.datetime.now()
        variables["now"] = now
        variables["brightness"] = 1
        variables["sunrise_percentage"] = 1
        variables["sunset_percentage"] = 0
        variables["fade_out"] = True
        variables["is_night"] = False

        if now <= variables["sunrise"] or now >= variables["sunset"]:
            variables["is_night"] = True

        variables["is_christmas"] = (now.month == 12 and now.day == 24 and now.hour >= 18) or (now.month == 12 and now.day in [25, 26])
        variables["is_new_year"] = now.month == 1 and now.day <= 6
        sunrise_effect_start = variables["sunrise"] - datetime.timedelta(minutes=30)
        sunrise_effect_end = variables["sunrise"] + datetime.timedelta(minutes=30)
        sunset_effect_start = variables["sunset"] - datetime.timedelta(minutes=30)
        sunset_effect_end = variables["sunset"] + datetime.timedelta(minutes=30)

        print("Updated variables:")
        for key, value in variables.items():
            print(f"\t{key}: {value}")

        if variables["is_new_year"]:
            variables["intensity"] = 30
            run_effect("simulate_fireworks", variables)
        elif variables["is_christmas"]:
            run_effect("simulate_christmas", variables)
        elif sunrise_effect_start <= now <= sunrise_effect_end:
            if current_effect_name != "simulate_sunrise":
                variables["fade_out"] = True
            else:
                variables["fade_out"] = False
            total_sunrise_duration = (sunrise_effect_end - sunrise_effect_start).total_seconds()
            elapsed_time = (now - sunrise_effect_start).total_seconds()
            sunrise_progress = elapsed_time / total_sunrise_duration
            variables["sunrise_percentage"] = round(sunrise_progress, 2)
            variables["brightness"] = 0.05
            run_effect("simulate_sunrise", variables)
        elif sunset_effect_start <= now <= sunset_effect_end:
            if current_effect_name != "simulate_sunset":
                variables["fade_out"] = True
            else:
                variables["fade_out"] = False
            total_sunset_duration = (sunset_effect_end - sunset_effect_start).total_seconds()
            elapsed_time = (now - sunset_effect_start).total_seconds()
            sunset_progress = elapsed_time / total_sunset_duration
            variables["sunset_percentage"] = round(sunset_progress, 2)
            variables["brightness"] = 0.05
            run_effect("simulate_sunset", variables)
        else:
            match variables["weather_condition"]:
                case "Drizzle":
                    variables["intensity"] = 5
                    if variables["is_night"]:
                        variables["brightness"] = 0.5
                    run_effect("simulate_rain", variables)
                case "Rain":
                    variables["intensity"] = 15
                    if variables["is_night"]:
                        variables["brightness"] = 0.5
                    run_effect("simulate_rain", variables)
                case "Thunder":
                    variables["intensity"] = 20
                    if variables["is_night"]:
                        variables["brightness"] = 0.5
                    run_effect("simulate_rain", variables)
                case "Snow":
                    variables["intensity"] = 5
                    if variables["is_night"]:
                        variables["brightness"] = 0.45
                    else:
                        variables["brightness"] = 0.9
                    run_effect("simulate_snow", variables)
                case _:
                    if variables["is_night"]:
                        run_effect("simulate_night", variables)
                    else:
                        variables["intensity"] = 30
                        run_effect("simulate_day", variables)

        time.sleep(30)
