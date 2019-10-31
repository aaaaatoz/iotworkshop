import boto3
client = boto3.client('iot-data')
import json

def handler(event,context):
    print(event)
    status = json.loads(event['body'])['status']
    if status == 0:
        payload = b'{"state":{"desired":{"status":"0"}}}'
    else:
        payload = b'{"state":{"desired":{"status":"1"}}}'

    client.update_thing_shadow(
        thingName='Door',
        payload= payload
    )

    response = {};
    response["headers"] = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
    }
    return response
