# step 0: **preparation**
set up the cloudformation(Preparation.yaml) stack in the us-east-1(or any region with IoT and Cloud9, should be fine although I haven't done the fully testing)

- CFN will take about 40 mins to build it(the majority of time is to build a cloudfront distruction so that your s3 isn’t public facing)
- provide a unique s3 bucket
- a unique cognito domain name - https://[a-unique-domain].auth.us-east-1.amazoncognito.com, eg the parameter is ‘iotworkshoprafaxu’ for me.
- if your default VPC in us-east-1 has any private subnet(it is very likely if you tested the NAT gateway function for Lambda), you need to specify the public subnet id in line 22



# step 1: **basic pub and sub**
~~~~
In this step we will create a device client to publish a status message to a topic then use a web UI to receive this status message
~~~~
## prepare the environment:
- Go to the Cloud9 service and open the IDE for IoTWorkshop-Door
- clone the repository to your cloud9
  ~~~~
  git clone https://github.com/aaaaatoz/iotworkshop
  cd iotworkshop
  git checkout step1
  cd ..
  Do the above steps in your laptop to get a local copy.
  ~~~~
- prepare the environment in C9 console:
  ~~~~
  sudo pip install AWSIoTPythonSDK
  ~~~~
## prepare the **authentication**
- download the certificate, private key by command: and download the CA certificate by command:
  ~~~~
   #aws iot create-keys-and-certificate --set-as-active --certificate-pem-outfile ./cert.pem --private-key-outfile ./key.pem --region us-east-1
   #wget https://www.amazontrust.com/repository/AmazonRootCA1.pem -O rootca.pem
  ~~~~
- find your endpoint:
  ~~~~
  from IoT console - eg a2a4ziueyywvoe-ats.iot.us-east-1.amazonaws.com or
  #aws iot describe-endpoint --endpoint-type iot:Data-ats --region us-east-1 > iot-endpoint.txt
  ~~~~
## prepare the **authorization**
  ~~~~
  attach the full IoT policy(IoTWorkshop-FullPolicy-Delete) to the certificate
  go to "aws iot console" and in secure -> certificate
  (https://console.aws.amazon.com/iot/home?region=us-east-1#/certificatehub),
  locate and locate your certificate
  click the certificate then actions -> attach the IoTWorkshop-FullPolicy-Delete
  ~~~~
- attendees need to understand the authentication and authorization
  ~~~~
  testing:
  authentication:
  openssl s_client -connect a2a4ziueyywvoe-ats.iot.us-east-1.amazonaws.com:8443 -CAfile rootca.pem -cert cert.pem -key key.pem -v

  in the console - https://console.aws.amazon.com/iot/home?region=us-east-1#/test
  subscribe to "my/topic" in the console to see if you can find the message

  curl --tlsv1.2 --cacert rootca.pem --cert cert.pem --key key.pem -X POST -d "{ \"message\": \"Hello, world\" }" "https://a2a4ziueyywvoe-ats.iot.us-east-1.amazonaws.com:8443/topics/my/topic"
  ~~~~

## prepare the basic publish device program
- copy the iot-pub into your directory
  ~~~~
  cp ./iotworkshop/iot-pub.py ./iot-main.py
  ~~~~
- make it executable
  ~~~~
  chmod a+x ./iot-main.py
  ~~~~
- make a status.txt file to simulate the door status(make sure you understand it)
  ~~~~
  echo 0 > status.txt
  ~~~~
- copy and change the config.json file to your endpoint
  ~~~~
  cp ./iotworkshop/config.json .
  ~~~~
- start the iot-main.py from terminal
  ~~~~
  ./iot-main.py
  ~~~~
- consistently change the status.txt content to simulate the door status change
  ~~~~
  while true;
  do
  sleep 5;
  echo 0 > status.txt;
  sleep 5;
  echo 1 > status.txt;
  done
  ~~~~
## prepare the web UI
- Create the static credentials for IoTWorkshop-dummyUser
  ~~~~
  In the AWS console(https://console.aws.amazon.com/iam/home?#/users/IoTWorkshop-dummyUser),
  locate the user - IoTWorkshop-dummyUser, Security credentials and generate the key/pass pair, note them down
  ~~~~
- replace your **local laptop's** iot-pub.html's key/pass and iot endpoint. Them launch it in the Chrome.
  ~~~~
  view the websocket communication in browser's dev tool -> network
  ~~~~

# step 2 **iot job**
~~~~
In this step we will create a iot-job agent to kill the iot-main.py, replace the iot-main content and restart it.
~~~~

- checkout the step2 branch
  ~~~~
  cd iotworkshop
  git checkout step2
  cd ..
  ~~~~
- create a thing via console(https://console.aws.amazon.com/iot/home?region=us-east-1#/thinghub) - called Door - keep all as default then choose "create thing without certificate"
- attach the certificate to the thing in the certificate console
- detach the full iot policy and attach the IoTWorkshop-job-policy policy
- copy the iot-job.py from the repository to the current directory
  ~~~~
  cp -rp ./iotworkshop/iot-job.py .
  chmod a+x ./iot-job.py
  read the iot job file to understand how it works
  ~~~~
- prepare the job artifacts:
  ~~~~
  aws s3 cp ./iotworkshop/iot-dummy.py s3://[yourbucket]
  change the [cloudfront] to your cloudfront in your ./iotworkshop/iot-dummy.json file
  ~~~~
- check if the iot-main.py file is updated
  ~~~~
  https://[cloudfront].cloudfront.net/iot-dummy.py
  ~~~~
- start the ./iot-job.py
- create a job:
  ~~~~
  aws iot create-job     --job-id $(uuidgen)     --targets "arn:aws:iot:us-east-1:[youraccountid]:thing/Door" --document file://iotworkshop/iot-dummy.json
  ~~~~

# step 3 **iot shadow - reported**
  ~~~~
  cd iotworkshop
  git checkout step3
  cd ..
  ~~~~
## update the iot-main.py by iot job agent
- copy the iot-shadow.py to s3
  ~~~~
  aws s3 cp ./iotworkshop/iot-shadow.py s3://[yourbucket]
  ~~~~
- update the iotworkshop/iot-shadow.json file to point to the correct source file.
- attach the certificate with the policy(IoTWorkshop-job-policy)
  ~~~~
  aws iot create-job  --job-id $(uuidgen)     --targets "arn:aws:iot:us-east-1:620428855768:thing/Door" --document file://iotworkshop/iot-shadow.json
  ~~~~
## update the ./iotworkshop/iot-shadow.html in [replaceme] field, the value is in output of cloudformation
 1. ClientId:
 2. AppWebDomain:
 3. RedirectUriSignIn and RedirectUriSignOut
 4. UserPoolId:
 5. IdentityPoolId:
 6. spend some time to understand the code.
- copy the js, css and html file to the s3
  ~~~~
$ aws s3 cp ./iotworkshop/amazon-cognito-auth.min.js  s3://[yourbucket]
$ aws s3 cp ./iotworkshop/bundle.js  s3://[yourbucket]                                    
$ aws s3 cp ./iotworkshop/styleSheetStart.css s3://[yourbucket]
$ aws s3 cp ./iotworkshop/iot-shadow.html s3://[yourbucket]
  ~~~~
## test:
 use chrome to open the   https://[cloudfront].cloudfront.net/iot-shadow.html

# step 4 **iot shadow - desired**
## set up the lambda code
~~~~
cd iotworkshop
git stash
git checkout step3
cd ..
~~~~
- update the lambda - IoTWorkshopSetStatus
- update the iot-control.html with the correct API GW endpoint (the endpoint is in CloudFormation output)
open the iot-control.html in the local laptop and change the door status - check the REST APIs/Lambda invocation
understand how it works.
## update the iot-main.py to receive the shadow delta
- update the iot-main function by iot-job agent
~~~~
aws s3 cp ./iotworkshop/iot-final.py s3://[yourbucket]
~~~~
- update the iot-final.json with correct url by replacing the cloudfront endpoint
- create the job content
~~~~
aws iot create-job     --job-id $(uuidgen)     --targets "arn:aws:iot:us-east-1:[youraccountid]:thing/Door" --document file://iotworkshop/iot-final.json
~~~~
check if you can control your device via iot-control.html page

# step 5: iot-rule
create a rule:
~~~~
SELECT topic(3) as thing, state.reported.status as status, timestamp FROM '$aws/things/+/shadow/update/accepted' where not isUndefined(state.reported)
integrated with lambda
replace the IoTWorkshopRule with
~~~~


direct rule:
~~~~
SELECT topic(3) AS ThingName, state.reported.status as status, timestamp() as Timestamp FROM '$aws/things/+/shadow/update/accepted' WHERE not isUndefined(state.reported)
action ddbv2 to dynamodb
SELECT topic(3) AS ThingName, state.reported.status as status, timestamp() as Timestamp FROM '$aws/things/+/shadow/update/accepted' WHERE (not isUndefined(state.reported)) and (state.reported.status='1') and ('09:00:00' ) < ( parse_time('HH:mm:ss', timestamp(), 'Australia/Sydney' ) ) and ('13:00:00' ) > ( parse_time('HH:mm:ss', timestamp(), 'Australia/Sydney' ) )
action to sns
~~~~
compare the difference between lambda and direct integrations
