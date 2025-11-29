const int LDR_PIN = A0;
const int MOTOR_PIN = 7;

bool motorState = false;

void setup() {
  Serial.begin(9600);
  pinMode(LDR_PIN, INPUT);
  pinMode(MOTOR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, LOW);
}

void loop() {
  int ldrValue = analogRead(LDR_PIN);
  float luzPorcentaje = map(ldrValue, 0, 1023, 0, 100);
  
  Serial.print("LUZ:");
  Serial.println(luzPorcentaje);
  
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    
    if (data.startsWith("MOTOR:")) {
      String stateStr = data.substring(6);
      stateStr.trim();
      
      if (stateStr == "1") {
        motorState = true;
        digitalWrite(MOTOR_PIN, HIGH);
      } else if (stateStr == "0") {
        motorState = false;
        digitalWrite(MOTOR_PIN, LOW);
      }
    }
  }
  
  delay(1000);
}