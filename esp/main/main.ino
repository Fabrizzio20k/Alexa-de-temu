#include <driver/i2s.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <FS.h>
#include <SPIFFS.h>
#include <PubSubClient.h>

#define I2S_WS 15
#define I2S_SD 32
#define I2S_SCK 14
#define I2S_PORT I2S_NUM_0
#define SAMPLE_RATE 16000
#define BUFFER_SIZE 512

WiFiClient mqttClient;
PubSubClient mqtt(mqttClient);

const char* mqttServer = "172.20.10.3";
const int mqttPort = 1883;

const char* ssid = "iPhone de Fabrizzio";
const char* password = "123456789";
const char* serverHost = "172.20.10.3";
const int port = 8000;
const char* serverUrl = "http://172.20.10.3:8000/api/v1/transcribe";

#define SILENCE_THRESHOLD 2300
#define SILENCE_DURATION 1500
#define MAX_RECORDING_SIZE 64000

int16_t sBuffer[BUFFER_SIZE];
bool isRecording = false;
unsigned long lastSoundTime = 0;
File recordingFile;
int recordingSamples = 0;

bool estadoVentilador = true;
bool estadoPersianas = true;
bool estadoBulbs = true;
float temperatura = 20.0;
float humedad = 20.0;
float luzAmbiente = 20.0;

void i2s_install() {
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

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
}

void i2s_setpin() {
  const i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = -1,
    .data_in_num = I2S_SD
  };

  i2s_set_pin(I2S_PORT, &pin_config);
}

void connectWiFi() {
  Serial.println("Conectando a WiFi...");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("");
  Serial.println("WiFi conectado!");
  Serial.print("IP del ESP32: ");
  Serial.println(WiFi.localIP());
}

void writeWavHeader(File &file, int dataSize) {
  int subchunk2Size = dataSize * 2;
  int chunkSize = 36 + subchunk2Size;

  file.write((const uint8_t*)"RIFF", 4);
  file.write((const uint8_t*)&chunkSize, 4);
  file.write((const uint8_t*)"WAVE", 4);
  file.write((const uint8_t*)"fmt ", 4);
  
  int subchunk1Size = 16;
  int16_t audioFormat = 1;
  int16_t numChannels = 1;
  int sampleRate = SAMPLE_RATE;
  int byteRate = SAMPLE_RATE * 2;
  int16_t blockAlign = 2;
  int16_t bitsPerSample = 16;
  
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
  if (SPIFFS.exists("/recording.raw")) {
    SPIFFS.remove("/recording.raw");
  }
  
  recordingFile = SPIFFS.open("/recording.raw", FILE_WRITE);
  
  if (!recordingFile) {
    Serial.println("Error al crear archivo de grabacion");
    return;
  }
  
  recordingSamples = 0;
  isRecording = true;
  Serial.println("*** GRABACION INICIADA ***");
}

void stopRecording() {
  if (recordingFile) {
    recordingFile.flush();
    recordingFile.close();
    delay(100);
  }
  
  isRecording = false;
  Serial.println("*** GRABACION FINALIZADA ***");
  Serial.print("Muestras grabadas: ");
  Serial.println(recordingSamples);
}

void reconnectMQTT() {
  while (!mqtt.connected()) {
    if (mqtt.connect("ESP32Client")) {
      Serial.println("MQTT conectado");
    } else {
      delay(5000);
    }
  }
}

