#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "driver/i2s.h"

const char* ssid = "iPhone de Fabrizzio";
const char* password = "123456789";

const char* mqttServer = "172.20.10.3";
const int mqttPort = 1883;

const char* serverUrl = "http://172.20.10.3:8000/api/v1/audio/";

#define I2S_BCLK 26
#define I2S_LRCK 27
#define I2S_DOUT 25

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

String pendingAudio = "";
bool shouldPlayAudio = false;

void setupI2S(uint32_t sampleRate) {
  i2s_config_t i2s_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
      .sample_rate = sampleRate,
      .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
      .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
      .communication_format = I2S_COMM_FORMAT_I2S,
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 8,
      .dma_buf_len = 1024,
      .use_apll = false
  };

  i2s_pin_config_t pin_config = {
      .bck_io_num = I2S_BCLK,
      .ws_io_num = I2S_LRCK,
      .data_out_num = I2S_DOUT,
      .data_in_num = -1
  };

  i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin_config);
}

uint32_t readWavSampleRate(WiFiClient* stream) {
  uint8_t header[44];
  stream->readBytes(header, 44);
  
  uint32_t sampleRate = header[24] | (header[25] << 8) | (header[26] << 16) | (header[27] << 24);
  
  return sampleRate;
}

void playAudio(String audioFilename) {
  String audioURL = String(serverUrl) + audioFilename;
  
  Serial.println("Descargando audio: " + audioURL);

  HTTPClient http;
  http.begin(audioURL);
  int httpCode = http.GET();

  if (httpCode != HTTP_CODE_OK) {
    Serial.println("Error al obtener archivo");
    http.end();
    return;
  }

  WiFiClient* stream = http.getStreamPtr();

  uint32_t sampleRate = readWavSampleRate(stream);
  Serial.print("Sample rate detectado: ");
  Serial.println(sampleRate);
  
  i2s_driver_uninstall(I2S_NUM_0);
  setupI2S(sampleRate);

  const size_t bufferSize = 512;
  uint8_t buffer[bufferSize];

  Serial.println("Reproduciendo...");

  while (http.connected() && stream->available()) {
    int len = stream->readBytes(buffer, bufferSize);
    if (len > 0) {
      size_t written;
      i2s_write(I2S_NUM_0, buffer, len, &written, portMAX_DELAY);
    }
  }

  i2s_zero_dma_buffer(I2S_NUM_0);
  delay(100);

  Serial.println("Audio terminado.");
  http.end();
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.println("Mensaje recibido en topic: " + String(topic));
  
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) {
    Serial.println("Error parseando JSON");
    return;
  }
  
  String audioFilename = doc["audio"].as<String>();
  String transcription = doc["transcription"].as<String>();
  String answer = doc["answer"].as<String>();
  
  Serial.println("Transcripcion: " + transcription);
  Serial.println("Respuesta: " + answer);
  Serial.println("Audio: " + audioFilename);
  
  if (audioFilename.length() > 0) {
    pendingAudio = audioFilename;
    shouldPlayAudio = true;
  }
}

void reconnectMQTT() {
  while (!mqtt.connected()) {
    Serial.println("Conectando a MQTT...");
    if (mqtt.connect("ESP32Speaker")) {
      Serial.println("MQTT conectado");
      mqtt.subscribe("ia");
      Serial.println("Suscrito a topic 'ia'");
    } else {
      Serial.println("Error MQTT, reintentando en 5s");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println("Conectando a WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado!");
  Serial.println(WiFi.localIP());

  setupI2S(22050);
  
  mqtt.setServer(mqttServer, mqttPort);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(512);
  
  reconnectMQTT();
}

void loop() {
  if (!mqtt.connected()) {
    reconnectMQTT();
  }
  mqtt.loop();
  
  if (shouldPlayAudio && pendingAudio.length() > 0) {
    shouldPlayAudio = false;
    playAudio(pendingAudio);
    pendingAudio = "";
  }
}
