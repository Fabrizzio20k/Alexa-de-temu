#include <driver/i2s.h>
#include <WiFi.h>
#include <FS.h>
#include <SPIFFS.h>
#include <PubSubClient.h>

#define I2S_WS 15
#define I2S_SD 32
#define I2S_SCK 14
#define I2S_PORT I2S_NUM_0
#define SAMPLE_RATE 16000
#define BUFFER_SIZE 512

#define SILENCE_THRESHOLD 2300
#define SILENCE_DURATION 1500
#define MAX_RECORDING_SIZE 64000

const char* WIFI_SSID = "Yes King";
const char* WIFI_PASSWORD = "72793838GG";
const char* SERVER_HOST = "192.168.18.153";
const int SERVER_PORT = 8000;
const char* MQTT_SERVER = "192.168.18.153";
const int MQTT_PORT = 1883;
const unsigned long MQTT_RECONNECT_INTERVAL = 5000;

WiFiClient mqttClient;
PubSubClient mqtt(mqttClient);

int16_t sBuffer[BUFFER_SIZE];
bool isRecording = false;
unsigned long lastSoundTime = 0;
unsigned long lastMqttAttempt = 0;
File recordingFile;
int recordingSamples = 0;

bool estadoVentilador = true;
bool estadoPersianas = true;
bool estadoBulbs = true;
float temperatura = 20.0;
float humedad = 20.0;
float luzAmbiente = 20.0;

void setupI2S() {
  const i2s_config_t i2s_config = {
    .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = i2s_bits_per_sample_t(16),
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
    .intr_alloc_flags = 0,
    .dma_buf_count = 8,
    .dma_buf_len = BUFFER_SIZE,
    .use_apll = false
  };

  const i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = -1,
    .data_in_num = I2S_SD
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_start(I2S_PORT);
}