void sendAudioToAPI() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado");
    return;
  }

  if (!SPIFFS.exists("/recording.raw")) {
    Serial.println("Archivo raw no existe");
    return;
  }

  if (SPIFFS.exists("/recording.wav")) {
    SPIFFS.remove("/recording.wav");
  }

  File rawFile = SPIFFS.open("/recording.raw", FILE_READ);
  if (!rawFile) {
    Serial.println("Error al abrir archivo raw");
    return;
  }

  File wavFile = SPIFFS.open("/recording.wav", FILE_WRITE);
  if (!wavFile) {
    Serial.println("Error al crear archivo wav");
    rawFile.close();
    return;
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
  delay(200);

  File file = SPIFFS.open("/recording.wav", FILE_READ);
  if (!file) {
    Serial.println("Error al abrir wav final");
    return;
  }

  int fileSize = file.size();

  String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
  
  String headerPart = "--" + boundary + "\r\n";
  headerPart += "Content-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\n";
  headerPart += "Content-Type: audio/wav\r\n\r\n";
  
  String temperaturePart = "\r\n--" + boundary + "\r\n";
  temperaturePart += "Content-Disposition: form-data; name=\"temperature\"\r\n\r\n";
  temperaturePart += String(temperatura) + "\r\n";
  
  String lightPart = "--" + boundary + "\r\n";
  lightPart += "Content-Disposition: form-data; name=\"light_quantity\"\r\n\r\n";
  lightPart += String(luzAmbiente) + "\r\n";
  
  String humidityPart = "--" + boundary + "\r\n";
  humidityPart += "Content-Disposition: form-data; name=\"humidity\"\r\n\r\n";
  humidityPart += String(humedad) + "\r\n";
  
  String ventiladorPart = "--" + boundary + "\r\n";
  ventiladorPart += "Content-Disposition: form-data; name=\"ventilador\"\r\n\r\n";
  ventiladorPart += (estadoVentilador ? "true" : "false") + String("\r\n");
  
  String persianasPart = "--" + boundary + "\r\n";
  persianasPart += "Content-Disposition: form-data; name=\"persianas\"\r\n\r\n";
  persianasPart += (estadoPersianas ? "true" : "false") + String("\r\n");
  
  String bulbsPart = "--" + boundary + "\r\n";
  bulbsPart += "Content-Disposition: form-data; name=\"bulbs\"\r\n\r\n";
  bulbsPart += (estadoBulbs ? "true" : "false") + String("\r\n");
  
  String footerPart = "--" + boundary + "--\r\n";

  WiFiClient client;
  
  if (!client.connect(serverHost, port)) {
    Serial.println("Error al conectar con el servidor");
    file.close();
    return;
  }

  int totalSize = headerPart.length() + fileSize + temperaturePart.length() + 
                  lightPart.length() + humidityPart.length() + ventiladorPart.length() + 
                  persianasPart.length() + bulbsPart.length() + footerPart.length();

  client.print("POST /api/v1/pipeline HTTP/1.1\r\n");
  client.print("Host: " + String(serverHost) + ":" + String(port) + "\r\n");
  client.print("Content-Type: multipart/form-data; boundary=" + boundary + "\r\n");
  client.print("Content-Length: " + String(totalSize) + "\r\n");
  client.print("Connection: close\r\n\r\n");
  
  client.print(headerPart);

  uint8_t buf[512];
  while (file.available()) {
    int bytesRead = file.read(buf, sizeof(buf));
    if (bytesRead > 0) {
      client.write(buf, bytesRead);
    }
    yield();
  }
  
  file.close();
  
  client.print(temperaturePart);
  client.print(lightPart);
  client.print(humidityPart);
  client.print(ventiladorPart);
  client.print(persianasPart);
  client.print(bulbsPart);
  client.print(footerPart);

  unsigned long timeout = millis();
  while (client.available() == 0) {
    if (millis() - timeout > 30000) {
      Serial.println("Timeout esperando respuesta");
      client.stop();
      SPIFFS.remove("/recording.raw");
      SPIFFS.remove("/recording.wav");
      return;
    }
    delay(100);
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

  int transcriptionStart = response.indexOf("\"transcription\":\"") + 17;
  int transcriptionEnd = response.indexOf("\"", transcriptionStart);
  String transcription = response.substring(transcriptionStart, transcriptionEnd);

  int audioStart = response.indexOf("\"audio_filename\":\"") + 18;
  int audioEnd = response.indexOf("\"", audioStart);
  String audioFilename = response.substring(audioStart, audioEnd);

  int answerStart = response.indexOf("\"answer\":\"") + 10;
  int answerEnd = response.indexOf("\"", answerStart);
  String answer = response.substring(answerStart, answerEnd);

  int ventiladorPos = response.indexOf("\"ventilador\":");
  if (ventiladorPos != -1) {
    int valueStart = ventiladorPos + 13;
    String valueStr = response.substring(valueStart, valueStart + 5);
    estadoVentilador = valueStr.indexOf("true") != -1;
  }

  int persianaPos = response.indexOf("\"persianas\":");
  if (persianaPos != -1) {
    int valueStart = persianaPos + 12;
    String valueStr = response.substring(valueStart, valueStart + 5);
    estadoPersianas = valueStr.indexOf("true") != -1;
  }

  int bulbsPos = response.indexOf("\"bulbs\":");
  if (bulbsPos != -1) {
    int valueStart = bulbsPos + 8;
    String valueStr = response.substring(valueStart, valueStart + 5);
    estadoBulbs = valueStr.indexOf("true") != -1;
  }

  Serial.println("========================================");
  Serial.print("Transcripcion: ");
  Serial.println(transcription);
  Serial.print("Respuesta: ");
  Serial.println(answer);
  Serial.print("Audio: ");
  Serial.println(audioFilename);
  Serial.print("Ventilador: ");
  Serial.println(estadoVentilador ? "ON" : "OFF");
  Serial.print("Persianas: ");
  Serial.println(estadoPersianas ? "ABIERTAS" : "CERRADAS");
  Serial.print("Luces: ");
  Serial.println(estadoBulbs ? "ON" : "OFF");
  Serial.print("Temperatura: ");
  Serial.print(temperatura);
  Serial.println("°C");
  Serial.print("Humedad: ");
  Serial.print(humedad);
  Serial.println("%");
  Serial.print("Luz ambiente: ");
  Serial.print(luzAmbiente);
  Serial.println("%");
  Serial.println("========================================");

  if (!mqtt.connected()) {
    reconnectMQTT();
  }

  String payload = "{\"transcription\":\"" + transcription + "\",\"answer\":\"" + answer + 
                  "\",\"audio\":\"" + audioFilename + "\",\"ventilador\":" + (estadoVentilador ? "true" : "false") + 
                  ",\"persianas\":" + (estadoPersianas ? "true" : "false") + 
                  ",\"bulbs\":" + (estadoBulbs ? "true" : "false") + 
                  ",\"temperatura\":" + String(temperatura) + 
                  ",\"humedad\":" + String(humedad) + 
                  ",\"luz\":" + String(luzAmbiente) + "}";

  mqtt.publish("ia", payload.c_str());
  Serial.println("Publicado en MQTT topic 'ia'");

  SPIFFS.remove("/recording.raw");
  SPIFFS.remove("/recording.wav");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Inicializando sistema...");
  
  if (!SPIFFS.begin(true)) {
    Serial.println("Error montando SPIFFS");
    return;
  }
  
  Serial.print("SPIFFS total: ");
  Serial.println(SPIFFS.totalBytes());
  Serial.print("SPIFFS usado: ");
  Serial.println(SPIFFS.usedBytes());
  
  connectWiFi();
  mqtt.setServer(mqttServer, mqttPort);
  
  delay(1000);
  
  i2s_install();
  i2s_setpin();
  i2s_start(I2S_PORT);
  
  Serial.println("Sistema listo! Esperando deteccion de voz...");
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
        Serial.println("Error al escribir en archivo");
        stopRecording();
        return;
      }
      recordingSamples += samplesRead;
      
      if (millis() - lastSoundTime > SILENCE_DURATION) {
        stopRecording();
        
        if (recordingSamples > 1000) {
          sendAudioToAPI();
        } else {
          Serial.println("Grabacion muy corta, descartada");
          SPIFFS.remove("/recording.raw");
        }
        
        recordingSamples = 0;
      }
      
      if (recordingSamples >= MAX_RECORDING_SIZE) {
        stopRecording();
        Serial.println("*** BUFFER LLENO - Enviando ***");
        sendAudioToAPI();
        recordingSamples = 0;
      }
    }
  }
  
  mqtt.loop();

  delay(10);
}