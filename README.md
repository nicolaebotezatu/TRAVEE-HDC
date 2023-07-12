# TRAVEE-HDC
```
usage: HDCGUIDemo.py [-h] -s SERVERPORT -d HMDPORT

optional arguments:
  -h, --help            show this help message and exit
  -s SERVERPORT, --ServerPort SERVERPORT
                        Port for the HDC WS Server to listen on
  -d HMDPORT, --HMDPort HMDPORT
                        Port on which the HMD WS Server is listening on
```
Sample usage:
![](/assets/SampleRun.PNG)
The *dummyHMDServer.py* is a basic WS server used for testing purposes instead of the HMD one. It accepts connections on port 22222.