void connectWiFi() {
  Serial.println("Conectando a WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void setupMQTT() {
  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setBufferSize(256);
  mqtt.setKeepAlive(15);
  mqtt.setSocketTimeout(15);
  randomSeed(micros());
}

void reconnectMQTT() {
  if (mqtt.connected() || millis() - lastMqttAttempt < MQTT_RECONNECT_INTERVAL) {
    return;
  }
  
  lastMqttAttempt = millis();
  String clientId = "ESP32-" + String(random(0xffff), HEX);
  
  if (mqtt.connect(clientId.c_str())) {
    Serial.println("MQTT conectado");
  } else {
    Serial.print("MQTT fallo: ");
    Serial.println(mqtt.state());
  }
}

void writeWavHeader(File &file, int dataSize) {
  int subchunk2Size = dataSize * 2;
  int chunkSize = 36 + subchunk2Size;
  int16_t audioFormat = 1;
  int16_t numChannels = 1;
  int sampleRate = SAMPLE_RATE;
  int byteRate = SAMPLE_RATE * 2;
  int16_t blockAlign = 2;
  int16_t bitsPerSample = 16;
  int subchunk1Size = 16;

  file.write((const uint8_t*)"RIFF", 4);
  file.write((const uint8_t*)&chunkSize, 4);
  file.write((const uint8_t*)"WAVE", 4);
  file.write((const uint8_t*)"fmt ", 4);
  file.write((const uint8_t*)&subchunk1Size, 4);
  file.write((const uint8_t*)&audioFormat, 2);
  file.write((const uint8_t*)&numChannels, 2);
  file.write((const uint8_t*)&sampleRate, 4);
  file.write((const uint8_t*)&byteRate, 4);
  file.write((const uint8_t*)&blockAlign, 2);
  file.write((const uint8_t*)&bitsPerSample, 2);
  file.write((const uint8_t*)"data", 4);
  file.write((const uint8_t*)&subchunk2Size, 4);
}

void startRecording() {
  if (recordingFile) {
    recordingFile.close();
  }
  
  SPIFFS.remove("/recording.raw");
  delay(50);
  
  recordingFile = SPIFFS.open("/recording.raw", FILE_WRITE);
  
  if (!recordingFile) {
    Serial.println("Error creando archivo");
    isRecording = false;
    return;
  }
  
  recordingSamples = 0;
  isRecording = true;
  Serial.println("*** GRABACION INICIADA ***");
}

void stopRecording() {
  isRecording = false;
  
  if (recordingFile) {
    recordingFile.flush();
    recordingFile.close();
  }
  
  Serial.print("*** GRABACION FINALIZADA: ");
  Serial.print(recordingSamples);
  Serial.println(" muestras ***");
}

String extractJsonValue(const String &json, const String &key) {
  int startPos = json.indexOf("\"" + key + "\":\"");
  if (startPos == -1) return "";
  
  startPos += key.length() + 4;
  int endPos = json.indexOf("\"", startPos);
  
  return json.substring(startPos, endPos);
}

bool extractJsonBool(const String &json, const String &key) {
  int pos = json.indexOf("\"" + key + "\":");
  if (pos == -1) return false;
  
  int valueStart = pos + key.length() + 3;
  String remaining = json.substring(valueStart);
  
  int truePos = remaining.indexOf("true");
  int falsePos = remaining.indexOf("false");
  int commaPos = remaining.indexOf(",");
  int bracePos = remaining.indexOf("}");
  
  int endPos = commaPos;
  if (endPos == -1 || (bracePos != -1 && bracePos < endPos)) {
    endPos = bracePos;
  }
  
  if (truePos != -1 && truePos < endPos) {
    return true;
  }
  
  if (falsePos != -1 && falsePos < endPos) {
    return false;
  }
  
  return false;
}

File convertToWav() {
  File rawFile = SPIFFS.open("/recording.raw", FILE_READ);
  if (!rawFile) {
    Serial.println("Error abriendo raw");
    return File();
  }

  SPIFFS.remove("/recording.wav");
  File wavFile = SPIFFS.open("/recording.wav", FILE_WRITE);
  
  if (!wavFile) {
    Serial.println("Error creando wav");
    rawFile.close();
    return File();
  }

  writeWavHeader(wavFile, recordingSamples);

  uint8_t buffer[512];
  while (rawFile.available()) {
    int bytesRead = rawFile.read(buffer, sizeof(buffer));
    wavFile.write(buffer, bytesRead);
  }

  rawFile.close();
  wavFile.flush();
  wavFile.close();
  
  return SPIFFS.open("/recording.wav", FILE_READ);
}

String buildMultipartBody(const String &boundary) {
  String body = "\r\n--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"temperature\"\r\n\r\n";
  body += String(temperatura) + "\r\n";
  
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"light_quantity\"\r\n\r\n";
  body += String(luzAmbiente) + "\r\n";
  
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"humidity\"\r\n\r\n";
  body += String(humedad) + "\r\n";
  
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"ventilador\"\r\n\r\n";
  body += estadoVentilador ? "true\r\n" : "false\r\n";
  
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"persianas\"\r\n\r\n";
  body += estadoPersianas ? "true\r\n" : "false\r\n";
  
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"bulbs\"\r\n\r\n";
  body += estadoBulbs ? "true\r\n" : "false\r\n";
  
  body += "--" + boundary + "--\r\n";
  
  return body;
}

void sendAudioToAPI() {
  if (WiFi.status() != WL_CONNECTED || !SPIFFS.exists("/recording.raw")) {
    return;
  }

  File wavFile = convertToWav();
  if (!wavFile) {
    SPIFFS.remove("/recording.raw");
    return;
  }

  WiFiClient client;
  if (!client.connect(SERVER_HOST, SERVER_PORT)) {
    Serial.println("Error conectando al servidor");
    wavFile.close();
    SPIFFS.remove("/recording.raw");
    SPIFFS.remove("/recording.wav");
    return;
  }

  String boundary = "----ESP32Boundary";
  String headerPart = "--" + boundary + "\r\n";
  headerPart += "Content-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\n";
  headerPart += "Content-Type: audio/wav\r\n\r\n";
  
  String bodyPart = buildMultipartBody(boundary);
  int totalSize = headerPart.length() + wavFile.size() + bodyPart.length();

  client.print("POST /api/v1/pipeline HTTP/1.1\r\n");
  client.print("Host: " + String(SERVER_HOST) + "\r\n");
  client.print("Content-Type: multipart/form-data; boundary=" + boundary + "\r\n");
  client.print("Content-Length: " + String(totalSize) + "\r\n");
  client.print("Connection: close\r\n\r\n");
  client.print(headerPart);

  uint8_t buf[512];
  while (wavFile.available()) {
    int bytesRead = wavFile.read(buf, sizeof(buf));
    if (bytesRead > 0) {
      client.write(buf, bytesRead);
    }
    yield();
  }
  
  wavFile.close();
  client.print(bodyPart);

  unsigned long timeout = millis();
  while (client.available() == 0 && millis() - timeout < 30000) {
    delay(100);
  }

  if (client.available() == 0) {
    Serial.println("Timeout");
    client.stop();
    SPIFFS.remove("/recording.raw");
    SPIFFS.remove("/recording.wav");
    return;
  }

  bool headersEnded = false;
  String response = "";
  
  while (client.available()) {
    String line = client.readStringUntil('\n');
    if (!headersEnded) {
      if (line == "\r" || line.length() == 0) {
        headersEnded = true;
      }
    } else {
      response += line;
    }
  }

  client.stop();

  String audioPath = extractJsonValue(response, "audio_filename");
  String transcript = extractJsonValue(response, "transcription");
  String res = extractJsonValue(response, "answer");
  estadoVentilador = extractJsonBool(response, "ventilador");
  estadoPersianas = extractJsonBool(response, "persianas");
  estadoBulbs = extractJsonBool(response, "bulbs");

  Serial.println("========================================");
  Serial.print("Transcription: ");
  Serial.println(transcript);
  Serial.print("Response: ");
  Serial.println(res);
  Serial.print("Audio: ");
  Serial.println(audioPath);
  Serial.print("Ventilador: ");
  Serial.println(estadoVentilador ? "ON" : "OFF");
  Serial.print("Persianas: ");
  Serial.println(estadoPersianas ? "ABIERTAS" : "CERRADAS");
  Serial.print("Luces: ");
  Serial.println(estadoBulbs ? "ON" : "OFF");
  Serial.println("========================================");

  for (int i = 0; i < 3 && !mqtt.connected(); i++) {
    reconnectMQTT();
    delay(500);
  }

  if (mqtt.connected()) {
    String payload = "{\"audio\":\"" + audioPath + "\"}";
    mqtt.loop();
    delay(100);
    
    if (mqtt.publish("ia", payload.c_str(), false)) {
      mqtt.loop();
      delay(50);
      Serial.println("Publicado en MQTT");
    } else {
      Serial.print("Error MQTT: ");
      Serial.println(mqtt.state());
    }
  } else {
    Serial.println("MQTT desconectado");
  }

  SPIFFS.remove("/recording.raw");
  SPIFFS.remove("/recording.wav");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Inicializando...");
  
  if (!SPIFFS.begin(true)) {
    Serial.println("Error SPIFFS");
    return;
  }
  
  File root = SPIFFS.open("/");
  File file = root.openNextFile();
  while(file) {
    String fileName = file.name();
    if (fileName.endsWith(".raw") || fileName.endsWith(".wav")) {
      SPIFFS.remove(fileName);
    }
    file = root.openNextFile();
  }
  
  connectWiFi();
  setupMQTT();
  reconnectMQTT();
  setupI2S();
  
  Serial.println("Sistema listo!");
  Serial.print("Memoria libre: ");
  Serial.println(ESP.getFreeHeap());
}

void loop() {
  size_t bytesIn = 0;
  esp_err_t result = i2s_read(I2S_PORT, &sBuffer, BUFFER_SIZE * sizeof(int16_t), &bytesIn, portMAX_DELAY);

  if (result == ESP_OK) {
    int samplesRead = bytesIn / sizeof(int16_t);
    int maxAmplitude = 0;
    
    for (int i = 0; i < samplesRead; i++) {
      int absVal = abs(sBuffer[i]);
      if (absVal > maxAmplitude) {
        maxAmplitude = absVal;
      }
    }
    
    if (maxAmplitude > SILENCE_THRESHOLD) {
      lastSoundTime = millis();
      if (!isRecording) {
        startRecording();
      }
    }
    
    if (isRecording && recordingFile) {
      size_t written = recordingFile.write((const uint8_t*)sBuffer, bytesIn);
      
      if (written != bytesIn) {
        Serial.println("Error escribiendo");
        stopRecording();
        SPIFFS.remove("/recording.raw");
        return;
      }
      
      recordingSamples += samplesRead;
      
      if (millis() - lastSoundTime > SILENCE_DURATION) {
        stopRecording();
        if (recordingSamples > 1000) {
          sendAudioToAPI();
        } else {
          Serial.println("Grabacion muy corta");
          SPIFFS.remove("/recording.raw");
        }
        recordingSamples = 0;
      }
      
      if (recordingSamples >= MAX_RECORDING_SIZE) {
        stopRecording();
        sendAudioToAPI();
        recordingSamples = 0;
      }
    }
  }

  static unsigned long lastMqttLoop = 0;
  if (millis() - lastMqttLoop > 100) {
    if (!mqtt.connected()) {
      reconnectMQTT();
    }
    mqtt.loop();
    lastMqttLoop = millis();
  }

  delay(10);
}