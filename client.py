#!/usr/bin/env python3

# Modified from: https://github.com/blims/Tindeq-Progressor-API


txt = """
info@tindeq.com

Dear tindeq team, thanks for this excellent, useful, and flexbile device!
I've been using the Tindeq Progressor 200 for some months now and have one feedback/suggestion/feature request for the Tindeq app:
    
    


"""




import platform
import logging
import asyncio
import struct
import csv
import time
import datetime

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from bleak import BleakClient
from bleak import BleakScanner
from bleak import _logger as logger

TARGET_NAME = "Progressor"

""" Progressor Commands """
CMD_TARE_SCALE = 100
CMD_START_WEIGHT_MEAS = 101
CMD_STOP_WEIGHT_MEAS = 102
CMD_START_PEAK_RFD_MEAS = 103
CMD_START_PEAK_RFD_MEAS_SERIES = 104
CMD_ADD_CALIBRATION_POINT = 105
CMD_SAVE_CALIBRATION = 106
CMD_GET_APP_VERSION = 107
CMD_GET_ERROR_INFORMATION = 108
CMD_CLR_ERROR_INFORMATION = 109
CMD_ENTER_SLEEP = 110
CMD_GET_BATTERY_VOLTAGE = 111

""" Progressor response codes """
RES_CMD_RESPONSE = 0
RES_WEIGHT_MEAS = 1
RES_RFD_PEAK = 2
RES_RFD_PEAK_SERIES = 3
RES_LOW_PWR_WARNING = 4

progressor_uuids = {
    "7e4e1701-1ea6-40c9-9dcc-13d34ffead57": "Progressor Service",
    "7e4e1702-1ea6-40c9-9dcc-13d34ffead57": "Data",
    "7e4e1703-1ea6-40c9-9dcc-13d34ffead57": "Control point",
}

progressor_uuids = {v: k for k, v in progressor_uuids.items()}

PROGRESSOR_SERVICE_UUID = "{}".format(
    progressor_uuids.get("Progressor Service")
)
DATA_CHAR_UUID = "{}".format(
    progressor_uuids.get("Data")
)
CTRL_POINT_CHAR_UUID = "{}".format(
    progressor_uuids.get("Control point")
)

current_cmd_request = None

datad = []

def plot_measurments(datad):

    datad = np.array(datad)
    time = datad[:, 0]
    weight = datad[:, 1]
    
    half = int(len(weight)/2)
    vec = weight[half:]
    
    med = np.median(vec)
    mad = np.median(np.absolute(vec - np.median(vec)))
    
    plt.plot(time[:half+1], weight[:half+1], color="gray")
    plt.plot(time[half+0:], weight[half+0:], color="orange")
    plt.plot(time, 0*weight + med, color="red")
    
    plt.xlabel('Time [s]')
    plt.ylabel('Weight [kg]')
    plt.title(f'Measurement = {med:.2f} ± {mad:.2f} kg')
    plt.grid()
    plt.savefig('client.png')
    plt.show()   
    
    print("DONE")
    
    return None



def notification_handler(sender, data):
    """ Function for handling data from the Progressor """
    global current_cmd_request
    try:
        if data[0] == RES_WEIGHT_MEAS:
            value = [data[i:i+4] for i in range (2, len(data), 8)]
            timestamp = [data[i:i+4] for i in range (6, len(data), 8)]
            time = -1
            for x, y in zip(value, timestamp):
                weight, = struct.unpack('<f', x)
                useconds, = struct.unpack('<I', y)
                time = useconds / 1000000
                datad.append([time, weight])
            if time > 0:
                print(time)
                
        elif data[0] == RES_LOW_PWR_WARNING:
            print("Received low battery warning.")
        elif data[0] == RES_CMD_RESPONSE:
            if current_cmd_request == CMD_GET_APP_VERSION:
                print("---Device information---")
                print("FW version : {0}".format(data[2:].decode("utf-8")))
            elif current_cmd_request == CMD_GET_BATTERY_VOLTAGE:
                vdd, = struct.unpack('<I', data[2:]) 
                print("Battery voltage : {0} [mV]".format(vdd))
            elif current_cmd_request == CMD_GET_ERROR_INFORMATION:
                try:
                    print("Crashlog : {0}".format(data[2:].decode("utf-8")))
                    print("------------------------")
                except:
                    print("Empty crashlog")
                    print("------------------------")
    except Exception as e:
        print(e)


async def run(loop, debug=False):
    
    global current_cmd_request

    if debug:
        import sys

    scanner = BleakScanner()
    devices = await scanner.discover(timeout=2)
    address = None
    for d in devices:
        if (
          hasattr(d, 'name') and 
          (d.name is not None) and 
          (d.name[: len(TARGET_NAME)] == TARGET_NAME)
        ):
            address = d.address
            print('Found "{0}" with address {1}'.format(d.name, d.address))
            break

    async with BleakClient(address) as client:
        print("Device is connected.")

        await client.start_notify(DATA_CHAR_UUID, notification_handler)
        current_cmd_request = CMD_GET_APP_VERSION
        await client.write_gatt_char(CTRL_POINT_CHAR_UUID, bytearray([CMD_GET_APP_VERSION]), response=True)
        await asyncio.sleep(.5)
        current_cmd_request = CMD_GET_BATTERY_VOLTAGE
        await client.write_gatt_char(CTRL_POINT_CHAR_UUID, bytearray([CMD_GET_BATTERY_VOLTAGE]), response=True)
        await asyncio.sleep(.5)
        current_cmd_request = CMD_GET_ERROR_INFORMATION
        await client.write_gatt_char(CTRL_POINT_CHAR_UUID, bytearray([CMD_GET_ERROR_INFORMATION]), response=True)
        await asyncio.sleep(.5)
        await client.write_gatt_char(CTRL_POINT_CHAR_UUID, bytearray([CMD_START_WEIGHT_MEAS]), response=True)
        await asyncio.sleep(10)
        print("PLOTTING")
        # await client.write_gatt_char(CTRL_POINT_CHAR_UUID, bytearray([CMD_ENTER_SLEEP]))


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop, debug=False))
    plot_measurments(datad)
