#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>

const char* ssid = "Nothing";
const char* password = "Theriyadhu.";

HTTPClient http;
WiFiClient client;

const int motionSensor = D7;
const int soundSensor = A0;
const int trigPin = D5;
const int echoPin = D6;

int currSoundVal, prevSoundVal;
int currDistance, prevDistance;

int isMotionDetected() {
  return digitalRead(motionSensor) == HIGH;
}


int getDistance() {
  int distance, duration;
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  duration = pulseIn(echoPin, HIGH);
  distance= duration*0.034/2;

  return distance;
}


int getSound() {
  return analogRead(soundSensor);
}


void setupMotionSensor() {
  pinMode(motionSensor, INPUT);
}


void setupUltraSonicSensor() {
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  prevDistance = getDistance();
}


void setupSoundSensor() {
  pinMode(soundSensor, INPUT);
  prevSoundVal = getSound();
}


void setupWifi() {
  WiFi.begin(ssid, password);
  while ( WiFi.status() != WL_CONNECTED ) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
}


int isSoundDetected() {
  currSoundVal = getSound();
  if ( !( prevSoundVal - 10 < currSoundVal && prevSoundVal + 10 > currSoundVal ) ) {
    prevSoundVal = currSoundVal;
    return 1;
  }
  return 0;
}

int isDistanceDetected(int tmp) {
  /* currDistance = getDistance();
  //currDistance = tmp > 0 ? tmp : currDistance;
  Serial.print(prevDistance);
  Serial.print(" ");
  Serial.println(currDistance); */
  //int tmp = getDistance();
  Serial.println(tmp);
  //if ( !( prevDistance - 10 < currDistance && prevDistance + 10 > currDistance ) ) {
  if ( ( tmp > 0 && tmp < 20 ) ) {
    //prevDistance = currDistance;
    return 1;
  }
  //prevDistance = currDistance;
  return 0;
}


void postRequest(int motionDetected, int sound, int soundDetected, int distance, int distanceDetected) {
  StaticJsonDocument<200> doc;
  doc["motionDetected"] = motionDetected;
  doc["sound"] = sound;
  doc["soundDetected"] = soundDetected;
  doc["distance"] = distance;
  doc["distanceDetected"] = distanceDetected;
  String json;
  serializeJson(doc, json);

  http.begin(client, "http://192.168.139.214:5000");
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(json);
  Serial.print("Response Status Code : ");
  Serial.println(code);
  if ( code == 200 ) {
    Serial.print("Response : ");
    Serial.println(http.getString());
  } else {
    Serial.print("Some Error occurred - Response : ");
    Serial.println(http.getString());
  }
  http.end();
  //delay(10000);
}


void setup() {
  Serial.begin(9600);
  setupMotionSensor();
  setupUltraSonicSensor();
  setupSoundSensor();
  setupWifi();
  pinMode(D4, OUTPUT);
}


void loop() {
  int motionDetected = 0, soundDetected = 0, distanceDetected = 0;
  int sound, distance;
  int led = 0;

  if ( isMotionDetected() ) {
    Serial.println("Motion Detected!!!");
    digitalWrite(D4, LOW);
    motionDetected = 1;
    led = 1;
  } 

  sound = getSound();
  if ( isSoundDetected() ) {
    Serial.println("Sound Detected");
    digitalWrite(D4, LOW);
    soundDetected = 1;
    led = 1;
  } 

  distance = getDistance();
  if ( isDistanceDetected(distance) ) {
    Serial.println("Someone is nearing");
    digitalWrite(D4, LOW);
    distanceDetected = 1;
    led = 1;
  } 

  if ( !led ) digitalWrite(D4, HIGH);

  postRequest(motionDetected, sound, soundDetected, distance, distanceDetected);

  //delay(250);

}
