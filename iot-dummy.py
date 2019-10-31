#!/usr/bin/python
from __future__ import print_function
import datetime
import time

def iot_shadow():
    while True:
        time.sleep(1)
        print("current time:" + str(datetime.datetime.now()))

if __name__ == "__main__":
    iot_shadow()