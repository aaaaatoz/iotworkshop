#!/usr/bin/python
'''
/*
 * Copyright 2010-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *
 *  http://aws.amazon.com/apache2.0
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */
 '''
from __future__ import print_function

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import logging
import json
import time


# Shadow JSON schema:
#
# Name: Bot
# {
#	"state": {
#		"desired":{
#			"property":<INT VALUE>
#		}
#	}
# }

def myShadowUpdateCallback(payload, responseStatus, token):
    print("shadow updated " + payload)

def iot_shadow():

    f = open("config.json", "r")
    config_data = json.load(f)
    endpoint = config_data['endpoint']
    root_ca = config_data['rootCA']
    private_key = config_data['certificateKey']
    private_cert = config_data['privateCert']
    clientId = thing_name = config_data['thingName']
    port = config_data['port']

    # Configure logging
    logger = logging.getLogger("AWSIoTPythonSDK.core")
    logger.setLevel(logging.WARNING)
    streamHandler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)

    # Init AWSIoTMQTTShadowClient

    myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId)
    myAWSIoTMQTTShadowClient.configureEndpoint(endpoint, port)
    myAWSIoTMQTTShadowClient.configureCredentials(root_ca, private_key, private_cert)

    # AWSIoTMQTTShadowClient configuration
    myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec

    # Connect to AWS IoT
    myAWSIoTMQTTShadowClient.connect()

    # Create a deviceShadow with persistent subscription
    deviceShadowHandler = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(thing_name, True)

    i = 0
    status = None

    while True:
        newstatus = get_door_status()
        if i == 0 or newstatus != status:
            shadowMessage = '{"state":{"reported":{"status":"' + newstatus + '"}}}'
            deviceShadowHandler.shadowUpdate(shadowMessage, myShadowUpdateCallback, 5)
            status = newstatus
            i += 1;
        time.sleep(5)

def get_door_status(filename="./status.txt"):
    file = open(filename, "r")
    content = file.read(1)
    file.close()
    return content

if __name__ == "__main__":
    iot_shadow()