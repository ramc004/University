#include <Wire.h>
#include <BH1750.h>

// Pin definitions
#define WARM_WHITE_PIN 25  // GPIO pin for warm white MOSFET (green wire)
#define COOL_WHITE_PIN 26  // GPIO pin for cool white MOSFET (green wire)

// PWM settings
#define PWM_FREQ 5000      // 5 kHz
#define PWM_RESOLUTION 8   // 8-bit resolution (0-255)
#define WW_CHANNEL 0       // PWM channel for warm white
#define CW_CHANNEL 1       // PWM channel for cool white

// BH1750 light sensor
BH1750 lightMeter;

// Variables
float lux = 0;
int warmWhite = 0;
int coolWhite = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 Dual White LED Controller Starting...");
  
  // Initialize I2C for BH1750
  Wire.begin(21, 22); // SDA=21, SCL=22 (default ESP32 pins)
  
  // Initialize BH1750 sensor
  if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println("BH1750 initialized successfully");
  } else {
    Serial.println("Error initializing BH1750");
  }
  
  // Configure PWM channels
  ledcSetup(WW_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
  ledcSetup(CW_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
  
  // Attach PWM channels to GPIO pins
  ledcAttachPin(WARM_WHITE_PIN, WW_CHANNEL);
  ledcAttachPin(COOL_WHITE_PIN, CW_CHANNEL);
  
  Serial.println("Setup complete!");
  Serial.println("Commands:");
  Serial.println("  'a' - Auto mode (uses BH1750 sensor)");
  Serial.println("  'm' - Manual mode");
  Serial.println("  'w XXX' - Set warm white (0-255)");
  Serial.println("  'c XXX' - Set cool white (0-255)");
  Serial.println("  's' - Show current values");
}

void loop() {
  // Read light sensor
  lux = lightMeter.readLightLevel();
  
  // Auto mode: adjust color temperature based on ambient light
  // Dim light (< 50 lux) = warmer (3000K)
  // Medium light (50-300 lux) = neutral (4500K)
  // Bright light (> 300 lux) = cooler (6000K)
  
  if (lux < 50) {
    // Warm white dominant
    warmWhite = 255;
    coolWhite = 100;
  } else if (lux < 300) {
    // Balanced neutral white
    warmWhite = 200;
    coolWhite = 200;
  } else {
    // Cool white dominant
    warmWhite = 100;
    coolWhite = 255;
  }
  
  // Set LED brightness
  ledcWrite(WW_CHANNEL, warmWhite);
  ledcWrite(CW_CHANNEL, coolWhite);
  
  // Print status every 2 seconds
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 2000) {
    Serial.print("Lux: ");
    Serial.print(lux);
    Serial.print(" | WW: ");
    Serial.print(warmWhite);
    Serial.print(" | CW: ");
    Serial.println(coolWhite);
    lastPrint = millis();
  }
  
  // Check for serial commands
  if (Serial.available()) {
    handleSerialCommand();
  }
  
  delay(100);
}

void handleSerialCommand() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  
  if (cmd == "s") {
    Serial.println("=== Current Status ===");
    Serial.print("Light Level: ");
    Serial.print(lux);
    Serial.println(" lux");
    Serial.print("Warm White: ");
    Serial.println(warmWhite);
    Serial.print("Cool White: ");
    Serial.println(coolWhite);
  } else if (cmd.startsWith("w ")) {
    warmWhite = cmd.substring(2).toInt();
    warmWhite = constrain(warmWhite, 0, 255);
    Serial.print("Warm White set to: ");
    Serial.println(warmWhite);
  } else if (cmd.startsWith("c ")) {
    coolWhite = cmd.substring(2).toInt();
    coolWhite = constrain(coolWhite, 0, 255);
    Serial.print("Cool White set to: ");
    Serial.println(coolWhite);
  }
}