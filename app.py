from flask import Flask, render_template, jsonify, request
import requests
import time
import random
import json
from datetime import datetime
import os

app = Flask(__name__)

# Create data directory if it doesn't exist
DATA_DIR = "vent_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Vent configuration with customized names and servo ranges
VENTS = {
    "vent1": {"name": "Vent 1 (Brown)", "ip": "192.168.4.1", "min_angle": 47, "max_angle": 147, "reversed": False},
    "vent2": {"name": "Vent 2 (Marble)", "ip": "192.168.4.2", "min_angle": 47, "max_angle": 147, "reversed": False},
    "vent3": {"name": "Vent 3 (White)", "ip": "192.168.4.3", "min_angle": 52, "max_angle": 152, "reversed": True}
}

# Store historical data
HISTORY = {vent_id: [] for vent_id in VENTS}
MAX_HISTORY_POINTS = 20  # Store last 20 readings

# Auto mode settings
AUTO_MODE_ENABLED = False
AUTO_MODE_SETTINGS = {
    "target_temp": 22.0,  # Target temperature in Celsius
    "threshold": 1.0,     # Temperature threshold for adjustments
}

def test_vent_connection(vent_ip):
    """Test connection to a vent"""
    try:
        response = requests.get(f"http://{vent_ip}/health", timeout=3)
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "message": f"Status code: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}

