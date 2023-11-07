import asyncio
import functools
from bleak import BleakClient, BleakScanner
import bleak
import math
import struct
from ansitable import ANSITable, Column
from websockets.sync.client import connect
import websockets.sync.client as wssyc
import argparse
from threading import Thread
from colored import Fore, Back, Style
import time
from queue import Queue

CLS = '\033[2J'
STAT_TABLE_WIDTH = 40
connected_devices = []
notify_uuid = "ee7323e8-795d-41de-b29c-3fc9d970035f"
dataQ = Queue()
ws_status = "D"

def printWSStat(status, color):
    print('\033[4;2H' + ' ' * STAT_TABLE_WIDTH)
    print(f'\033[4;2HWS Status: {color}{status}{Style.reset}')

def printConnectedDevices():
    print('\033[2;2H' + ' ' * STAT_TABLE_WIDTH)
    print('\033[2;2H' + 'Connected devices: ' + str(len(connected_devices)))

def printStatus(status):
    print('\033[3;2H' + ' ' * STAT_TABLE_WIDTH)
    print('\033[3;2H' + 'BLE Status: ' + status + ' ' * (25 - len(status)))

def printStatTable():
    TL_CORNER = u'\u250C'
    TR_CORNER = u'\u2510'
    BL_CORNER = u'\u2514'
    BR_CORNER = u'\u2518'
    H_LINE = u'\u2500'
    V_LINE = u'\u2502'
    print('\033[1;1H' + TL_CORNER + H_LINE * STAT_TABLE_WIDTH + TR_CORNER)
    print(V_LINE + ' ' * STAT_TABLE_WIDTH + V_LINE)
    print(V_LINE + ' ' * STAT_TABLE_WIDTH + V_LINE)
    print(V_LINE + ' ' * STAT_TABLE_WIDTH + V_LINE)
    print(BL_CORNER + H_LINE * STAT_TABLE_WIDTH + BR_CORNER)

def euler_from_quaternion(x, y, z, w):
    """
    Convert a quaternion into euler angles (roll, pitch, yaw)
    """
    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + y * y)
    roll_x = math.atan2(t0, t1)
    
    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    pitch_y = math.asin(t2)
    
    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    yaw_z = math.atan2(t3, t4)
    
    return math.degrees(roll_x), math.degrees(pitch_y), math.degrees(yaw_z) # in radians

def callback(client, characteristic, data):
    # print(client.address, characteristic, data)
    # print(client.address)
    la_stat, la_x, la_y, la_z, rv_stat, rv_i, rv_j, rv_k, rv_real, rv_acu, stabc_stat, stabc_v = struct.unpack("<BhhhBhhhhhBB", data)
    rv_i = rv_i * (1.0 / (1 << 14))
    rv_j = rv_j * (1.0 / (1 << 14))
    rv_k = rv_k * (1.0 / (1 << 14))
    rv_real = rv_real * (1.0 / (1 << 14))
    rv_acu = rv_acu * (1.0 / (1 << 12))

    la_x = la_x * (1.0 / (1 << 8))
    la_y = la_y * (1.0 / (1 << 8))
    la_z = la_z * (1.0 / (1 << 8))

    rv_p, rv_r, rv_y = euler_from_quaternion(rv_i,rv_j,rv_k,rv_real)

    text = ''
    if stabc_v == 0:
        text = "Unknown"
    elif stabc_v == 1:
        text = "On table"
    elif stabc_v == 2:
        text = "Stationary"
    elif stabc_v == 3:
        text = "Stable"
    elif stabc_v == 4:
        text = "Motion"

    table = ANSITable(Column(" Calib ","{:2d}",colcolor="red"),
                      Column(" LA X ","{:+.2f}",colcolor="red"),
                      Column(" LA Y ","{:+.2f}",colcolor="red"),
                      Column(" LA Z ","{:+.2f}",colcolor="red"),
                      Column(" Calib ","{:2d}",colcolor="green"),
                      Column(" Pitch ","{:+.2f}",colcolor="green"),
                      Column(" Roll  ","{:+.2f}",colcolor="green"),
                      Column(" Yaw   ","{:+.2f}",colcolor="green"),
                      Column("Accuracy","{:+.2f}",colcolor="yellow"),
                      Column("Stability clasification"),
                      border="double",bordercolor="blue")
    table.row(la_stat,
              la_x,
              la_y,
              la_z,
              rv_stat,
              rv_p,
              rv_r,
              rv_y,
              rv_acu,
              text)
    # print(connected_devices)
    idx = connected_devices.index(client.address)
    print('\033['+str(6+6*idx)+';1H'+client.address)
    table.print()

    if ws_status == "C":
        to_send = "%2d %+.2f %+.2f %+.2f %2d %+.2f %+.2f %+.2f %+.2f %s" % (la_stat, la_x, la_y, la_z, rv_stat, rv_p, rv_r, rv_y, math.degrees(rv_acu), text)
        dataQ.put("I=" + client.address + " " + to_send)

