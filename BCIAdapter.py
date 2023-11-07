from pydispatch import dispatcher
from threading import Thread
import logging
import sys
import enum
import os
import socket
import json
import time
import select

TCP_IP = '0.0.0.0'
TCP_PORT = 37456

class BCIAdapter(Thread):
    def __init__(self, debugLevel=logging.DEBUG):
        Thread.__init__(self)

        self.ip = TCP_IP
        self.port = TCP_PORT
        self.kill = False
        self.buffer = b''

        ### Signals ###
        self.signalGotData = "bci1"
        self.signalGotStatus = "bci2"

        ### Logger setup ###
        self.log = logging.getLogger(__name__)
        self.log.setLevel(debugLevel)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.bind((self.ip, self.port))
        self.srv.listen(1)
        self.log.info("Socket created")

    def checkBuffer(self):
        oB = 0
        cB = 0
        cnt = 0
        if len(self.buffer) > 0:
            try:
                cBindex = self.buffer.index(b'}')
                try:
                    oBindex = self.buffer.index(b'{')
                except:
                    # the buffer starts with an incomplete message
                    self.buffer = b''
                    return None
                if oBindex > cBindex:
                    # incomplete msg at the front of the buffer
                    self.buffer = self.buffer[oBindex:]
                    return None
            except:
                pass

        for i in self.buffer:
            if bytes([i]) == b'{':
                oB+=1
            elif bytes([i]) == b'}':
                cB+=1
                if oB == cB and oB > 0:
                    # first occurence of } is before {
                    try:
                        if self.buffer.index(b'{') > self.buffer.index(b'}'):
                            # incomplete msg at the front of the buffer
                            self.buffer = b''
                            continue
                    except:
                        self.buffer = b''
                        continue
                    json_data = self.buffer[0:cnt+1]
                    self.buffer = self.buffer[cnt+1:]
                    return json_data
            cnt+=1
        return None

    def recvJSON(self):
        json_data = self.checkBuffer()
        if json_data is not None:
            return json_data
        
        while True:
            r,_,_ = select.select([self.conn], [], [], 0.7)
            if self.kill == True:
                self.conn.close()
                return None
            if r:
                data = self.conn.recv(8192)
                if not data:
                    self.log.info("Client disconnected (%d JSON objects received)", self.jsonCounter)
                    self.conn.close()
                    return None
                else:
                    self.buffer += data
                
            json_data = self.checkBuffer()
            if json_data is None:
                continue
            return json_data




    def run(self):

        while self.kill == False:
            # Wait for new client connection
            self.log.info("Waiting for client at "+self.ip+":"+str(self.port))
            self.conn, self.addr = self.srv.accept()
            self.log.info("Client %s connected", self.addr)
            dispatcher.send(self.signalGotStatus, self, type="BCI", id="1", data="connected")

            self.jsonCounter = 0
            while True:
                # get JSON byte array
                data = self.recvJSON()
                if data is None:
                    break
                try:
                    json_dict = json.loads(data.decode())
                except:
                    self.log.error("Not a JSON object")
                    continue
                self.log.debug("Received %s", json_dict)
                self.jsonCounter+=1
                self.messageParser(json_dict)

            dispatcher.send(self.signalGotStatus, self, type="BCI", id="1", data="disconnected")

        self.log.info("Closing...")
        

    def messageParser(self, msg):
        try:
            if msg['Name'] == 'BCI_VALUE':
                dispatcher.send(self.signalGotData, self, type="BCI", id="1", data=str(msg['Parameters'][0]['NumericValue']))
        except:
            pass
        # if "I=" in msg:
        #     dispatcher.send(self.signalGotData, self, type="IMU", id=msg[2:19], data=msg[19:])
        # if "C=" in msg:
        #     dispatcher.send(self.signalGotStatus, self, type="IMU", id=msg[2:19], data="connected")
        #     # if self.imuList.index()
        # if "D=" in msg:
        #     dispatcher.send(self.signalGotStatus, self, type="IMU", id=msg[2:19], data="disconnected")

    ### "SLOTS" ###
    def handlerCloseSignal(self):
        self.kill = True
        time.sleep(1)
        

if __name__ == "__main__":
    srv = BCIAdapter()
    srv.start()
    srv.join()    