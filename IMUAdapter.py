from pydispatch import dispatcher
from websockets.sync.server import serve
from threading import Thread
import logging
import sys
import enum
import os

WS_PORT = 18788
WS_IP = "127.0.0.1"

class IMUAdapter(Thread):
    def __init__(self, debugLevel=logging.DEBUG):
        Thread.__init__(self)

        self.ip = WS_IP
        self.port = WS_PORT

        ### Signals ###
        self.signalGotData = "imu1"
        self.signalGotStatus = "imu2"

        ### Logger setup ###
        self.log = logging.getLogger(__name__)
        self.log.setLevel(debugLevel)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.imuList = []
        self.connectionList = []

    def run(self):

        # Start the IMU app on local machine
        if self.ip == "localhost" or self.ip == "127.0.0.1":
            os.system("start cmd /k bridgeApps\IMUBLEBridge.exe "
                      + self.ip
                      + " "
                      + str(self.port))

        # Start WS server
        self.log.info("Starting WS Server on port %d", self.port)
        with serve(self.handlerWS, self.ip, self.port) as self.server:
            self.server.serve_forever()

    def handlerWS(self, ws):
        self.connectionList.append(ws)
        data = ''
        self.log.info("New WS connection: %s", ws.remote_address)
        while True:
            try:
                data = ws.recv()
                if data is None:
                    break
                self.log.debug("Data: %s", data)
                self.messageParser(data)
            except:
                break
        
        self.log.info("Connection closed")
        self.connectionList.remove(ws)
        # self.server.shutdown()

    def messageParser(self, msg):
        if "I=" in msg:
            dispatcher.send(self.signalGotData, self, type="IMU", id=msg[2:19], data=msg[19:])
        if "C=" in msg:
            dispatcher.send(self.signalGotStatus, self, type="IMU", id=msg[2:19], data="connected")
            # if self.imuList.index()
        if "D=" in msg:
            dispatcher.send(self.signalGotStatus, self, type="IMU", id=msg[2:19], data="disconnected")

    ### "SLOTS" ###
    def handlerCloseSignal(self):
        self.log.debug("Shutting down...")
        for ws in self.connectionList:
            ws.close()
        self.server.shutdown()