#include <Arduino.h>
#include <ADS1299.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <esp_gap_ble_api.h>

ADS1299 ADS;

// ADS1299 DEFINITIONS
#define RESET_PIN  14
#define DRDY_PIN   9
#define CS_PIN     10
#define MOSI_PIN   11   // AKA Data. Connected to ADS1299 DIN
#define SCK_PIN    12
#define MISO_PIN   13   // AKA Quad. Connected to ADS1299 DOUT
#define START_PIN  18

// BLUETOOTH DEFINITIONS
#define bleServerName "ESP32_EEG_DATA"                              //BLE server name
#define SERVICE_UUID "91bad492-b950-4226-aa2b-4ede9fa42f59"         //BLE service UUID (randomly generated)
#define CHARACTERISTIC_UUID "cba1d466-344c-4be3-ab3f-189f80dd7518"  //BLE characteristic UUID (randomly generated)
BLECharacteristic *pCharacteristic = NULL;

// FUNCTION DECLARATIONS
void IRAM_ATTR dataReadyISR();              // DRDY Interrupt
void IRAM_ATTR buttonISR();                 // Button Interrupt
void myGapHandler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param); // GAP event handler for debugging
void readADSDataTask(void * pvParameters);  // Core 1: Read Data from ADS1299
void sendDataTask(void * pvParameters);     // Core 0: Send Data to PC

// VARIABLES
SemaphoreHandle_t drdySemaphore;            // Semaphore to signal when DRDY goes low 
QueueHandle_t packetQueue;                  // Create a queue to pass 33-byte arrays between cores
uint8_t sampleCounter = 0;
volatile bool deviceConnected = false;      // Flag to track BLE connection status

// HARDWARE BUTTON DEFINITION
#define BOOT_BUTTON_PIN 0
volatile bool triggerRecordMode = false; // Flag to trigger state change

// --------------------------------------------------------------------------------------------------------------------------------------

//Setup bluetooth callbacks onConnect and onDisconnect
class MyServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer, esp_ble_gatts_cb_param_t *param) {
    deviceConnected = true;
    Serial.println("Device connected!");
    pServer->updateConnParams(param->connect.remote_bda, 6, 12, 0, 400);  // Can change 12 to 10 to force a faster intervaL.
    esp_ble_gap_set_pkt_data_len(param->connect.remote_bda, 251); // Request data length extension
  };

  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    Serial.println("Device disconnected. Restarting advertising...");
    // Restart advertising to allow reconnection
    pServer->getAdvertising()->start();
  }
};

// --------------------------------------------------------------------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.printf("PSRAM size: %u bytes\n", ESP.getPsramSize());

  // Boot button setup
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(BOOT_BUTTON_PIN), buttonISR, FALLING);

  // Initialize Queue holding up to 256 packets of 28 bytes
  packetQueue = xQueueCreate(256, 28 * sizeof(uint8_t));

  // BLUETOOTH LOW ENERGY SETUP
  BLEDevice::init(bleServerName);                               // Create the BLE Device
  BLEDevice::setMTU(512);                                       // Set MTU to maximum to allow for larger packets and reduce fragmentation
  BLEServer *pServer = BLEDevice::createServer();               // Set BLE device as a server
  pServer->setCallbacks(new MyServerCallbacks());               // Assign callback function
  BLEService *pService = pServer->createService(SERVICE_UUID);  // Start BLE service with service UUID
  pCharacteristic = pService->createCharacteristic(CHARACTERISTIC_UUID,BLECharacteristic::PROPERTY_NOTIFY);   // Create a BLE Characteristic with notify property
  pCharacteristic->addDescriptor(new BLE2902());                // Add a BLE2902 descriptor to allow notifications
  pService->start();                                            // Start the service
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();   // Start advertising
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pServer->getAdvertising()->start();
  BLEDevice::setCustomGapHandler(myGapHandler);
  delay(1000);

  // SETUP ADS1299
  ADS.setup(DRDY_PIN, CS_PIN, SCK_PIN, MISO_PIN, MOSI_PIN, RESET_PIN, START_PIN);
  digitalWrite(START_PIN, LOW);     // Pull start low to stop conversations
  delay(10);
  ADS.SDATAC();                     // Stop continuous data mode to allow register configuration
  ADS.WREG(GPIO, 0b00000000);
  ADS.WREG(CONFIG1, 0b10010101);    // Set SPS (110 = 250, 101 = 500, 100 = 1000)
  ADS.WREG(CONFIG3, 0b11111110);    // Enable power-down reference buffer, bias measurement, internal bias ref, bias buffer and bias lead off
  ADS.WREG(CONFIG4, 0b00000010);    // Enable lead-off comparator

  ADS.WREG(MISC1, 0b00100100);      // Connect SRB1 to inverting inputs.
  ADS.WREG(BIAS_SENSP, 0b00000001); // Set which positive channels to use for bias
  ADS.WREG(BIAS_SENSN, 0b00000000); // Set which negative channels to use for bias

  ADS.WREG(LOFF, 0b00000100);
  ADS.WREG(LOFF_SENSP, 0b11111111); // Enable lead-off detection for channel 1p)
  ADS.WREG(LOFF_SENSN, 0b00000001); // Enable lead-off detection for channel 1n)

  for(int i=CH1SET; i<=CH8SET; i++) ADS.WREG(i, 0b01100000);
 
  drdySemaphore = xSemaphoreCreateBinary();                                 // Create a binary semaphore to signal when DRDY goes low
  attachInterrupt(digitalPinToInterrupt(DRDY_PIN), dataReadyISR, FALLING);  // Set up DRDY interrupt on falling edge
  ADS.RDATAC();                     // Start continuous data mode
  digitalWrite(START_PIN, HIGH);    // Pull start high to begin conversations
  delay(10);

  // Core 1: Read Data from ADS1299
  xTaskCreatePinnedToCore(
    readADSDataTask,   
    "ReadTask",        
    4096,              
    NULL,              
    3,        
    NULL,              
    1);

  // Core 0: Send Data to PC
  xTaskCreatePinnedToCore(
    sendDataTask,      
    "SendTask",        
    4096,              
    NULL,              
    1,                 
    NULL,              
    0);

  Serial.println("Setup complete\n");
}

