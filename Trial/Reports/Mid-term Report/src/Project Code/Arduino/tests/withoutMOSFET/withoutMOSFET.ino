/*
 * AI-Based Smart Bulb for Adaptive Home Automation
 * ESP32-WROOM-32D Firmware - OPTIMIZED VERSION
 * 
 * Student: Caleb Ram (6801936)
 * Supervisor: Dr Ahmed Elzanaty
 * University of Surrey - MEng Electronic Engineering
 * 
 * SELECT YOUR HARDWARE CONFIGURATION:
 */


#define CONFIG_BT_NIMBLE_ENABLED
#define CONFIG_BTDM_CONTROLLER_MODE_BLE_ONLY
// UNCOMMENT ONE OF THESE:
#define MODE_DEV_ONLY           // Dev module only (built-in LED)
// #define MODE_TWO_MOSFETS     // 2x MOSFETs (no sensors)
// #define MODE_FULL_HARDWARE   // Full hardware (sensors + MOSFETs)

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#if !defined(MODE_DEV_ONLY)
  #include <WiFi.h>
  #include <WiFiManager.h>
#endif

#if defined(MODE_FULL_HARDWARE)
  #include <Wire.h>
  #include <BH1750.h>
  #include <OneWire.h>
  #include <DallasTemperature.h>
#endif

#include <Preferences.h>

// ==================== PINS ====================
#define PWM_WARM_WHITE 25
#define PWM_COOL_WHITE 26
#define STATUS_LED 2

#define PWM_FREQ 1000
#define PWM_RESOLUTION 8

// ==================== BLE UUIDs ====================
#define SERVICE_UUID           "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define POWER_CHAR_UUID        "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define BRIGHTNESS_CHAR_UUID   "beb5483e-36e1-4688-b7f5-ea07361b26a9"
#define COLOR_CHAR_UUID        "beb5483e-36e1-4688-b7f5-ea07361b26aa"
#define MODE_CHAR_UUID         "beb5483e-36e1-4688-b7f5-ea07361b26ab"
#define STATUS_CHAR_UUID       "beb5483e-36e1-4688-b7f5-ea07361b26ac"

// ==================== GLOBALS ====================
BLEServer *pServer = NULL;
BLECharacteristic *pPowerChar = NULL;
BLECharacteristic *pBrightnessChar = NULL;
BLECharacteristic *pColorChar = NULL;
BLECharacteristic *pModeChar = NULL;
BLECharacteristic *pStatusChar = NULL;

#ifdef MODE_FULL_HARDWARE
  BH1750 lightMeter;
  OneWire oneWire(4);
  DallasTemperature tempSensor(&oneWire);
#endif

struct {
  bool power = false;
  uint8_t brightness = 255;
  uint8_t red = 255;
  uint8_t green = 255;
  uint8_t blue = 255;
  uint8_t mode = 0;
  uint8_t warmWhite = 128;
  uint8_t coolWhite = 128;
  float temperature = 25.0;
  float ambientLight = 100.0;
} bulbState;

bool deviceConnected = false;
bool oldDeviceConnected = false;

// ==================== FORWARD DECLARATIONS ====================
void updateLEDs();
void notifyStatus();
void rgbToWarmCool(uint8_t r, uint8_t g, uint8_t b);

// ==================== BLE CALLBACKS ====================
class ServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    digitalWrite(STATUS_LED, HIGH);
    Serial.println("BLE Connected");
  }
  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    digitalWrite(STATUS_LED, LOW);
    Serial.println("BLE Disconnected");
    BLEDevice::startAdvertising();
  }
};

class PowerCallbacks: public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {
    uint8_t* data = pCharacteristic->getData();
    if (data) {
      bulbState.power = (data[0] == 1);
      updateLEDs();
      notifyStatus();
    }
  }
};

class BrightnessCallbacks: public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {
    uint8_t* data = pCharacteristic->getData();
    if (data) {
      bulbState.brightness = data[0];
      updateLEDs();
      notifyStatus();
    }
  }
};

class ColorCallbacks: public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {
    uint8_t* data = pCharacteristic->getData();
    size_t length = pCharacteristic->getValue().length();
    if (data && length >= 3) {
      bulbState.red = data[0];
      bulbState.green = data[1];
      bulbState.blue = data[2];
      rgbToWarmCool(bulbState.red, bulbState.green, bulbState.blue);
      updateLEDs();
      notifyStatus();
    }
  }
};

class ModeCallbacks: public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {
    uint8_t* data = pCharacteristic->getData();
    if (data) {
      bulbState.mode = data[0];
      notifyStatus();
    }
  }
};

// ==================== FUNCTIONS ====================
void rgbToWarmCool(uint8_t r, uint8_t g, uint8_t b) {
  float warmRatio = (float)r / 255.0;
  float coolRatio = (float)b / 255.0;
  float total = warmRatio + coolRatio;
  if (total > 0) {
    warmRatio /= total;
    coolRatio /= total;
  } else {
    warmRatio = 0.5;
    coolRatio = 0.5;
  }
  bulbState.warmWhite = (uint8_t)(warmRatio * 255);
  bulbState.coolWhite = (uint8_t)(coolRatio * 255);
}