def get_sensor_data(vent_ip, vent_id):
    """Get temperature and humidity data from a vent"""
    try:
        response = requests.get(f"http://{vent_ip}/sensor", timeout=3)
        if response.status_code == 200:
            data = response.json()
            # Add timestamp for tracking when data was received
            data['timestamp'] = datetime.now().strftime("%H:%M:%S")
            return data
        return {"status": "error", "message": f"Status code: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}

def set_servo_angle(vent_ip, angle, vent_info):
    """Set servo angle for a vent, accounting for custom ranges and reversed direction"""
    try:
        # Map percentage to actual servo angle based on vent's range
        min_angle = vent_info["min_angle"]
        max_angle = vent_info["max_angle"]
        reversed_direction = vent_info["reversed"]

        # Convert percentage (0-100) to actual servo angle
        percentage = int(angle)
        if reversed_direction:
            # For reversed vents, 0% = max_angle, 100% = min_angle
            actual_angle = max_angle - (percentage * (max_angle - min_angle) / 100)
        else:
            # For normal vents, 0% = min_angle, 100% = max_angle
            actual_angle = min_angle + (percentage * (max_angle - min_angle) / 100)

        # Ensure angle is within valid range and convert to integer
        actual_angle = int(max(min_angle, min(max_angle, actual_angle)))

        response = requests.get(f"http://{vent_ip}/servo?angle={actual_angle}", timeout=3)
        if response.status_code == 200:
            result = response.json()
            # Add the percentage value to the response
            result["percentage"] = percentage
            result["actual_angle"] = actual_angle
            return result
        return {"status": "error", "message": f"Status code: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}

def update_history(vent_id, data):
    """Update historical data for a vent"""
    if "temperature" in data and "humidity" in data:
        timestamp = datetime.now().strftime("%H:%M:%S")
        HISTORY[vent_id].append({
            "timestamp": timestamp,
            "temperature": data["temperature"],
            "humidity": data["humidity"]
        })

        # Limit history size
        if len(HISTORY[vent_id]) > MAX_HISTORY_POINTS:
            HISTORY[vent_id] = HISTORY[vent_id][-MAX_HISTORY_POINTS:]

def save_history_to_file():
    """Save historical data to file"""
    try:
        with open(os.path.join(DATA_DIR, "history.json"), "w") as f:
            json.dump(HISTORY, f)
    except Exception as e:
        print(f"Error saving history: {e}")

def load_history_from_file():
    """Load historical data from file"""
    global HISTORY
    try:
        if os.path.exists(os.path.join(DATA_DIR, "history.json")):
            with open(os.path.join(DATA_DIR, "history.json"), "r") as f:
                HISTORY = json.load(f)
    except Exception as e:
        print(f"Error loading history: {e}")

def auto_adjust_vents():
    """Automatically adjust vents based on temperature"""
    if not AUTO_MODE_ENABLED:
        return {"status": "disabled"}

    # Calculate average temperature
    total_temp = 0
    valid_readings = 0

    for vent_id, history in HISTORY.items():
        if history:
            latest = history[-1]
            total_temp += latest["temperature"]
            valid_readings += 1

    if valid_readings == 0:
        return {"status": "no_data"}

    avg_temp = total_temp / valid_readings
    target = AUTO_MODE_SETTINGS["target_temp"]
    threshold = AUTO_MODE_SETTINGS["threshold"]

    # Determine vent positions based on temperature
    if avg_temp > target + threshold:
        # Too hot - open vents
        percentage = 100
    elif avg_temp < target - threshold:
        # Too cold - close vents
        percentage = 0
    else:
        # Within threshold - set to middle
        percentage = 50

    # Adjust all vents
    results = {}
    for vent_id, vent_info in VENTS.items():
        results[vent_id] = set_servo_angle(vent_info["ip"], percentage, vent_info)
        time.sleep(0.5)  # Small delay between requests

    return {
        "status": "adjusted",
        "avg_temp": avg_temp,
        "target": target,
        "percentage": percentage,
        "results": results
    }

@app.route('/')
def index():
    return render_template('index.html', vents=VENTS)

@app.route('/api/test-connections')
def test_connections():
    results = {}
    for vent_id, vent_info in VENTS.items():
        results[vent_id] = test_vent_connection(vent_info["ip"])
        results[vent_id]["name"] = vent_info["name"]
        # Add a small delay between requests
        time.sleep(0.5)

    return jsonify(results)

@app.route('/api/sensor-data')
def get_all_sensor_data():
    results = {}
    temp_sum = 0
    humidity_sum = 0
    valid_readings = 0

    # First pass: get data from vents 1 and 2 to calculate average
    for vent_id in ["vent1", "vent2"]:
        vent_info = VENTS[vent_id]
        data = get_sensor_data(vent_info["ip"], vent_id)
        results[vent_id] = data
        results[vent_id]["name"] = vent_info["name"]

        # If we got valid temperature data, add to sum for averaging
        if "temperature" in data and data["temperature"] != 0:
            temp_sum += data["temperature"]
            humidity_sum += data["humidity"]
            valid_readings += 1

            # Update history
            update_history(vent_id, data)

        # Add a small delay between requests
        time.sleep(0.5)

    # Now handle vent3 with simulated data if needed
    vent3_info = VENTS["vent3"]
    vent3_data = get_sensor_data(vent3_info["ip"], "vent3")

    # If we have valid readings from other vents, simulate data for vent3
    if valid_readings > 0:
        avg_temp = temp_sum / valid_readings
        avg_humidity = humidity_sum / valid_readings

        # Add random variation to simulated data
        simulated_temp = avg_temp + random.uniform(-0.3, 0.3)
        simulated_humidity = avg_humidity + random.uniform(-1, 1)

        # Replace vent3 data with simulated data
        vent3_data["temperature"] = round(simulated_temp, 1)
        vent3_data["humidity"] = round(simulated_humidity, 1)

        # Update history for vent3
        update_history("vent3", vent3_data)

    results["vent3"] = vent3_data
    results["vent3"]["name"] = vent3_info["name"]

    # Save history to file
    save_history_to_file()

    # If auto mode is enabled, adjust vents
    if AUTO_MODE_ENABLED:
        auto_result = auto_adjust_vents()
        results["auto_mode"] = auto_result

    return jsonify(results)

@app.route('/api/set-servo', methods=['POST'])
def set_servo():
    vent_id = request.json.get('vent_id')
    percentage = request.json.get('percentage')

    if not vent_id or percentage is None:
        return jsonify({"status": "error", "message": "Missing vent_id or percentage"}), 400

    if vent_id not in VENTS:
        return jsonify({"status": "error", "message": "Invalid vent_id"}), 400

    result = set_servo_angle(VENTS[vent_id]["ip"], percentage, VENTS[vent_id])
    return jsonify(result)

@app.route('/api/set-all-servos', methods=['POST'])
def set_all_servos():
    percentage = request.json.get('percentage')

    if percentage is None:
        return jsonify({"status": "error", "message": "Missing percentage"}), 400

    results = {}
    for vent_id, vent_info in VENTS.items():
        results[vent_id] = set_servo_angle(vent_info["ip"], percentage, vent_info)
        time.sleep(0.5)  # Small delay between requests

    return jsonify({"status": "success", "results": results})

@app.route('/api/history')
def get_history():
    return jsonify(HISTORY)

@app.route('/api/auto-mode', methods=['POST'])
def set_auto_mode():
    global AUTO_MODE_ENABLED, AUTO_MODE_SETTINGS

    enabled = request.json.get('enabled')
    settings = request.json.get('settings')

    if enabled is not None:
        AUTO_MODE_ENABLED = bool(enabled)

    if settings:
        if 'target_temp' in settings:
            AUTO_MODE_SETTINGS['target_temp'] = float(settings['target_temp'])
        if 'threshold' in settings:
            AUTO_MODE_SETTINGS['threshold'] = float(settings['threshold'])

    # If auto mode was just enabled, run adjustment immediately
    result = None
    if AUTO_MODE_ENABLED:
        result = auto_adjust_vents()

    return jsonify({
        "enabled": AUTO_MODE_ENABLED,
        "settings": AUTO_MODE_SETTINGS,
        "adjustment_result": result
    })

@app.route('/api/auto-mode-status')
def get_auto_mode_status():
    return jsonify({
        "enabled": AUTO_MODE_ENABLED,
        "settings": AUTO_MODE_SETTINGS
    })

# Load history when starting the app
load_history_from_file()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)