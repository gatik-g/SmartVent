#include <WiFi.h>
#include <WebServer.h>
#include <DHT.h>
#include <ESP32Servo.h>

// --- Configuration ---
const char* ssid = "ESP32_Vent_AP";
const char* password = "password123";
const char* ventName = "Vent 3"; // Client Vent 3

// --- Static IP Configuration ---
IPAddress staticIP(192, 168, 4, 3);    // Static IP for this device
IPAddress gateway(192, 168, 4, 1);     // Gateway (AP's IP)
IPAddress subnet(255, 255, 255, 0);    // Subnet mask

// --- Hardware Pins ---
#define DHTPIN 2     // Digital pin connected to the DHT sensor (D2)
#define SERVOPIN 4   // Digital pin connected to the Servo motor (D4)

// --- Sensor & Motor Objects ---
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);
Servo ventServo;

// Create a WebServer object for the client
WebServer server(80);

// For tracking uptime and debugging
unsigned long startTime = 0;
unsigned long lastServoMove = 0;

// --- Web Server Handler Functions ---
void handleRoot() {
  unsigned long uptime = millis() / 1000;
  String response = String(ventName);
  response += " is running\n";
  response += "Uptime: " + String(uptime) + " seconds";
  server.send(200, "text/plain", response);
}

// Simple test endpoint
void handleTest() {
  server.send(200, "text/plain", String(ventName) + " test endpoint is working!");
}

// Health check endpoint for monitoring
void handleHealth() {
  server.send(200, "application/json", "{\"status\":\"ok\",\"ventName\":\"" + String(ventName) + "\",\"uptime\":" + String(millis()/1000) + "}");
}

// Get temperature and humidity with improved error handling
void handleGetSensorData() {
  Serial.println("Sensor data requested");
  
  // Add a small delay before reading sensor
  delay(10);
  
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  
  // Add debug output
  Serial.print("Sensor read - Temp: ");
  Serial.print(t);
  Serial.print("°C, Humidity: ");
  Serial.println(h);
  
  // Handle sensor read failure more gracefully
  if (isnan(h) || isnan(t)) {
    Serial.println("Failed to read from DHT sensor!");
    // Return zeros instead of error
    server.send(200, "application/json", "{\"ventName\":\"" + String(ventName) + "\",\"temperature\":0,\"humidity\":0,\"error\":\"sensor_read_failed\"}");
    return;
  }
  
  String json = "{\"ventName\":\"" + String(ventName) + "\",\"temperature\":" + String(t) + ",\"humidity\":" + String(h) + "}";
  server.send(200, "application/json", json);
}

// Set servo angle with power management
void handleSetServo() {
  Serial.println("Servo control requested");
  
  if (!server.hasArg("angle")) {
    server.send(400, "text/plain", "Missing angle parameter");
    return;
  }
  
  int angle = server.arg("angle").toInt();
  
  // Validate angle
  if (angle < 0) angle = 0;
  if (angle > 180) angle = 180;
  
  // Check if we need to limit servo movement frequency
  unsigned long currentTime = millis();
  if (currentTime - lastServoMove < 500) { // Minimum 500ms between moves
    delay(500 - (currentTime - lastServoMove));
  }
  
  // Set the servo angle
  Serial.print("Setting servo angle to: ");
  Serial.println(angle);
  
  // Send response before moving servo to avoid timeout
  server.send(200, "application/json", "{\"ventName\":\"" + String(ventName) + "\",\"success\":true,\"angle\":" + String(angle) + "}");
  
  // Now move the servo
  ventServo.write(angle);
  lastServoMove = millis();
}

void handleNotFound() {
  server.send(404, "text/plain", "404: Not found");
}

