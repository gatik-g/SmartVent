# Smart Vent: Intelligent Climate Control
## Project Overview

This project demonstrates a networked system of three "smart vents" that can be monitored and controlled from a central dashboard. Each vent contains:

- ESP32 microcontroller
- DHT22 temperature and humidity sensor
- MG90s servo motor for vent angle control

The system operates on a local WiFi network created by one of the ESP32s, allowing for a completely standalone demonstration without requiring external internet connectivity.

## Features

- **Temperature & Humidity Monitoring**: Real-time sensor readings from all three vents
- **Remote Vent Control**: Adjust the opening angle (0-180°) of each vent independently
- **Web Dashboard**: Control all vents from a browser-based interface
- **Standalone Operation**: Creates its own WiFi network, no external internet required
- **Fault Tolerance**: Robust error handling and automatic reconnection

## Network Architecture

- **Access Point (AP)**: Vent 1 creates a WiFi network
  - SSID: `ESP32_Vent_AP`
  - Password: `password123`
  - IP Address: 192.168.4.1

- **Client Vents**: Vent 2 and Vent 3 connect to the AP
  - Vent 2 IP: 192.168.4.2
  - Vent 3 IP: 192.168.4.3

- **Control Device**: Any device (laptop/tablet) connected to the `ESP32_Vent_AP` network

## Hardware Requirements

### Per Vent
- ESP32 Development Board
- DHT22 Temperature & Humidity Sensor
- MG90s Servo Motor
- Jumper Wires
- Micro USB Cable & Power Supply
- 3D Printed Vent Housing (optional)

### For Dashboard
- Laptop or Tablet with WiFi
- Web Browser (Chrome/Firefox recommended)

## Wiring Diagram

```
ESP32 ───── DHT22 Temperature/Humidity Sensor
  │           - VCC: 3.3V
  │           - GND: GND
  │           - DATA: D2
  │
  └─────── MG90s Servo Motor
              - VCC: 5V or External Power
              - GND: GND
              - SIGNAL: D4
```

## Software Components

### ESP32 Firmware
- **Vent 1 (AP)**: Creates WiFi network and hosts web server
- **Vent 2 & 3 (Clients)**: Connect to AP and host individual web servers

### Control Software
- **Web Dashboard**: HTML/CSS/JavaScript interface for monitoring and control
- **Python CLI**: Command-line tool for testing and direct control

## Installation

### ESP32 Setup
1. Install the Arduino IDE and ESP32 board support
2. Install required libraries:
   - WiFi
   - WebServer
   - DHT sensor library
   - ESP32Servo
3. Flash each ESP32 with the appropriate firmware:
   - `vent1_ap.ino` for the Access Point vent
   - `vent2_client.ino` for Vent 2
   - `vent3_client.ino` for Vent 3

### Dashboard Setup
1. Connect your laptop/tablet to the `ESP32_Vent_AP` WiFi network
2. Open the dashboard HTML file in a web browser
3. Alternatively, run a local web server to host the dashboard

## Usage

### Web Dashboard
- Access the dashboard by opening the HTML file in your browser
- Monitor temperature and humidity readings from all vents
- Adjust vent angles using the sliders (0° = closed, 180° = fully open)
- Use preset buttons for quick adjustments

### Python CLI
For testing and direct control, use the provided Python script:

```bash
# Test connection to all vents
python vent_controller.py test

# Get sensor readings from all vents
python vent_controller.py reading

# Set a specific vent angle
python vent_controller.py angle 90 --vent vent1

# Monitor all vents for 2 minutes
python vent_controller.py monitor --duration 120
```

## API Reference

Each vent exposes the following HTTP endpoints:

- `GET /` - Basic status information
- `GET /test` - Simple connectivity test
- `GET /health` - Health check with uptime
- `GET /sensor` - Get temperature and humidity readings
- `GET /servo?angle=X` - Set servo angle (0-180 degrees)

## Troubleshooting

### Common Issues
- **Connection Problems**: Ensure all vents are powered and within range
- **Sensor Errors**: Check DHT22 wiring and connections
- **Servo Not Moving**: Verify power supply is adequate for servo operation

### Diagnostic Tools
- Serial monitor (115200 baud) provides debugging information
- Health endpoint (`/health`) shows device uptime
- Python test script can verify individual component functionality

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- ESP32 and Arduino communities for libraries and examples
- DHT sensor library by Adafruit
- ESP32Servo library contributors

---

*This project was created for educational purposes as part of the 3D printing challenge hosted by the MSJ Rotary Club, check out our instructable for more information https://www.instructables.com/SmartVent-Intelligent-Climate-Control/.*
