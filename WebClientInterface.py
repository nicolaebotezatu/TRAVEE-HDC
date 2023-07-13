from pydispatch import dispatcher
from websockets.sync.server import serve
from threading import Thread
import logging
import sys
import enum

class SessionStatus(enum.Enum):
    IDLE = 0
    STARTED = 1
    VR_CONNECTED = 2

class ExerciseStatus(enum.Enum):
    IDLE = 0
    RUNNING = 1
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
        self.signalGotHMDIP = "wci1"
        self.signalExercise = "wci2"

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
                self.log.debug("Data: %s", data)
                self.messageParser(data)
            except:
                break
        
        self.log.info("Connection closed")
        self.connectionList.remove(ws)
        # self.server.shutdown()

    def messageParser(self, msg):
        if "START_SESSION" in msg:
            # if self.sesStat != SessionStatus.IDLE:
            #     self.log.info("Session already started!")
            #     return
            
            try:
                HMDIP = msg.split('(')[1][:-1]
            except:
                self.log.error("START_SESSION: unable to parse the IP address")
                return
            
            self.log.debug("Parsed START_SESSION message. HMD IP: %s", HMDIP)

            # if self.sesStat != SessionStatus.VR_CONNECTED:
            self.sesStat = SessionStatus.STARTED
            dispatcher.send(self.signalGotHMDIP, self, ip=HMDIP)
            
            
        elif "START_EXERCISE" in msg:
            if self.sesStat != SessionStatus.VR_CONNECTED:
                self.log.info("HMD not connected")
                return
            if self.exStat != ExerciseStatus.IDLE:
                self.log.info("Exercise already defined!")
                return
            try:
                params = msg.split('(')[1].split(',')
                exerciseId = params[0]
                targetLimb = params[1]
                deviceList = params[2][:-1]
            except:
                self.log.error("START_EXERCISE: unable to parse parameters")
                return
            
            self.log.debug("Parsed START_EXERCISE message: %s, %s, %s", exerciseId, targetLimb, deviceList)
            #TODO: parse parms & emit relevant signals
            #TODO: Add params to dispatched signal
            dispatcher.send(self.signalExercise, self, status="start")
            self.exStat = ExerciseStatus.RUNNING
        elif "PAUSE_EXERCISE" in msg:
            if self.sesStat != SessionStatus.VR_CONNECTED:
                self.log.info("HMD not connected")
                return
            self.log.debug("Parsed PAUSE_EXERCISE message")
            #TODO: function logic
            dispatcher.send(self.signalExercise, self, status="pause")
            self.exStat = ExerciseStatus.PAUSED
        elif "RESUME_EXERCISE" in msg:
            if self.sesStat != SessionStatus.VR_CONNECTED:
                self.log.info("HMD not connected")
                return
            self.log.debug("Parsed RESUME_EXERCISE message")
            #TODO: function logic
            dispatcher.send(self.signalExercise, self, status="resume")
            self.exStat = ExerciseStatus.RUNNING
        elif "STOP_EXERCISE" in msg:
            if self.sesStat != SessionStatus.VR_CONNECTED:
                self.log.info("HMD not connected")
                return
            self.log.debug("Parsed STOP_EXERCISE message")
            #TODO: function logic
            dispatcher.send(self.signalExercise, self, status="stop")
            self.exStat = ExerciseStatus.IDLE

    ### "SLOTS" ###

    # Handler for signals dispatched by the device wrappers (connection status, errorr?)
    def handlerDeviceData(self, type, id, data):
        #TODO: adapt to app needs
        #self.log.debug("handlerDeviceData: %s, %s, %s", type, str(id), data)
        for ws in self.connectionList:
            ws.send("HW_CONNECTION_STATUS("+str(type)+","+str(id)+","+str(data)+")")
        pass

    # Handler for signals dispatched by the HMD interface
    def handlerHMDInterface(self, status):
        if status == "connected":
            self.sesStat = SessionStatus.VR_CONNECTED
        elif status == "disconnected":
            self.sesStat = SessionStatus.IDLE

        for ws in self.connectionList:
            ws.send("VR_CONNECTION_STATUS("+str(status)+")")
        pass

    def handlerCloseSignal(self):
        self.log.debug("Shutting down...")
        for ws in self.connectionList:
            ws.close()
        self.server.shutdown()

if __name__ == "__main__":
    c = WebClientInterace(11111)
    c.start()