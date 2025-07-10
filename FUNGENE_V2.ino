#include <Arduino.h>
#include <ArduinoJson.h>

#include <AD9833.h>
#define FNC_PIN_1 5
AD9833 gen1(FNC_PIN_1);
#define FNC_PIN_2 4
AD9833 gen2(FNC_PIN_2);

struct Channel {
  String type = "Sine";
  float frequency = 1000.0;
  float phase = 0.0;
  bool enabled = true;
};

struct Modulation {
  String type = "MFSK";
  int m = 2;
  float frequency = 100000.0;
  float delta_freq = 1000.0;
  float baud_rate = 1000;
  float mod_time = 10.0;
  bool enabled = false;
  std::vector<int> data;
};

Channel channel1, channel2;
Modulation modulation;

String inputBuffer;

#define XOR_PIN 15
float currentPhase = 0.0;  // in degrees
float kp = 0.5;            // Proportional gain
//float kd = 0.0;            // Derivative gain
const float PHASE_THRESHOLD = 0.1; // degrees

float previousPhaseError = 0.0;
unsigned long previousTime = 0;

int gen_sel = 1;

int indexd = 0;
int maxstate;
int pwstate[1000];
int change_no = 1;

#define PWM_CHANNEL_0 0
#define PWM_PIN 2
int pwm_timer = 12;

int sel_A = 12;
int sel_B = 13;

void setup() {
  gen1.Begin();
  gen1.ApplySignal(SINE_WAVE, REG0, 1000, REG0, 0.0);
  gen1.EnableOutput(true);
  delay(100);

  gen2.Begin();
  gen2.ApplySignal(SINE_WAVE, REG0, 1000, REG0, 0.0);
  gen2.EnableOutput(true);
  delay(100);


  Serial.begin(115200);
  while (!Serial);
  delay(2000);

  pinMode(XOR_PIN, INPUT);
  //previousTime = esp_timer_get_time();

  pinMode(sel_A, OUTPUT);
  pinMode(sel_B, OUTPUT);
}

void communicator() {
  char c = Serial.read();
  if (c == '\n') {
    processCommand(inputBuffer);
    indexd = modulation.data.size() - 1;
    inputBuffer = "";
    change_no = 1;
  } else {
    inputBuffer += c;
  }
  if((channel1.enabled || channel2.enabled || modulation.enabled) && !(modulation.type.equals("AM") || modulation.type.equals("PWM"))) {
    digitalWrite(sel_A, LOW);
    digitalWrite(sel_B, LOW);
  } else if (modulation.type.equals("AM")) {
    digitalWrite(sel_A, HIGH);
    digitalWrite(sel_B, LOW);
  } else if (modulation.type.equals("PWM")) {
    digitalWrite(sel_A, LOW);
    digitalWrite(sel_B, HIGH);
  }
}

void loop() {
  if (Serial.available()) {
    communicator();
  }

  if (modulation.enabled)
    setmod();

  if (change_no && (channel1.enabled || channel2.enabled)){
    setgen();
    change_no = 0;
  }

  if (channel1.enabled && channel2.enabled && (channel1.frequency == channel2.frequency)) {
    unsigned long highTime = pulseIn(XOR_PIN, HIGH);
    unsigned long lowTime = pulseIn(XOR_PIN, LOW);
    unsigned long period = highTime + lowTime;  

  // if (period == 0) {
    //   Serial.println("No signal detected.");
    //   delay(100);
    //   return;
    // }

    float dutyCycle = (float)highTime / period;
    float measuredPhase = dutyCycle * 180.0;

    float targetPhase = channel1.phase - channel2.phase;

    if (targetPhase > 180.0) targetPhase -= 360.0;
    if (targetPhase < -180.0) targetPhase += 360.0;

    if (targetPhase > 173.0) targetPhase = 173.0;
    if (targetPhase < -173.0) targetPhase = 173.0;

    if (targetPhase < 0) {
      gen_sel = 2; 
      targetPhase = fabs(targetPhase);
    } else {
      gen_sel = 1;
    }

    float phaseError = measuredPhase - targetPhase;
    
    // unsigned long currentTime = esp_timer_get_time();
    // float dt = (currentTime - previousTime) / 1000000.0;
    // previousTime = currentTime;

    // Only adjust if phase error is significant
    if (fabs(phaseError) >= PHASE_THRESHOLD) {// && dt > 0) {
      // float derivative = (phaseError - previousPhaseError) / dt;
      float correction = kp * phaseError;// + kd * derivative;
      currentPhase -= correction;

      // Wrap currentPhase between 0–360
      if (currentPhase < 0) currentPhase += 360.0;
      if (currentPhase >= 360.0) currentPhase -= 360.0;

      if (gen_sel == 1)
        gen1.SetPhase(REG0, currentPhase);
      else 
        gen2.SetPhase(REG0, currentPhase);

    }

    previousPhaseError = phaseError;

    //Debug output
    // Serial.print("Duty Cycle: ");
    // Serial.print(dutyCycle, 2);
    // Serial.print("Target: ");
    // Serial.print(targetPhase, 2);
    // Serial.print("°, Measured: ");
    // Serial.print(measuredPhase, 2);
    // Serial.print("°, Error: ");
    // Serial.print(phaseError, 2);
    // Serial.print("°, Gen1 Phase: ");
    // Serial.println(currentPhase, 2);
  }
  
}

