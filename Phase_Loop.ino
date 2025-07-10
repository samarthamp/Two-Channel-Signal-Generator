#include "AD9833.h"

#define XOR_PIN 15
#define AD9833_FSYNC1 5
#define AD9833_FSYNC2 4
AD9833 gen1(AD9833_FSYNC1);
AD9833 gen2(AD9833_FSYNC2);
#define freq 1000000

float currentPhase = 0.0;  // in degrees
float targetPhase = 90.0;  // desired phase difference in degrees
float kp = 0.5;            // Proportional gain
//float kd = 0.0;            // Derivative gain
const float PHASE_THRESHOLD = 0.1; // degrees

float previousPhaseError = 0.0;
unsigned long previousTime = 0;

void setup() {
  gen1.Begin();
  gen1.ApplySignal(SINE_WAVE, REG0, freq, REG0, 0.0);
  gen1.EnableOutput(true);
  delay(100);

  gen2.Begin();
  gen2.ApplySignal(SINE_WAVE, REG0, freq, REG0, 0.0);
  gen2.EnableOutput(true);
  delay(100);

  Serial.begin(115200);
  while (!Serial);
  delay(500);

  pinMode(XOR_PIN, INPUT);
  //previousTime = esp_timer_get_time();
}

void loop() {
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

  // Compute signed error from target
  float phaseError = measuredPhase - targetPhase;

  // Wrap error to -180 to 180 for shortest path
  // if (phaseError > 180.0) phaseError -= 360.0;
  // if (phaseError < -180.0) phaseError += 360.0;
  
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
