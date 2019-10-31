#!/usr/bin/python
from __future__ import print_function
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTThingJobsClient
from AWSIoTPythonSDK.core.jobs.thingJobManager import jobExecutionTopicType
from AWSIoTPythonSDK.core.jobs.thingJobManager import jobExecutionTopicReplyType
from AWSIoTPythonSDK.core.jobs.thingJobManager import jobExecutionStatus

import threading
import logging
import datetime
import json
import requests
import os
import time
import subprocess, signal

logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.ERROR)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)


class JobsMessageProcessor(object):
    def __init__(self, awsIoTMQTTThingJobsClient, clientToken):
        #keep track of this to correlate request/responses
        self.clientToken = clientToken
        self.awsIoTMQTTThingJobsClient = awsIoTMQTTThingJobsClient
        self.done = False
        self.jobsStarted = 0
        self.jobsSucceeded = 0
        self.jobsRejected = 0
        self.jobsFailed = 0
        self._setupCallbacks(self.awsIoTMQTTThingJobsClient)


    def _setupCallbacks(self, awsIoTMQTTThingJobsClient):
        self.awsIoTMQTTThingJobsClient.createJobSubscription(self.newJobReceived, jobExecutionTopicType.JOB_NOTIFY_NEXT_TOPIC)
        self.awsIoTMQTTThingJobsClient.createJobSubscription(self.startNextJobSuccessfullyInProgress, jobExecutionTopicType.JOB_START_NEXT_TOPIC, jobExecutionTopicReplyType.JOB_ACCEPTED_REPLY_TYPE)
        self.awsIoTMQTTThingJobsClient.createJobSubscription(self.startNextRejected, jobExecutionTopicType.JOB_START_NEXT_TOPIC, jobExecutionTopicReplyType.JOB_REJECTED_REPLY_TYPE)

        # '+' indicates a wildcard for jobId in the following subscriptions
        self.awsIoTMQTTThingJobsClient.createJobSubscription(self.updateJobSuccessful, jobExecutionTopicType.JOB_UPDATE_TOPIC, jobExecutionTopicReplyType.JOB_ACCEPTED_REPLY_TYPE, '+')
        self.awsIoTMQTTThingJobsClient.createJobSubscription(self.updateJobRejected, jobExecutionTopicType.JOB_UPDATE_TOPIC, jobExecutionTopicReplyType.JOB_REJECTED_REPLY_TYPE, '+')

    #call back on successful job updates
    def startNextJobSuccessfullyInProgress(self, client, userdata, message):
        payload = json.loads(message.payload.decode('utf-8'))
        if 'execution' in payload:
            self.jobsStarted += 1
            execution = payload['execution']
            statusDetails = {'HandledBy': 'ClientToken: {}'.format(self.clientToken)}
            try:
                reboot = self.executeJob(execution)

                threading.Thread(target = self.awsIoTMQTTThingJobsClient.sendJobsUpdate, kwargs = {'jobId': execution['jobId'], 'status': jobExecutionStatus.JOB_EXECUTION_SUCCEEDED, 'statusDetails': statusDetails, 'expectedVersion': execution['versionNumber'], 'executionNumber': execution['executionNumber']}).start()
                if reboot:
                    self.reboot()

            except Exception:
                 threading.Thread(target = self.awsIoTMQTTThingJobsClient.sendJobsUpdate, kwargs = {'jobId': execution['jobId'], 'status': jobExecutionStatus.JOB_EXECUTION_FAILED, 'statusDetails': statusDetails, 'expectedVersion': execution['versionNumber'], 'executionNumber': execution['executionNumber']}).start()

        else:
            print('Start next saw no execution: ' + message.payload.decode('utf-8'))
            self.done = True


    def executeJob(self, execution):
        #################################
        ###
        ###The logic of the job tasks
        ###
        #################################
        print('Executing job ID, version, number: {}, {}, {}'.format(execution['jobId'], execution['versionNumber'], execution['executionNumber']))
        print('With jobDocument: ' + json.dumps(execution['jobDocument']))
        execute_job_detail = execution['jobDocument']
        operation = execute_job_detail['operation']
        file_url = execute_job_detail['newfile']

        reboot_required = False
        p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
        out, err = p.communicate()
        print(len(out.splitlines()))

        for line in out.splitlines():
            if 'iot-main.py' in line.decode("utf-8"):
                print(line)
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGKILL)

        # replace the file
        r = requests.get(file_url)
        with open("./iot-main.py", "wb") as code:
            code.write(r.content)

        time.sleep(5)
        log = open('./iot.log', 'w')
        subprocess.Popen(["./iot-main.py"], stdout=log, stderr=log, shell=True)
        print("finished the job starting...")
        return reboot_required

    def newJobReceived(self, client, userdata, message):
        payload = json.loads(message.payload.decode('utf-8'))
        if 'execution' in payload:
            self._attemptStartNextJob()
        else:
            print('Notify next saw no execution')
            self.done = True

    def reboot(self):
       os.system('sudo shutdown -r now')

    def processJobs(self):
        self.done = False
        print("set done to false")
        self._attemptStartNextJob()

    def startNextRejected(self, client, userdata, message):
        print('Start next rejected:' + message.payload.decode('utf-8'))
        self.jobsRejected += 1

    def updateJobSuccessful(self, client, userdata, message):
        self.jobsSucceeded += 1

    def updateJobRejected(self, client, userdata, message):
        self.jobsRejected += 1

    def _attemptStartNextJob(self):
        statusDetails = {'StartedBy': 'ClientToken: {} on {}'.format(self.clientToken, datetime.datetime.now().isoformat())}
        threading.Thread(target=self.awsIoTMQTTThingJobsClient.sendJobsStartNext, kwargs = {'statusDetails': statusDetails}).start()

    def isDone(self):
        return self.done

    def getStats(self):
        stats = {}
        stats['jobsStarted'] = self.jobsStarted
        stats['jobsSucceeded'] = self.jobsSucceeded
        stats['jobsRejected'] = self.jobsRejected
        return stats


f = open("config.json","r")
config_data = json.load(f)
host = config_data['endpoint']
root_ca = config_data['rootCA']
private_key = config_data['certificateKey']
private_cert = config_data['privateCert']
thing_name= config_data['thingName']


myAWSIoTMQTTClient = None
myAWSIoTMQTTClient = AWSIoTMQTTClient("random")
myAWSIoTMQTTClient.configureEndpoint(host, 8883)
myAWSIoTMQTTClient.configureCredentials(root_ca, private_key, private_cert)
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(10)  # 5 sec

jobsClient = AWSIoTMQTTThingJobsClient(thing_name, thing_name, QoS=1, awsIoTMQTTClient=myAWSIoTMQTTClient)

connected = False
while not connected:
     try:
          connected = myAWSIoTMQTTClient.connect()
     except Exception:
         print("waiting")
         time.sleep(10)

jobsMsgProc = JobsMessageProcessor(jobsClient, thing_name)
print('Starting to process jobs...')
jobsMsgProc.processJobs()


while True:
    time.sleep(10)

jobsClient.disconnect()