WaveformType getWaveformTypeFromString(const String& type) {
  if (type == "Sine") return SINE_WAVE;
  else if (type == "Square") return SQUARE_WAVE;
  else if (type == "Triangle") return TRIANGLE_WAVE;
  else return SINE_WAVE; // Default to Sine if unknown
}

void setgen() {
  if (channel1.enabled == true)
    gen1.ApplySignal(getWaveformTypeFromString(channel1.type), REG0, channel1.frequency, REG0, channel1.phase);
  if (channel2.enabled == true)
    gen2.ApplySignal(getWaveformTypeFromString(channel2.type), REG0, channel2.frequency, REG0, channel2.phase);
}

void BSK() {
  int timerz = (1000000 / modulation.baud_rate) - 39;
  if (timerz < 0) {
    timerz = 0;
  }
  for (int i = 0; i <= indexd; i++) {
    if (modulation.data[i] > maxstate) {
      modulation.data[i] = maxstate;
    }
  }
  long int timer = esp_timer_get_time();
  while (esp_timer_get_time() - timer <= modulation.mod_time * 1000000) {
    for (int i = 0; i <= indexd; i++) {
      if (modulation.data[i] == 0) {
        gen1.SetOutputSource(REG0);
      } else {
        gen1.SetOutputSource(REG1);
      }
      if (Serial.available()) {
        communicator();
      }
      delayMicroseconds(timerz);
    }
  }
}

void FSK() {
  int timerz = (1000000 / modulation.baud_rate) - 114;
  if (timerz < 0) {
    timerz = 0;
  }
  int prevstate = 0;
  for (int i = 0; i <= indexd; i++) {
    if (modulation.data[i] > maxstate) {
      modulation.data[i] = maxstate;
    }
  }
  gen1.ApplySignal(SINE_WAVE, REG0, modulation.frequency, REG0, 0.0);
  long int timer = esp_timer_get_time();
  while (esp_timer_get_time() - timer <= modulation.mod_time * 1000000) {
    for (int i = 0; i <= indexd; i++) {
      gen1.IncrementFrequency(REG0, (modulation.data[i] - prevstate) * modulation.delta_freq);
      prevstate = modulation.data[i];
      if (Serial.available()) {
        communicator();
      }
      delayMicroseconds(timerz);
    }
  }
}

void PSK() {
  int timerz = (1000000 / modulation.baud_rate) - 40;
  if (timerz < 0) {
    timerz = 0;
  }
  //int prevstate = 0;
  for (int i = 0; i <= indexd; i++) {
    if (modulation.data[i] > maxstate) {
      modulation.data[i] = maxstate;
    }
  }
  for (int i = 0; i <= indexd; i++) {
    pwstate[i] = modulation.data[i] ^ (modulation.data[i] >> 1);
  }
  gen1.ApplySignal(SINE_WAVE, REG0, modulation.frequency, REG0, 0.0);
  long int timer = esp_timer_get_time();
  while (esp_timer_get_time() - timer <= modulation.mod_time * 1000000) {
    for (int i = 0; i <= indexd; i++) {
      //gen.IncrementPhase(REG0, (pwstate[i] - prevstate) * phasebuff);
      gen1.SetPhase(REG0, pwstate[i] * modulation.delta_freq);
      //prevstate = pwstate[i];
      if (Serial.available()) {
        communicator();
      }
      delayMicroseconds(timerz);
    }
  }
}

void ASK() {
  int timerz = (1000000 / modulation.baud_rate) - 39;
  if (timerz < 0) {
    timerz = 0;
  }
  for (int i = 0; i <= indexd; i++) {
    if (modulation.data[i] > maxstate) {
      modulation.data[i] = maxstate;
    }
  }
  gen1.ApplySignal(SINE_WAVE, REG0, modulation.frequency, REG0, 0.0);
  long int timer = esp_timer_get_time();
  while (esp_timer_get_time() - timer <= modulation.mod_time * 1000000) {
    for (int i = 0; i <= indexd; i++) {
      if (modulation.data[i] == 0) {
        gen1.EnableOutput(false);
      } else {
        gen1.EnableOutput(true);
      }
      if (Serial.available()) {
        communicator();
      }
      delayMicroseconds(timerz);
    }
  }
  gen1.EnableOutput(true);
}

