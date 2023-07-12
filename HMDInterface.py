from pydispatch import dispatcher
from websockets.sync.client import connect
from threading import Thread
import logging
import sys
import enum

class ConnectionStatus(enum.Enum):
    DISCONNECTED = 0
    CONNECTED = 1

class HMDInterace:
    def __init__(self, port, debugLevel=logging.DEBUG):
        super().__init__()

        ### Connection setup ###
        self.port = port

        ### Functioning logic setup ###
        self.connStat = ConnectionStatus.DISCONNECTED
        self.recvThread = None

        ### Signals ###
        self.signalConnectionStatus = "hmdi1"

        ### Logger setup ###
        self.log = logging.getLogger(__name__)
        self.log.setLevel(debugLevel)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

    def run(self):
        while True:
            try:
                data = self.ws.recv()
                if data is None:
                    break
                self.log.debug("Data: %s", data)
            except:
                break
        self.log.info("HMD connection closed")
        dispatcher.send(self.signalConnectionStatus, self, status="disconnected")

    ### "SLOTS" ###
    def handlerSetIPAddress(self, ip):
        self.log.info(ip)
        if self.recvThread is not None:
            if self.recvThread.is_alive() == True:
                self.ws.close()
        try:
            self.ws = connect("ws://"+ip+":"+str(self.port))#,open_timeout=0.5)
            self.log.info("HMD connection opened!")
            self.connStat = ConnectionStatus.CONNECTED
            self.recvThread = Thread(target=self.run)
            self.recvThread.start()
            dispatcher.send(self.signalConnectionStatus, self, status="connected")
        except:
            self.log.info("HMD connection error")
            self.connStat = ConnectionStatus.DISCONNECTED
            dispatcher.send(self.signalConnectionStatus, self, status="error")
            pass

    def handlerSendData(self, type, id, data):
        self.log.debug("handlerSendData: %s %s %s", type, id, data)
        try:
            if self.connStat == ConnectionStatus.CONNECTED:
                self.ws.send(type+id+"("+data+")")
        except:
            # probably ConnectionClosed exception
            pass