// --------------------------------------------------------------------------------------------------------------------------------------

void loop() {
  // If the BOOT button is pressed, turn off lead off
  if (triggerRecordMode) {
    triggerRecordMode = false; // Reset flag

    // Stop conversations and stop continuous data mode
    digitalWrite(START_PIN, LOW);
    delay(10);
    ADS.SDATAC();
    
    // 2. Check bias lead-off
    uint8_t config3_val = ADS.RREG(CONFIG3); 
    bool biasDisconnected = (config3_val & 0b00000001);
    if (biasDisconnected) {
      Serial.println("Bias Disconnected");
    } else {
      Serial.println("Bias Connected");
    }

    // Turn off lead off detection
    ADS.WREG(LOFF_SENSP, 0b00000000); 
    ADS.WREG(LOFF_SENSN, 0b00000000);
    ADS.WREG(CONFIG3, 0b11111100);
    
    // Restart continuous data mode
    ADS.RDATAC();
    digitalWrite(START_PIN, HIGH);
    delay(10);
    
    Serial.println("Lead-off disabled\n");
    vTaskDelete(NULL);
  }

  // Delay to yeild to other tasks
  delay(100);
}

// --------------------------------------------------------------------------------------------------------------------------------------

void IRAM_ATTR buttonISR() {
  triggerRecordMode = true;
}

// --------------------------------------------------------------------------------------------------------------------------------------

void IRAM_ATTR dataReadyISR() {
  BaseType_t xHigherPriorityTaskWoken = pdFALSE;
  // Give the semaphore
  xSemaphoreGiveFromISR(drdySemaphore, &xHigherPriorityTaskWoken);
  
  // Force a context switch if the read task is ready
  if (xHigherPriorityTaskWoken) {
    portYIELD_FROM_ISR();
  }
}

// --------------------------------------------------------------------------------------------------------------------------------------

void myGapHandler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param) {
    if (event == ESP_GAP_BLE_SET_PKT_LENGTH_COMPLETE_EVT) {
        Serial.printf("DLE: status=%d tx=%d rx=%d\n",
            param->pkt_data_lenth_cmpl.status,
            param->pkt_data_lenth_cmpl.params.tx_len,
            param->pkt_data_lenth_cmpl.params.rx_len);
    }
    
    if (event == ESP_GAP_BLE_UPDATE_CONN_PARAMS_EVT) {
    Serial.printf("Conn params: interval=%d (%.2f ms), latency=%d, timeout=%d ms\n",
        param->update_conn_params.conn_int,
        param->update_conn_params.conn_int * 1.25,
        param->update_conn_params.latency,
        param->update_conn_params.timeout * 10);
}
}

// --------------------------------------------------------------------------------------------------------------------------------------

void readADSDataTask(void * pvParameters) {
  uint8_t dataPacket[28];
  
  for(;;) {
    // Sleep until ISR gives semaaphore
    if (xSemaphoreTake(drdySemaphore, portMAX_DELAY) == pdTRUE) {
      
      // Assign Sample Counter
      dataPacket[0] = sampleCounter++;

      // Read SPI Data
      ADS.updateDataPacket(dataPacket);

      // Send to the Bluetooth Core
      xQueueSend(packetQueue, dataPacket, 0); 
    }
  }
}

// --------------------------------------------------------------------------------------------------------------------------------------

void sendDataTask(void * pvParameters) {
  uint8_t singlePacket[28]; // Holds one packet of 28 bytes received from the queue
  uint8_t batchBuffer[224]; // Holds 8 packets of 28 bytes
  int batchCount = 0;
  
  for(;;) {
    // Clear queue and reset batch if no device is connected
    if (!deviceConnected) {
      xQueueReset(packetQueue);
      batchCount = 0;
      vTaskDelay(pdMS_TO_TICKS(100));  // sleep while disconnected
      continue;
    }

    // Wait for a single 28-byte packet from Core 1
    if (xQueueReceive(packetQueue, &singlePacket, portMAX_DELAY) == pdPASS) {
      
      // Copy the 28 bytes into the correct slot of 224-byte batch buffer
      memcpy(&batchBuffer[batchCount * 28], singlePacket, 28);
      batchCount++;

      // After 8 packets, send the full 224-byte batch
      if (batchCount == 8) {
        pCharacteristic->setValue(batchBuffer, 224);
        pCharacteristic->notify();
        
        batchCount = 0;
      }
    }
  }
}