void PWM() {
  int timerz = (1000000 / modulation.baud_rate) - 5;
  if (timerz < 0) {
    timerz = 0;
  }
  long int timer = esp_timer_get_time();
  while (esp_timer_get_time() - timer <= modulation.mod_time * 1000000) {
    for (int i = 0; i <= indexd; i++) {
      ledcWrite(PWM_CHANNEL_0, pwstate[i]);
      if (Serial.available()) {
        communicator();
      }
      delayMicroseconds(timerz);
    }
  }
}

void SWEEP() {
  int parts;
  int temp_int = (1000000 / modulation.baud_rate);
  parts = modulation.m;
  int bufferfreq = modulation.delta_freq;
  int i = modulation.frequency;
  int timerz = temp_int - 114;
  if (timerz < 0) {
    timerz = 0;
  }
  //gen1.SetFrequency(REG0, i);
  long int timer = esp_timer_get_time();
  while (esp_timer_get_time() - timer <= modulation.mod_time * 1000000) {
    for (int iter = 0; iter < parts; iter++){
      gen1.SetFrequency(REG0, i);
      i += bufferfreq;
      delayMicroseconds(timerz);
      if (Serial.available()) {
        communicator();
      }
    }
    i = modulation.frequency;
  }
  gen1.SetFrequency(REG0, modulation.frequency);
}

void setmod() {
  if (modulation.type.equals("MFSK") && modulation.m == 2) {
    maxstate = 1;
    int temp_freq_max = modulation.frequency + modulation.delta_freq;
    gen1.ApplySignal(SINE_WAVE, REG1, temp_freq_max, REG1, 0.0);
    gen1.ApplySignal(SINE_WAVE, REG0, modulation.frequency, REG0, 0.0);
    BSK();
  } else if (modulation.type.equals("MPSK") && modulation.m == 2) {
    maxstate = 1;
    gen1.ApplySignal(SINE_WAVE, REG1, modulation.frequency, REG1, modulation.delta_freq);
    gen1.ApplySignal(SINE_WAVE, REG0, modulation.frequency, REG0, 0.0);
    BSK();
  } else if (modulation.type.equals("MFSK")) {
    maxstate = modulation.m - 1;
    FSK();
  } else if (modulation.type.equals("MPSK")) {
    maxstate = modulation.m - 1;
    PSK();
  } else if (modulation.type.equals("ASK")) {
    maxstate = 1;
    ASK();
  } else if (modulation.type.equals("SWEEP")) {
    SWEEP();
  } else if (modulation.type.equals("AM")) {
    gen1.ApplySignal(SINE_WAVE, REG0, modulation.frequency, REG0, 0.0);
    gen2.ApplySignal(SINE_WAVE, REG0, modulation.baud_rate, REG0, 0.0);
    long int pT = esp_timer_get_time();
    while (esp_timer_get_time() - pT < modulation.mod_time * 1000000) {
      if (Serial.available()) {
        communicator();
      }
    }
  } else if (modulation.type.equals("PWM")) {
    if (modulation.frequency <= 76) {
      pwm_timer = 20;
      maxstate = 1048575;
    } else if (modulation.frequency <= 152) {
      pwm_timer = 19;
      maxstate = 524287;
    } else if (modulation.frequency <= 305) {
      pwm_timer = 18;
      maxstate = 262143;
    } else if (modulation.frequency <= 611) {
      pwm_timer = 17;
      maxstate = 131071;
    } else if (modulation.frequency <= 1223) {
      pwm_timer = 16;
      maxstate = 65535;
    } else if (modulation.frequency <= 2446) {
      pwm_timer = 15;
      maxstate = 32767;
    } else if (modulation.frequency <= 4892) {
      pwm_timer = 14;
      maxstate = 16383;
    } else if (modulation.frequency <= 9784) {
      pwm_timer = 13;
      maxstate = 8191;
    } else if (modulation.frequency <= 19569) {
      pwm_timer = 12;
      maxstate = 4095;
    } else if (modulation.frequency <= 39138) {
      pwm_timer = 11;
      maxstate = 2047;
    } else if (modulation.frequency <= 78277) {
      pwm_timer = 10;
      maxstate = 1023;
    } else if (modulation.frequency <= 156555) {
      pwm_timer = 9;
      maxstate = 511;
    } else if (modulation.frequency <= 313111) {
      pwm_timer = 8;
      maxstate = 255;
    } else if (modulation.frequency <= 626223) {
      pwm_timer = 7;
      maxstate = 127;
    } else if (modulation.frequency <= 1252446) {
      pwm_timer = 6;
      maxstate = 63;
    } else if (modulation.frequency <= 2504892) {
      pwm_timer = 5;
      maxstate = 31;
    } else if (modulation.frequency <= 5009784) {
      pwm_timer = 4;
      maxstate = 15;
    } else if (modulation.frequency <= 10019568) {
      pwm_timer = 3;
      maxstate = 7;
    } else if (modulation.frequency <= 20039136) {
      pwm_timer = 2;
      maxstate = 3;
    } else {
      pwm_timer = 1;
      maxstate = 1;
    }
    for (int i = 0; i <= indexd; i++) {
      pwstate[i] = map(modulation.data[i], 0, 100, 0, maxstate+1);
      if (pwstate[i] > maxstate) {
        pwstate[i] = maxstate;
      }
    }
    ledcAttach(PWM_PIN, modulation.frequency, pwm_timer);
    if (indexd == 0) {
      ledcWrite(PWM_PIN, pwstate[0]);
      long int pT = esp_timer_get_time();
      while (esp_timer_get_time() - pT < modulation.mod_time * 1000000) {
        if (Serial.available()) {
          communicator();
        }
      }
    } else {
      PWM();
    }
    ledcDetach(PWM_PIN);
  }
  //modulation.data.size()
}