// --- Setup Function ---
void setup() {
  Serial.begin(115200);
  delay(100); // Short delay for serial to initialize
  
  Serial.println("\n\n");
  Serial.println("=== " + String(ventName) + " Starting ===");

  // Set WiFi to maximum power for better range
  WiFi.setTxPower(WIFI_POWER_19_5dBm); // Maximum power setting

  // Initialize hardware
  Serial.println("Initializing DHT sensor...");
  dht.begin();
  
  Serial.println("Initializing servo...");
  ventServo.attach(SERVOPIN);
  ventServo.write(90); // Start at neutral position
  delay(500); // Give servo time to move
  
  // Connect to WiFi network with static IP
  Serial.print("Connecting to WiFi network: ");
  Serial.println(ssid);
  
  WiFi.mode(WIFI_STA);
  WiFi.config(staticIP, gateway, subnet); // Configure static IP
  WiFi.begin(ssid, password);
  
  // Wait for connection with increased timeout
  int connectionAttempts = 0;
  int maxAttempts = 40; // Increased from 20
  while (WiFi.status() != WL_CONNECTED && connectionAttempts < maxAttempts) {
    delay(500);
    Serial.print(".");
    connectionAttempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    
    // Configure web server routes
    server.on("/", HTTP_GET, handleRoot);
    server.on("/test", HTTP_GET, handleTest);
    server.on("/health", HTTP_GET, handleHealth);
    server.on("/sensor", HTTP_GET, handleGetSensorData);
    server.on("/servo", HTTP_GET, handleSetServo);
    server.onNotFound(handleNotFound);
    
    // Start the server
    server.begin();
    Serial.println("HTTP server started");
  } else {
    Serial.println("");
    Serial.println("WiFi connection failed");
    Serial.println("Will retry connection in the loop");
  }
  
  startTime = millis();
}

// --- Loop Function ---
void loop() {
  // Check WiFi connection and reconnect if needed
  if (WiFi.status() != WL_CONNECTED) {
    static unsigned long lastReconnectAttempt = 0;
    static int reconnectDelay = 1000; // Start with 1 second
    unsigned long currentMillis = millis();
    
    // Try to reconnect with exponential backoff
    if (currentMillis - lastReconnectAttempt > reconnectDelay) {
      lastReconnectAttempt = currentMillis;
      
      Serial.println("Attempting to reconnect to WiFi...");
      WiFi.disconnect();
      WiFi.config(staticIP, gateway, subnet); // Ensure static IP is maintained
      WiFi.begin(ssid, password);
      
      // Wait briefly to see if connection succeeds
      int reconnectAttempts = 0;
      while (WiFi.status() != WL_CONNECTED && reconnectAttempts < 10) {
        delay(500);
        Serial.print(".");
        reconnectAttempts++;
      }
      
      if (WiFi.status() == WL_CONNECTED) {
        Serial.println("");
        Serial.println("WiFi reconnected");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        reconnectDelay = 1000; // Reset delay on successful connection
      } else {
        Serial.println("");
        Serial.println("WiFi reconnection failed");
        // Implement exponential backoff (max 30 seconds)
        reconnectDelay = min(reconnectDelay * 2, 30000);
        Serial.print("Next attempt in ");
        Serial.print(reconnectDelay / 1000);
        Serial.println(" seconds");
      }
    }
  } else {
    // Handle incoming client requests if WiFi is connected
    server.handleClient();
  }
  
  // Print uptime every minute for debugging
  static unsigned long lastUptimePrint = 0;
  if (millis() - lastUptimePrint > 60000) { // Every minute
    lastUptimePrint = millis();
    unsigned long uptime = millis() / 1000;
    Serial.print("Uptime: ");
    Serial.print(uptime);
    Serial.println(" seconds");
    
    // Also check free heap memory
    Serial.print("Free heap: ");
    Serial.print(ESP.getFreeHeap());
    Serial.println(" bytes");
    
    // Print current IP address and signal strength
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("Current IP address: ");
      Serial.println(WiFi.localIP());
      Serial.print("Signal strength (RSSI): ");
      Serial.print(WiFi.RSSI());
      Serial.println(" dBm");
    }
  }
  
  // Small delay to prevent watchdog issues
  delay(1);
}