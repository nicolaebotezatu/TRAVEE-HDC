import asyncio
import functools
from bleak import BleakClient, BleakScanner
import bleak
import math
import struct
from ansitable import ANSITable, Column
from websockets.sync.client import connect
import websockets.sync.client as wssyc
import websockets
import argparse
from threading import Thread
from colored import Fore, Back, Style
import time
from queue import Queue

CLS = '\033[2J'
STAT_TABLE_WIDTH = 40
connected_devices = []
ws_handler = []

lra_play_uuid = "e533fe33-2658-47fd-b0e9-850ad9758850"

def printWSStat(status, color):
    print('\033[4;2H' + ' ' * STAT_TABLE_WIDTH)
    print(f'\033[4;2HWS Status: {color}{status}{Style.reset}')

def printConnectedDevices():
    print('\033[2;2H' + ' ' * STAT_TABLE_WIDTH)
    print('\033[2;2H' + 'Connected devices: ' + str(len(connected_devices)))

def printStatus(status):
    print('\033[3;2H' + ' ' * STAT_TABLE_WIDTH)
    print('\033[3;2H' + 'BLE Status: ' + status + ' ' * (25 - len(status)))

def printGeneral(status):
    print('\033[5;2H' + ' ' * STAT_TABLE_WIDTH)
    print('\033[5;2H' + status + ' ' * (37 - len(status)))    

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
    print(V_LINE + ' ' * STAT_TABLE_WIDTH + V_LINE)
    print(BL_CORNER + H_LINE * STAT_TABLE_WIDTH + BR_CORNER)

def disconnected_callback(client):
    #with lock:
    print(CLS)
    printStatTable()
    printConnectedDevices()
    printStatus("Device disconnected")
    asyncio.ensure_future(client.disconnect(),loop=asyncio.get_event_loop())
    if len(ws_handler) > 0:
        asyncio.ensure_future(ws_handler[-1].send("D=" + client.address),loop=asyncio.get_event_loop())
    connected_devices.remove(client)
    # dataQ.put("D=" + client.address)
    printConnectedDevices()
    # print("disconnect from", client.address)

async def scan_and_connect():
    print(CLS)
    printStatTable()
    while True:
        printConnectedDevices()
        printStatus("Scanning for devices...")
        # device = await BleakScanner.find_device_by_filter(match_device)
        device = await BleakScanner.find_device_by_name("VW1LRA")
        if device is None:
            # maybe asyncio.sleep() here for some seconds if you aren't in a hurry
            await asyncio.sleep(1)
            continue
        printStatus("Connecting to device")
        client = BleakClient(device, disconnected_callback=disconnected_callback)
        try:
            await client.connect()
            # print("connected to", device.address)
            if client.is_connected:
                connected_devices.append(client)
                if len(ws_handler) > 0:
                    await ws_handler[-1].send("C=" + client.address)
            # printStatus("Sending play commands")
            # await asyncio.sleep(1)
            # await client.start_notify(notify_uuid, functools.partial(callback, client))
            #with lock:
            # dataQ.put("C=" + device.address)
            # i = 0
            # while i < 10:
            #     i += 1
            #     await client.write_gatt_char(lra_play_uuid, b'\x01\x01\x0f', response=True)
            #     await asyncio.sleep(2)



        except bleak.BleakError:
            # if failed to connect, this is a no-op, if failed to start notifications, it will disconnect
            print("exception")
            await client.disconnect()
            # I'm not sure if manually disconnecting triggers disconnected_callback, (pretty easy to figure this out though)
            # if so, you will be getting disconnected_callback called twice
            # if not, you should call it here
            disconnected_callback(client)

async def write_to_gatt(client, characteristic_uuid, message):
    if client.is_connected:
        try:
            # if len(message) > 1:
            #     return
            msg = b'\x01\x01' + int(message).to_bytes(1, 'big')
            # print(msg)
            await client.write_gatt_char(characteristic_uuid, msg, response=True)
            printGeneral(str(msg) + " to GATT")
        except Exception as e:
            printGeneral("Failed to write to GATT")
    # else:
    #     print("Client is not connected")

async def websocket_handler(clients, ip, port):
    while True:
        try:
            printWSStat('connecting...', Fore.white)
            async with websockets.connect("ws://"+ip+":"+str(port)) as websocket:
                printWSStat('connected', Fore.green)
                ws_handler.append(websocket)
                while True:
                    try:
                        message = await websocket.recv()
                        # print(f"Received message: {message}")
                        for client in clients:
                            if client.is_connected:
                                await write_to_gatt(client, lra_play_uuid, message)
                    except websockets.ConnectionClosed:
                        printWSStat('disconnected', Fore.red)
                        break
                ws_handler.remove(websocket)
        except Exception as e:
            printWSStat('disconnected', Fore.red)
        await asyncio.sleep(5)  # Wait before attempting to reconnect

async def main():
    parser = argparse.ArgumentParser(description='Connect to a LRA DRV2605 device via BLE and play haptic patterns')
    parser.add_argument('ip', 
                        type=str,
                        help="WS Server IP address")
    parser.add_argument('port',
                        type=int,
                        help="WS Server port")
    args = parser.parse_args()
    print(CLS)
    printStatTable()

    # Run device connection management and WebSocket handler concurrently
    await asyncio.gather(
        scan_and_connect(),
        websocket_handler(connected_devices, args.ip, args.port)
    )

if __name__ == "__main__":
    asyncio.run(main())