void processCommand(String jsonStr) {
  StaticJsonDocument<1024> doc;
  DeserializationError error = deserializeJson(doc, jsonStr);

  if (error) {
    sendError("Invalid JSON");
    return;
  }

  String cmd = doc["cmd"] | "";
  if (cmd == "get_settings") {
    sendSettings();
  } else if (cmd == "set_channel") {
    int ch = doc["channel"] | 1;
    if (ch != 1 && ch != 2) {
      sendError("Invalid channel");
      return;
    }

    Channel* target = (ch == 1) ? &channel1 : &channel2;

    target->type = doc["type"] | target->type;
    target->frequency = doc["frequency"] | target->frequency;
    target->phase = doc["phase"] | target->phase;
    target->enabled = doc["enabled"] | target->enabled;

    // Apply channel settings to hardware here...

    sendOK();
  } else if (cmd == "set_modulation") {
    modulation.type = doc["type"] | modulation.type;
    modulation.m = doc["m"] | modulation.m;
    modulation.frequency = doc["frequency"] | modulation.frequency;
    modulation.delta_freq = doc["delta_freq"] | modulation.delta_freq;
    modulation.baud_rate = doc["baud_rate"] | modulation.baud_rate;
    modulation.mod_time = doc["mod_time"] | modulation.mod_time;
    modulation.enabled = doc["enabled"] | modulation.enabled;

    modulation.data.clear();
    if (doc["data"].is<JsonArray>()) {
      for (int val : doc["data"].as<JsonArray>()) {
        modulation.data.push_back(val);
      }
    }

    // Apply modulation settings to hardware here...

    sendOK();
  } else {
    sendError("Unknown command");
  }
}

void sendSettings() {
  StaticJsonDocument<1024> doc;
  doc["status"] = "ok";

  JsonObject ch1 = doc.createNestedObject("channel1");
  ch1["type"] = channel1.type;
  ch1["frequency"] = channel1.frequency;
  ch1["phase"] = channel1.phase;
  ch1["enabled"] = channel1.enabled;

  JsonObject ch2 = doc.createNestedObject("channel2");
  ch2["type"] = channel2.type;
  ch2["frequency"] = channel2.frequency;
  ch2["phase"] = channel2.phase;
  ch2["enabled"] = channel2.enabled;

  JsonObject mod = doc.createNestedObject("modulation");
  mod["type"] = modulation.type;
  mod["m"] = modulation.m;
  mod["frequency"] = modulation.frequency;
  mod["delta_freq"] = modulation.delta_freq;
  mod["baud_rate"] = modulation.baud_rate;
  mod["mod_time"] = modulation.mod_time;
  mod["enabled"] = modulation.enabled;

  JsonArray dataArray = mod.createNestedArray("data");
  for (int val : modulation.data) {
    dataArray.add(val);
  }

  serializeJson(doc, Serial);
  Serial.println();
}

void sendOK() {
  Serial.println("{\"status\":\"ok\"}");
}

void sendError(String message) {
  StaticJsonDocument<256> err;
  err["status"] = "error";
  err["error"] = message;
  serializeJson(err, Serial);
  Serial.println();
}
