/*
 * If Arduino BLE makes problems, one can alternatively use espressif sdk, see:
 *    - https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/bluetooth/esp_gatts.html
 *    - https://github.com/espressif/esp-idf/blob/master/examples/bluetooth/bluedroid/ble/gatt_server_service_table/tutorial/Gatt_Server_Service_Table_Example_Walkthrough.md
 *    
 *  Bluetooth GATT profiles: https://www.bluetooth.com/specifications/GATT/
 *  
 *  This sketch was copy pasted from examples BLE_notify and BLE_write
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

BLEServer* pServer = NULL;
// memorize bd address to update connection params lateron
esp_bd_addr_t remote_bda;
BLECharacteristic* pCNotify[3];
bool deviceConnected = false;
bool oldDeviceConnected = false;
uint32_t value = 0;

// See the following for generating UUIDs:
// https://www.uuidgenerator.net/

#define SERVICE_UUID  "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
const char* UUID_NOTIFY[3] = {
  "beb5483e-36e1-4688-b7f5-ea07361b26a8",
  "beb5483e-36e1-4688-b7f5-ea07361b26a9",
  "beb5483e-36e1-4688-b7f5-ea07361b26ab"
};
#define UUID_WRITE    "beb5483e-36e1-4688-b7f5-ea07361b26aa"

// variable connection parameters for benchmarking different configurations
byte minLatency = 6;
byte maxLatency = 6;
byte payloadSize = 45;
byte delayTime = 10;
byte numChars = 1;

char sbuf [500];

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer, esp_ble_gatts_cb_param_t* param) {
      deviceConnected = true;
      // the conn params change can be observed on Android: https://stackoverflow.com/a/44810808
      // but it is also obvious when using a good performing BT dongle
      // min/max-interval = arg * 1.25ms
      // bluetooth spec says a minimum of 7.5ms but some hardware supports <1ms, see https://devzone.nordicsemi.com/f/nordic-q-a/24013/minimum-connection-interval
      // esp only supports 7.5ms, see https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/bluetooth/esp_gap_ble.html#_CPPv4N18esp_ble_adv_data_t12min_intervalE
      memcpy(&remote_bda, &(param->connect.remote_bda), 6); //remote_bda = param->connect.remote_bda;
      pServer->updateConnParams(remote_bda, minLatency, maxLatency, 0, 400);
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
    }
};

class MyCharacteristicCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
      std::string value = pCharacteristic->getValue();
      if (value.length() > 0) {
        switch (value[0]) {
          case 0:
            Serial.println("starting tests!");
            break;
          case 1:
            Serial.println("testing connection params");
            minLatency = value[1];
            maxLatency = value[2];
            payloadSize = value[3];
            delayTime = value[4];
            numChars = value[5];
            pServer->updateConnParams(remote_bda, minLatency, maxLatency, 0, 400);
            break;
        }
        Serial.println(value.length());
        Serial.println();
      }
    }
};

void setup() {
  Serial.begin(2000000);

  // Create the BLE Device
  BLEDevice::init("Glove5");
  // following line sadly doesnt change anything, is it related(?) to https://docs.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.genericattributeprofile.gattsession.maxpdusize?view=winrt-19041
  BLEDevice::setMTU(512);

  // Create the BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create the BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // BLECharacteristic::PROPERTY_READ | WRITE | NOTIFY | INDICATE
  for (int i = 0; i < 3; i++) {
    pCNotify[i] = pService->createCharacteristic(UUID_NOTIFY[i], BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
    // Create a CCCD GATT Descriptor, necessary to subscribe to the characteristic
    pCNotify[i]->addDescriptor(new BLE2902());    
    BLEDescriptor *pBLE2901 = new BLEDescriptor((uint16_t)0x2901); // Characteristic User Description    
    sprintf(sbuf, "notify_%d", i);
    pBLE2901->setValue(sbuf);
    pCNotify[i]->addDescriptor(pBLE2901);    
  }

  BLECharacteristic *pCWrite = pService->createCharacteristic(
   UUID_WRITE,
   BLECharacteristic::PROPERTY_READ |
   BLECharacteristic::PROPERTY_WRITE
  );
  pCWrite->setCallbacks(new MyCharacteristicCallbacks());
  pCWrite->setValue("Hello World");

  // Start the service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);  // set value to 0x00 to not advertise this parameter
  BLEDevice::startAdvertising();
  Serial.println("Waiting a client connection to notify...");
}

int i = 0;
void loop() {
    // notify changed value
    if (deviceConnected) {
        sprintf(sbuf, "%d0----------1----------2----------3----------4----------5----------6----------7----------8----------9----------", value);
        Serial.print(".");
        if (i++ % 50 == 0)
          Serial.println();
        // the whole packet is 1 (preamble) + 4 (address)  + 1 (data header) + 1 (payload length) + 0-27 (l2cap payload) + 3 (crc)
        // l2cap mtu is 27: 2 (lc2cap length) + 2 (l2cap cid) + 0-23 (att payload)
        // default ATT_MTU is 23 (increasable by client up til 512) = 2 attribute handle + 0-20 value + 1 free to avoid next packet
        // optimal payloads seem to be n*25 + 20
        for (int i = 0; i < numChars; i++) {
          pCNotify[i]->setValue((uint8_t*)sbuf, payloadSize);
          pCNotify[i]->notify();          
        }
        value++;
        delay(delayTime); // bluetooth stack will go into congestion, if too many packets are sent, in 6 hours test i was able to go as low as 3ms
    }
    // disconnecting
    if (!deviceConnected && oldDeviceConnected) {
        delay(500); // give the bluetooth stack the chance to get things ready
        pServer->startAdvertising(); // restart advertising
        Serial.println("start advertising");
        oldDeviceConnected = deviceConnected;
    }
    // connecting
    if (deviceConnected && !oldDeviceConnected) {
        // do stuff here on connecting
        oldDeviceConnected = deviceConnected;
    }
}
