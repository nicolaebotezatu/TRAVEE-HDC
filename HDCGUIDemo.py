import tkinter as tk
from tkinter import ttk
import WebClientInterface as wci
import HMDInterface as hmdi
import IMUAdapter as imua
import BCIAdapter as bcia
from pydispatch import dispatcher
from threading import Timer
import argparse
import time
from dataclasses import dataclass
import logging

@dataclass
class exerciseInfo:
    id:      int
    limb:    str
    devices: []
    status:  str


class HDCGUIDemo(tk.Tk):
    def __init__(self, wsServerPort=31010, wsHMDPort=22222):
        super().__init__()
        self.title("HDC dummy")
        ttk.Label(self, text='Demo value generator').pack()
        
        ### GUI elements ###
        fPeriod = ttk.Frame(self)
        fPeriod.pack()
        ttk.Label(fPeriod, text='Period (s)').pack(side=tk.LEFT)
        self.labelPeriod = ttk.Label(fPeriod, text='1')
        self.sliderPeriod = ttk.Scale(fPeriod, from_=1, to=10, orient=tk.HORIZONTAL, command=self.handlerPeriod)
        self.sliderPeriod.set(1)
        self.sliderPeriod.pack(side=tk.LEFT)
        
        self.labelPeriod.pack(side=tk.LEFT)

        fValue = ttk.Frame(self)
        fValue.pack()
        ttk.Label(fValue, text='Value').pack(side=tk.LEFT)
        self.sliderValue = ttk.Scale(fValue, from_=0.0, to=1.0, orient=tk.HORIZONTAL, command=self.handlerValue)
        self.sliderValue.pack(side=tk.LEFT)
        self.labelValue = ttk.Label(fValue, text='0')
        self.labelValue.pack(side=tk.LEFT)

        fDevs = ttk.Frame(self)
        fDevs.pack()
        self.varDevs = []

        self.varDevs.append(tk.IntVar())
        self.varDevs.append(tk.IntVar())
        self.varDevs.append(tk.IntVar())
        self.varDevs.append(tk.IntVar())
        self.oldValDevs = [0,0,0,0]
        ttk.Checkbutton(fDevs, text="Device 0", variable=self.varDevs[0], offvalue=0, onvalue=1, command=self.handlerCheckbox).pack(side=tk.LEFT)
        ttk.Checkbutton(fDevs, text="Device 1", variable=self.varDevs[1], offvalue=0, onvalue=1, command=self.handlerCheckbox).pack(side=tk.LEFT)
        ttk.Checkbutton(fDevs, text="Device 2", variable=self.varDevs[2], offvalue=0, onvalue=1, command=self.handlerCheckbox).pack(side=tk.LEFT)
        ttk.Checkbutton(fDevs, text="Device 3", variable=self.varDevs[3], offvalue=0, onvalue=1, command=self.handlerCheckbox).pack(side=tk.LEFT)
        
        ### Signals ###
        self.signalHwStatus = "gui1"
        self.signalHwData = "gui2"
        self.signalKill = "gui3"

        ### BE elements ###
        self.wci = wci.WebClientInterace(port=wsServerPort)
        self.wci.start()
        self.hmdi = hmdi.HMDInterace(port=wsHMDPort, debugLevel=logging.DEBUG)
        self.imua = imua.IMUAdapter(debugLevel=logging.INFO)
        self.imua.start()
        self.bcia = bcia.BCIAdapter(debugLevel=logging.DEBUG)
        self.bcia.start()
        

        # WS-Srv --> HMD IP --> WS-Cl
        # WebClientInterface receives the IP of the HMD and sends it to the HMDInterface
        dispatcher.connect(self.hmdi.handlerSetIPAddress, signal=self.wci.signalGotHMDIP, sender=self.wci)
        # WS-Cl --> Conn status --> WS-Srv
        # HMDInterface sends its connection status with the HMD to the WebClientInterface
        dispatcher.connect(self.wci.handlerHMDInterface, signal=self.hmdi.signalConnectionStatus, sender=self.hmdi)
        # WS-Cl --> Conn status --> GUI (start/stop timer)
        # HMDInterface sends its connection status with the HMD to the HDC main app
        dispatcher.connect(self.handlerHMDInterface, signal=self.hmdi.signalConnectionStatus, sender=self.hmdi)
        # Timer --> BCI_data --> WS-Cl
        # HDC main app sends dummy BCI data to the HMDInterface
        ###dispatcher.connect(self.hmdi.handlerSendData, signal=self.signalHwData, sender=self)
        # Chkbox --> Hw_stat --> WS_Srv
        # HDC main app sends dummy HW device status info to the WebClientInterface
        dispatcher.connect(self.wci.handlerDeviceData, signal=self.signalHwStatus, sender=self)
        
        # IMUAdapter sends IMU data to the HMDInterface
        ###dispatcher.connect(self.hmdi.handlerSendData, signal=self.imua.signalGotData, sender=self.imua)
        # IMUAdapter send HW status info to the WebClientInterface
        dispatcher.connect(self.wci.handlerDeviceData, signal=self.imua.signalGotStatus, sender=self.imua)

        #BCIAdapter sebds BCI data to the HMDInterface
        ###dispatcher.connect(self.hmdi.handlerSendData, signal=self.bcia.signalGotData, sender=self.bcia)
        # BCIAdapter send HW status info to the WebClientInterface
        dispatcher.connect(self.wci.handlerDeviceData, signal=self.bcia.signalGotStatus, sender=self.bcia)

        # HDC main app sends kill command to all interface components
        dispatcher.connect(self.wci.handlerCloseSignal, signal=self.signalKill, sender=self)
        dispatcher.connect(self.hmdi.handlerCloseSignal, signal=self.signalKill, sender=self)
        dispatcher.connect(self.imua.handlerCloseSignal, signal=self.signalKill, sender=self)
        dispatcher.connect(self.bcia.handlerCloseSignal, signal=self.signalKill, sender=self)

        # WebClientInterface sends exercise status info to the HDC main app
        dispatcher.connect(self.handlerExerciseEvent, signal=self.wci.signalExercise, sender=self.wci)

        self.timer = Timer(1, self.handlerTimer)
        self.timer = Timer(self.sliderPeriod.get(), self.handlerTimer)
        self.timer.start()

        ### Internal structures ###
        self.exerciseList = []
        self.deviceDataSignals = {
                                    "BCI": {
                                        "signal": self.bcia.signalGotData, #self.signalHwData,
                                        "sender": self.bcia #self
                                        },
                                    "IMU": {
                                        "signal": self.imua.signalGotData,
                                        "sender": self.imua
                                    }}

    def handlerTimer(self):
        #TODO: 
        try:
            value = self.sliderValue.get()
            dispatcher.send(self.signalHwData, self, type="BCI", id="", data="{:.2f}".format(value))

            self.timer = Timer(self.sliderPeriod.get(), self.handlerTimer)
            self.timer.start()
        except:
            pass

    def handlerPeriod(self, event):
        try:
            period = int(self.sliderPeriod.get())
            self.labelPeriod.config(text=str(period))

            if self.timer.is_alive() == True:
                self.timer.cancel()
                self.timer = Timer(self.sliderPeriod.get(), self.handlerTimer)
                self.timer.start()
        except:
            pass

    def handlerValue(self, event):
        value = self.sliderValue.get()
        self.labelValue.config(text="{:.2f}".format(value))

    def handlerCheckbox(self):
        if self.oldValDevs[0] != self.varDevs[0].get():
            dispatcher.send(self.signalHwStatus,self,type="Dev",id=1,data="connected" if self.varDevs[0].get() == 1 else "disconnected")
            # print("Dev 0: ", self.varDevs[0].get())
            self.oldValDevs[0] = self.varDevs[0].get()

        if self.oldValDevs[1] != self.varDevs[1].get():
            dispatcher.send(self.signalHwStatus,self,type="Dev",id=2,data="connected" if self.varDevs[1].get() == 1 else "disconnected")
            # print("Dev 1: ", self.varDevs[1].get())
            self.oldValDevs[1] = self.varDevs[1].get()

        if self.oldValDevs[2] != self.varDevs[2].get():
            dispatcher.send(self.signalHwStatus,self,type="Dev",id=3,data="connected" if self.varDevs[2].get() == 1 else "disconnected")
            # print("Dev 2: ", self.varDevs[2].get())
            self.oldValDevs[2] = self.varDevs[2].get()

        if self.oldValDevs[3] != self.varDevs[3].get():
            dispatcher.send(self.signalHwStatus,self,type="Dev",id=4,data="connected" if self.varDevs[3].get() == 1 else "disconnected")
            # print("Dev 3: ", self.varDevs[3].get())
            self.oldValDevs[3] = self.varDevs[3].get()
        pass

    def handlerHMDInterface(self, status):
        # print("handlerHMDInterface:", status)
        if status == "connected":
            # self.timer = Timer(self.sliderPeriod.get(), self.handlerTimer)
            # self.timer.start()
            pass
        elif status == "disconnected":
            # print("Cancelling timer")
            self.timer.cancel()
            # pass

    def handlerExerciseEvent(self, id, limb, devList, status):
        # print(id, limb, devList, status)
        if status == "start":
            ei = exerciseInfo(id, limb, devList, status)
            for i in self.exerciseList:
                if i.id == id and i.limb == limb:
                    self.exerciseList.remove(i)
            self.exerciseList.append(ei)
            for d in devList:
                try:
                    # print(self.deviceDataSignals[d])
                    dispatcher.connect(self.hmdi.handlerSendData, signal=self.deviceDataSignals[d]["signal"], sender=self.deviceDataSignals[d]["sender"])
                except KeyError:
                    # print("KeyError")
                    pass
        elif status == "resume":
            for i in self.exerciseList:
                if i.id == id:
                    for d in i.devices:
                        try:
                            dispatcher.connect(self.hmdi.handlerSendData, signal=self.deviceDataSignals[d]["signal"], sender=self.deviceDataSignals[d]["sender"])
                        except KeyError:
                            pass
        elif status == "pause":
            for i in self.exerciseList:
                if i.id == id:
                    for d in i.devices:
                        try:
                            dispatcher.disconnect(self.hmdi.handlerSendData, signal=self.deviceDataSignals[d]["signal"], sender=self.deviceDataSignals[d]["sender"])
                        except KeyError:
                            pass
        elif status == "stop":
            for i in self.exerciseList:
                if i.id == id:
                    for d in i.devices:
                        try:
                            dispatcher.disconnect(self.hmdi.handlerSendData, signal=self.deviceDataSignals[d]["signal"], sender=self.deviceDataSignals[d]["sender"])
                        except KeyError:
                            pass
                    self.exerciseList.remove(i)
        # if status == "start" or status == "resume":
        #     self.timer = Timer(self.sliderPeriod.get(), self.handlerTimer)
        #     self.timer.start()
        # elif status == "pause" or status == "stop":
        #     self.timer.cancel()

    def cleanUp(self):
        # print("Sending kill signal...")
        dispatcher.send(self.signalKill, self)
        self.wci.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--ServerPort", type=int, default=31010, help = "Port for the HDC WS Server to listen on")
    parser.add_argument("-d", "--HMDPort", type=int, default=22222, help = "Port on which the HMD WS Server is listening on")
    args = parser.parse_args()

    app = HDCGUIDemo()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("Keyboard Interrupt")
    app.timer.cancel()
    app.cleanUp()
    time.sleep(1)