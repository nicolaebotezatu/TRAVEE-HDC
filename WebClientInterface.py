from pydispatch import dispatcher
from websockets.sync.server import serve
from threading import Thread
import logging
import sys
import enum

class SessionStatus(enum.Enum):
    IDLE = 0
    STARTED = 1

class ExerciseStatus(enum.Enum):
    IDLE = 0
    STARTED = 1
    PAUSED = 2

class WebClientInterace(Thread):
    def __init__(self, port, debugLevel=logging.DEBUG):
        Thread.__init__(self)

        ### Connection setup ###
        self.port = port

        ### Functioning logic setup ###
        self.sesStat = SessionStatus.IDLE
        self.exStat = ExerciseStatus.IDLE
        self.connectionList = []

        ### Signals ###
        self.signalGotHMDIP = "s1"

        ### Logger setup ###
        self.log = logging.getLogger(__name__)
        self.log.setLevel(debugLevel)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

    def run(self):
        self.log.info("Starting WS Server on port %d", self.port)
        with serve(self.handlerWS, 'localhost', self.port) as self.server:
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
                self.log.debug("%s", data)
                self.messageParser(data)
            except:
                break
        
        self.log.info("Connection closed")
        self.connectionList.remove(ws)
        # self.server.shutdown()

    def messageParser(self, msg):
        if "START_SESSION" in msg:
            if self.sesStat != SessionStatus.IDLE:
                self.log.info("Session already started!")
                return
            
            try:
                HMDIP = msg.split('(')[1][:-1]
            except:
                self.log.error("START_SESSION: unable to parse the IP address")
                return
            
            self.log.debug("Parsed START_SESSION message. HMD IP: %s", HMDIP)
            dispatcher.send(self.signalGotHMDIP, self, ip=HMDIP)
            self.sesStat = SessionStatus.STARTED
            self.log.info("Starting new session")
        elif "START_EXERCISE" in msg:
            if self.exStat != ExerciseStatus.IDLE:
                self.log.info("Exercise already defined!")
                return
            
            try:
                params = msg.split('(')[1].split(',')
                exerciseId = params[0]
                targetLimb = params[1]
                deviceList = params[2]
            except:
                self.log.error("START_EXERCISE: unable to parse parameters")
                return
            
            self.exStat = ExerciseStatus.STARTED
            self.log.debug("Parsed START_EXERCISE message: %s, %s, %s", exerciseId, targetLimb, deviceList)
            #TODO: parse parms & emit relevant signals
        elif "PAUSE_EXERCISE" in msg:
            self.log.debug("Parsed PAUSE_EXERCISE message")
            #TODO: function logic
            pass
        elif "RESUME_EXERCISE" in msg:
            self.log.debug("Parsed RESUME_EXERCISE message")
            #TODO: function logic
            pass
        elif "STOP_EXERCISE" in msg:
            self.log.debug("Parsed STOP_EXERCISE message")
            #TODO: function logic
            pass


    ### "SLOTS" ###

    # Handler for signals dispatched by the device wrappers (connection status, errorr?)
    def handlerDeviceData(self, type, device, data):
        #TODO: adapt to app needs
        for ws in self.connectionList:
            ws.send("HW_CONNECTION_STATUS("+str(device)+","+str(data)+")")
        pass

    # Handler for signals dispatched by the HMD interface
    def handlerHMDInterface(self, data):
        for ws in self.connectionList:
            ws.send("VR_CONNECTION_STATUS("+str(data)+")")
        pass

c = WebClientInterace(11111)
c.start()