void updateLEDs() {
  #ifdef MODE_DEV_ONLY
    digitalWrite(STATUS_LED, bulbState.power ? HIGH : LOW);
  #else
    if (!bulbState.power) {
      ledcWrite(PWM_WARM_WHITE, 0);
      ledcWrite(PWM_COOL_WHITE, 0);
      digitalWrite(STATUS_LED, LOW);
      return;
    }
    digitalWrite(STATUS_LED, HIGH);
    uint8_t warmPWM = (bulbState.brightness * bulbState.warmWhite) / 255;
    uint8_t coolPWM = (bulbState.brightness * bulbState.coolWhite) / 255;
    ledcWrite(PWM_WARM_WHITE, warmPWM);
    ledcWrite(PWM_COOL_WHITE, coolPWM);
  #endif
}

void notifyStatus() {
  if (deviceConnected && pStatusChar) {
    uint8_t status[6] = {
      bulbState.power ? (uint8_t)1 : (uint8_t)0,
      bulbState.brightness,
      bulbState.red,
      bulbState.green,
      bulbState.blue,
      bulbState.mode
    };
    pStatusChar->setValue(status, 6);
    pStatusChar->notify();
  }
}

void handleEffects() {
  if (!bulbState.power || bulbState.mode == 0) return;
  
  static uint8_t step = 0;
  step++;
  
  switch (bulbState.mode) {
    case 1: { // Fade
      float fade = (sin(step * 0.05) + 1.0) / 2.0;
      uint8_t temp = bulbState.brightness;
      bulbState.brightness = (uint8_t)(temp * fade);
      updateLEDs();
      bulbState.brightness = temp;
      break;
    }
    case 2: { // Rainbow
      float ratio = (sin(step * 0.03) + 1.0) / 2.0;
      bulbState.warmWhite = (uint8_t)(ratio * 255);
      bulbState.coolWhite = (uint8_t)((1.0 - ratio) * 255);
      updateLEDs();
      break;
    }
    case 3: // Pulse
      if (step % 100 < 50) {
        uint8_t temp = bulbState.brightness;
        bulbState.brightness = temp / 2;
        updateLEDs();
        bulbState.brightness = temp;
      } else {
        updateLEDs();
      }
      break;
  }
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(500);
  
  Serial.println("\n=== AI Smart Bulb - ESP32 ===");
  #ifdef MODE_DEV_ONLY
    Serial.println("MODE: DEV ONLY");
  #elif defined(MODE_TWO_MOSFETS)
    Serial.println("MODE: 2x MOSFETs");
  #elif defined(MODE_FULL_HARDWARE)
    Serial.println("MODE: FULL HARDWARE");
  #endif
  Serial.println("Student: Caleb Ram (6801936)");
  Serial.println("==============================\n");
  
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);
  
  #if !defined(MODE_DEV_ONLY)
    ledcAttach(PWM_WARM_WHITE, PWM_FREQ, PWM_RESOLUTION);
    ledcAttach(PWM_COOL_WHITE, PWM_FREQ, PWM_RESOLUTION);
    Serial.println("PWM initialized");
  #endif
  
  #ifdef MODE_FULL_HARDWARE
    Wire.begin(21, 22);
    if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
      Serial.println("BH1750 OK");
    }
    tempSensor.begin();
    Serial.println("DS18B20 OK");
  #endif
  
  // Initialize BLE
  BLEDevice::init("SmartBulb-AI");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());
  
  BLEService *pService = pServer->createService(SERVICE_UUID);
  
  pPowerChar = pService->createCharacteristic(
    POWER_CHAR_UUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
  );
  pPowerChar->setCallbacks(new PowerCallbacks());
  pPowerChar->addDescriptor(new BLE2902());
  
  pBrightnessChar = pService->createCharacteristic(
    BRIGHTNESS_CHAR_UUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
  );
  pBrightnessChar->setCallbacks(new BrightnessCallbacks());
  pBrightnessChar->addDescriptor(new BLE2902());
  
  pColorChar = pService->createCharacteristic(
    COLOR_CHAR_UUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
  );
  pColorChar->setCallbacks(new ColorCallbacks());
  pColorChar->addDescriptor(new BLE2902());
  
  pModeChar = pService->createCharacteristic(
    MODE_CHAR_UUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
  );
  pModeChar->setCallbacks(new ModeCallbacks());
  pModeChar->addDescriptor(new BLE2902());
  
  pStatusChar = pService->createCharacteristic(
    STATUS_CHAR_UUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
  );
  pStatusChar->addDescriptor(new BLE2902());
  
  pService->start();
  
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  BLEDevice::startAdvertising();
  
  Serial.println("BLE Service started");
  Serial.println("Service UUID: " SERVICE_UUID);
  Serial.println("Device Name: SmartBulb-AI");
  Serial.println("\nReady for connections!\n");
  
  updateLEDs();
}

// ==================== LOOP ====================
void loop() {
  // Handle BLE reconnection
  if (!deviceConnected && oldDeviceConnected) {
    delay(500);
    pServer->startAdvertising();
    oldDeviceConnected = deviceConnected;
  }
  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = deviceConnected;
  }
  
  // Handle effects
  static unsigned long lastEffect = 0;
  if (millis() - lastEffect > 50) {
    handleEffects();
    lastEffect = millis();
  }
  
  #ifdef MODE_FULL_HARDWARE
    // Read sensors periodically
    static unsigned long lastSensor = 0;
    if (millis() - lastSensor > 2000) {
      if (lightMeter.measurementReady()) {
        bulbState.ambientLight = lightMeter.readLightLevel();
      }
      tempSensor.requestTemperatures();
      bulbState.temperature = tempSensor.getTempCByIndex(0);
      lastSensor = millis();
    }
  #endif
  
  delay(10);
}