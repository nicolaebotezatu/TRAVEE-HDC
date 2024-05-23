from pydispatch import dispatcher
from websockets.sync.client import connect
import websockets.sync.client as wssyc
from threading import Thread
import threading
import logging
import sys
import enum
import ctypes

class ConnectionStatus(enum.Enum):
    RECONNECTING = 0
    CONNECTED = 1
    IDLE = 2

class HMDInterace:
    def __init__(self, port, debugLevel=logging.DEBUG):
        super().__init__()

        ### Connection setup ###
        self.port = port

        ### Functioning logic setup ###
        self.connStat = ConnectionStatus.IDLE
        self.recvThread = None

        ### Signals ###
        self.signalConnectionStatus = "hmdi1"
        self.signalStartVibration = "hmdi2"

        ### Logger setup ###
        self.log = logging.getLogger(__name__)
        self.log.setLevel(debugLevel)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.reconnectionTimer = None
        self.serverIP = None

    def connect(self):
        if self.serverIP is None:
            return
        if self.recvThread is not None:
            if self.recvThread.is_alive() == True:
                self.ws.close()
        try:
            self.ws = connect("ws://"+self.serverIP+":"+str(self.port))#,open_timeout=0.5)
            # print(type(self.ws))
            self.log.info("HMD connection opened!")
            self.connStat = ConnectionStatus.CONNECTED
            self.recvThread = Thread(target=self.run)
            self.recvThread.start()
            dispatcher.send(self.signalConnectionStatus, self, status="connected")
        except:
            self.log.info("HMD connection error, trying to reconnect in 2 seconds...")
            self.connStat = ConnectionStatus.RECONNECTING
            dispatcher.send(self.signalConnectionStatus, self, status="error")
            self.reconnectionTimer = threading.Timer(2, self.connect)
            self.reconnectionTimer.start()

    def run(self):
        while True:
            try:
                data = self.ws.recv()
                if data is None:
                    break
                self.log.debug("Data: %s", data)
                if data == "START_VIBRATION" or data == "START_VIBRATIONS":
                    dispatcher.send(self.signalStartVibration, self, pattern="15")
            except:
                break
            # Parse messages received from HMD
            
        self.log.info("HMD connection closed")
        if self.connStat != ConnectionStatus.IDLE:
            self.connStat = ConnectionStatus.RECONNECTING
            self.connect()
        dispatcher.send(self.signalConnectionStatus, self, status="disconnected")

    ### "SLOTS" ###
    def handlerSetIPAddress(self, ip):
        self.log.info(ip)
        self.serverIP = ip
        self.connect()

    def handlerSendData(self, type, id, data):
        self.log.debug("handlerSendData: %s %s %s", type, id, data)
        try:
            if self.connStat == ConnectionStatus.CONNECTED:
                # self.ws.send(type+id+"("+data+")")
                self.ws.send(type+" "+data)
        except:
            # probably ConnectionClosed exception
            pass

    def getThreadId(self):
        # returns id of the respective thread
        if hasattr(self.recvThread, '_thread_id'):
            return self.recvThread._thread_id
        for id, thread in threading._active.items():
            if thread is self.recvThread:
                return id

    def handlerCloseSignal(self):
        self.connStat = ConnectionStatus.IDLE
        self.log.info("Closing HMD connection")
        try:
            if isinstance(self.ws, wssyc.ClientConnection) == True:
                # print("self.ws.close()")
                self.ws.close()
            if isinstance(self.recvThread, Thread) == True:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(self.getThreadId(), ctypes.py_object(SystemExit))
                # print("PyThreadState_SetAsyncExc")
                self.recvThread.join()
                # print("self.recvThread.join()")
        except Exception as e:
            self.log.debug(e)
