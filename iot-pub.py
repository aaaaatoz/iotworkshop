#!/usr/bin/python
from __future__ import print_function
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import time
import json
import datetime

def iot_pub():

    ## configuration files:

    f = open("config.json", "r")
    config_data = json.load(f)
    endpoint = config_data['endpoint']
    root_ca = config_data['rootCA']
    private_key = config_data['certificateKey']
    private_cert = config_data['privateCert']
    #clientId = thing_name = config_data['thingName']
    port = config_data['port']
    clientId = "whatever"

    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
    myAWSIoTMQTTClient.configureEndpoint(endpoint, port)
    myAWSIoTMQTTClient.configureCredentials(root_ca, private_key, private_cert)

    myAWSIoTMQTTClient.connect()
    topic = "/status/" + clientId
    message = {}
    status = ""
    i = 0

    while True:
        newstatus = get_door_status()
        if i  == 0 or newstatus != status:
            message['message'] = newstatus
            message['timestamp'] = str(datetime.datetime.now())
            messageJson = json.dumps(message)
            myAWSIoTMQTTClient.publish(topic, messageJson, 1)
            print("Status published to /status/" + clientId + " topic - status: " + newstatus)
            status = newstatus
            i += 1;
        time.sleep(1)

def get_door_status(filename="./status.txt"):
    file = open(filename, "r")
    content = file.read(1)
    file.close()
    return content

if __name__ == "__main__":
    iot_pub()
