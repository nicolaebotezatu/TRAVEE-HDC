from pydispatch import dispatcher
from websockets.sync.server import serve
from threading import Thread
import logging
import sys

class WebClientInterace(Thread):
    def __init__(self, port, debugLevel=logging.DEBUG):
        Thread.__init__(self)
        self.port = port
        self.log = logging.getLogger(__name__)
        self.log.setLevel(debugLevel)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

    def run(self):
        self.log.info("Starting WS Server on port %d", self.port)
        with serve(self.handler, 'localhost', self.port) as self.server:
            self.server.serve_forever()

    def handler(self, ws):
        data = ''
        self.log.info("New WS connection: %s", ws.remote_address)
        while True:
            try:
                data = ws.recv()
                if data is None:
                    break
                self.log.info("%s", data)
                self.messageParser(data)
            except:
                break
        
        self.log.info("Connection closed")
        # self.server.shutdown()

    def messageParser(self, msg):
        pass

c = WebClientInterace(11111)
c.start()