#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import logging
import os
import time

from threading import Thread
from threading import Lock
mutex = Lock()

import paho.mqtt.publish as publish
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0'}

GISMETEO_URL = os.getenv('GISMETEO_URL', 'https://www.gismeteo.ru/weather-bryansk-4258/now/')
GISMETEO_INTERVAL = os.getenv('GISMETEO_INTERVAL', 10*60)
MQTT_SERVICE_HOST = os.getenv('MQTT_SERVICE_HOST', 'mosquitto.local')
MQTT_SERVICE_PORT = int(os.getenv('MQTT_SERVICE_PORT', 1883))
MQTT_SERVICE_TOPIC = os.getenv('MQTT_SERVICE_TOPIC', 'gismeteo')
MQTT_CLIENT_ID = os.getenv('HOSTNAME', 'gismeteo2mqtt')
MQTT_USER = os.getenv('MQTT_USER', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_INTERVAL = os.getenv('MQTT_INTERVAL', 5)

if MQTT_USER != '':
    MQTT_AUTH = {'username':MQTT_USER, 'password':MQTT_PASSWORD}
else :
    MQTT_AUTH = None

updated = False

temperature_now_global = ""
wind_speed_global = ""
wind_direction_global = ""
pressure_global = ""
humidity_global = ""
magnetic_global = ""
temperature_water_global = ""

def UpdateFromGismeteo():   
    global temperature_now_global
    global wind_speed_global
    global wind_direction_global
    global pressure_global
    global humidity_global
    global magnetic_global
    global temperature_water_global
    global updated
    while True:
        print ("Start update from Gismeteo")
    
        response = requests.get(GISMETEO_URL, headers=headers)
        contents = response.text
        soup = BeautifulSoup(contents, 'lxml')
                
        temperature_now = soup.find("span", attrs={ "class" : "js_value tab-weather__value_l"}).text.strip()             
        now_info_element = soup.find("div", attrs={ "class" : "now__info nowinfo"})

        wind_element = now_info_element.find("div", attrs={ "class" : "unit unit_wind_m_s"})
        wind_speed = wind_element.find("div", attrs={ "class" : "nowinfo__value"}).text.strip()
        wind_direction = wind_element.find("div", attrs={ "class" : "nowinfo__measure nowinfo__measure_wind"}).text.replace("м/с", "").strip()

        pressure = now_info_element.find("div", attrs={ "class" : "unit unit_pressure_mm_hg_atm"}).text.replace("мм рт. ст.", "").strip()

        humidity = now_info_element.find("div", attrs={ "class" : "nowinfo__item nowinfo__item_humidity"}).text.replace("Влажность", "").replace("%", "").strip()

        magnetic = now_info_element.find("div", attrs={ "class" : "nowinfo__item nowinfo__item_gm"}).find("div", attrs={ "class" : "nowinfo__value"}).text

        temperature_water_element = now_info_element.find("div", attrs={ "class" : "nowinfo__item nowinfo__item_water"})
        temperature_water = temperature_water_element.find("div", attrs={ "class" : "unit unit_temperature_c"}).text.replace("°C", "")  
        
        mutex.acquire()  
        temperature_now_global = temperature_now
        wind_speed_global = wind_speed
        wind_direction_global = wind_direction
        pressure_global = pressure
        humidity_global = humidity
        magnetic_global = magnetic
        temperature_water_global = temperature_water               
        mutex.release()
        
        updated = True
        
        print ("End update from Gismeteo")
        
        time.sleep(GISMETEO_INTERVAL)
        
        
            
            
def MqttPublish():  
    global temperature_now_global
    global wind_speed_global
    global wind_direction_global
    global pressure_global
    global humidity_global
    global magnetic_global
    global temperature_water_global
    global updated     
    while True:
        if updated:
            mutex.acquire()
            msgs = []
            msgs.append({'topic': MQTT_SERVICE_TOPIC + "/temperature_now", 'payload': temperature_now_global})
            msgs.append({'topic': MQTT_SERVICE_TOPIC + "/wind_speed", 'payload': wind_speed_global})
            msgs.append({'topic': MQTT_SERVICE_TOPIC + "/wind_direction", 'payload': wind_direction_global})
            msgs.append({'topic': MQTT_SERVICE_TOPIC + "/pressure", 'payload': pressure_global})
            msgs.append({'topic': MQTT_SERVICE_TOPIC + "/humidity", 'payload': humidity_global})
            msgs.append({'topic': MQTT_SERVICE_TOPIC + "/magnetic", 'payload': magnetic_global})
            msgs.append({'topic': MQTT_SERVICE_TOPIC + "/temperature_water", 'payload': temperature_water_global})
            publish.multiple(msgs, hostname=MQTT_SERVICE_HOST, port=MQTT_SERVICE_PORT, client_id=MQTT_CLIENT_ID, auth=MQTT_AUTH)            
        
            print("Температура воздуха: " + temperature_now_global + "°C")
            print("Скорость ветра: " + wind_speed_global + " м/с")
            print("Давление: " + pressure_global + " мм рт. ст.")
            print("Влажность: " + humidity_global + "%")
            print("Г/м активность: " + magnetic_global + " баллов")
            print("Температура воды: " + temperature_water_global + "°C")
            print("")
            mutex.release()                
        time.sleep(MQTT_INTERVAL)
        
if __name__ == "__main__":
    fromGismeteoUpdater = Thread(target=UpdateFromGismeteo)
    fromGismeteoUpdater.start()
    
    mqttPublish = Thread(target=MqttPublish)
    mqttPublish.start()
    
    fromGismeteoUpdater.join()
    mqttPublish.join()

    
