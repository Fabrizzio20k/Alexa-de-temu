#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <driver/i2s.h>

const char* WIFI_SSID = "iPhone de Fabrizzio";
const char* WIFI_PASSWORD = "123456789";
const char* MQTT_SERVER = "172.20.10.2";
const int MQTT_PORT = 1883;
const char* AUDIO_SERVER_URL = "http://172.20.10.2:8000/api/v1/audio/";

#define I2S_BCLK 26
#define I2S_LRCK 27
#define I2S_DOUT 25
#define BUFFER_SIZE 512
#define WAV_HEADER_SIZE 44
#define DMA_BUFFER_COUNT 8
#define DMA_BUFFER_LENGTH 1024

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
    .dma_buf_count = DMA_BUFFER_COUNT,
    .dma_buf_len = DMA_BUFFER_LENGTH,
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

uint32_t extractSampleRateFromWav(WiFiClient* stream) {
  uint8_t header[WAV_HEADER_SIZE];
  stream->readBytes(header, WAV_HEADER_SIZE);
  
  uint32_t sampleRate = header[24] | 
                        (header[25] << 8) | 
                        (header[26] << 16) | 
                        (header[27] << 24);
  
  return sampleRate;
}

void streamAudioToI2S(WiFiClient* stream) {
  uint8_t buffer[BUFFER_SIZE];
  
  while (stream->available()) {
    int bytesRead = stream->readBytes(buffer, BUFFER_SIZE);
    if (bytesRead > 0) {
      size_t bytesWritten;
      i2s_write(I2S_NUM_0, buffer, bytesRead, &bytesWritten, portMAX_DELAY);
    }
  }
}

void playAudio(const String& audioFilename) {
  String audioURL = String(AUDIO_SERVER_URL) + audioFilename;
  
  Serial.println("Descargando: " + audioURL);

  HTTPClient http;
  http.begin(audioURL);
  int httpCode = http.GET();

  if (httpCode != HTTP_CODE_OK) {
    Serial.println("Error HTTP: " + String(httpCode));
    http.end();
    return;
  }

  WiFiClient* stream = http.getStreamPtr();
  uint32_t sampleRate = extractSampleRateFromWav(stream);
  
  Serial.print("Sample rate: ");
  Serial.println(sampleRate);
  
  i2s_driver_uninstall(I2S_NUM_0);
  setupI2S(sampleRate);

  Serial.println("Reproduciendo...");
  streamAudioToI2S(stream);
  
  delay(350);
  i2s_zero_dma_buffer(I2S_NUM_0);
  
  Serial.println("Finalizado");
  http.end();
}

void processIncomingMessage(const JsonDocument& doc) {
  String audioFilename = doc["audio"].as<String>();
  
  Serial.println("Audio: " + audioFilename);
  
  if (audioFilename.length() > 0) {
    pendingAudio = audioFilename;
    shouldPlayAudio = true;
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.println("Mensaje MQTT recibido");
  
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) {
    Serial.println("Error parseando JSON: " + String(error.c_str()));
    return;
  }
  
  processIncomingMessage(doc);
}

void connectMQTT() {
  while (!mqtt.connected()) {
    Serial.println("Conectando a MQTT...");
    
    String clientId = "ESP32Speaker-" + String(random(0xffff), HEX);
    
    if (mqtt.connect(clientId.c_str())) {
      Serial.println("MQTT conectado");
      mqtt.subscribe("ia");
      Serial.println("Suscrito a 'ia'");
    } else {
      Serial.print("Error MQTT: ");
      Serial.println(mqtt.state());
      delay(5000);
    }
  }
}

void connectWiFi() {
  Serial.println("Conectando a WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi conectado");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  delay(500);
  
  randomSeed(micros());
  
  connectWiFi();
  setupI2S(22050);
  
  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(512);
  
  connectMQTT();
  
  Serial.println("Sistema listo");
}

void loop() {
  if (!mqtt.connected()) {
    connectMQTT();
  }
  
  mqtt.loop();
  
  if (shouldPlayAudio && pendingAudio.length() > 0) {
    shouldPlayAudio = false;
    playAudio(pendingAudio);
    pendingAudio = "";
  }
}