def disconnected_callback(client):
    #with lock:
    print(CLS)
    printStatTable()
    printConnectedDevices()
    printStatus("Device disconnected")
    asyncio.ensure_future(client.disconnect(),loop=asyncio.get_event_loop())
    
    connected_devices.remove(client.address)
    dataQ.put("D=" + client.address)
    printConnectedDevices()
    # print("disconnect from", client.address)

async def scan_and_connect():
    print(CLS)
    printStatTable()
    while True:
        printConnectedDevices()
        printStatus("Scanning for devices...")
        # device = await BleakScanner.find_device_by_filter(match_device)
        device = await BleakScanner.find_device_by_name("BNO086 Integration")
        if device is None:
            # maybe asyncio.sleep() here for some seconds if you aren't in a hurry
            continue
        printStatus("Connecting to device")
        client = BleakClient(device, disconnected_callback=disconnected_callback)
        try:
            await client.connect()
            # print("connected to", device.address)
            connected_devices.append(device.address)
            printStatus("Activating notifications")
            await asyncio.sleep(1)
            await client.start_notify(notify_uuid, functools.partial(callback, client))
            #with lock:
            dataQ.put("C=" + device.address)

        except bleak.BleakError:
            # if failed to connect, this is a no-op, if failed to start notifications, it will disconnect
            print("exception")
            await client.disconnect()
            # I'm not sure if manually disconnecting triggers disconnected_callback, (pretty easy to figure this out though)
            # if so, you will be getting disconnected_callback called twice
            # if not, you should call it here
            disconnected_callback(client)



class WSClient(Thread):
    def __init__(self, ip, port):
        Thread.__init__(self)

        self.port = port
        self.ip = ip

    def run(self):
        global ws_status
        while True:
            try:
                ws_status = "D"
                printWSStat('connecting...', Fore.white)
                self.ws = connect("ws://"+self.ip+":"+str(self.port))
            except:
                printWSStat('disconnected', Fore.red)
                time.sleep(2)
                continue
            ws_status = "C"
            printWSStat('connected', Fore.green)
            while True:
                try:
                    data = dataQ.get()
                    # refresh intf status
                    if data[0] == "D":
                        printWSStat('connected', Fore.green)
                except:
                    continue
                try:
                    self.ws.send(data)
                except:
                    self.ws.close()
                    ws_status = "D"
                    printWSStat('disconnected', Fore.red)
                    time.sleep(2)
                    break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Connect to a BNO086 device via BLE and read data from it')
    parser.add_argument('ip', 
                        type=str,
                        help="WS Server IP address")
    parser.add_argument('port',
                        type=int,
                        help="WS Server port")
    
    args = parser.parse_args()
    print(CLS)
    printStatTable()
    wsc = WSClient(args.ip, args.port)
    wsc.start()
    # i=0
    # while True:
    #     try:
    #         time.sleep(1)
    #         dataQ.put('AAA'+str(i))
    #         i += 1
    #     except KeyboardInterrupt:
    #         break
    asyncio.run(scan_and_connect())