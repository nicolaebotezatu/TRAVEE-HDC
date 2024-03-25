import socket
import time
import json
import random

d = {'Name':"BCI_VALUE", 'Parameters':[{'Name':"Update",'NumericValue':1}]}

# Creaza un socket IPv4, TCP
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Conectare la serverul care asculta pe portul 5000
s.connect(('127.0.0.1', 33333))

s.send(b'}, "ABC":123}')

for i in range(1,100):
    # Trimite date
    v = random.random()
    p = random.random()
    if p<0.1:
        for j in range(1,50):
            d['Parameters'][0]['NumericValue']=-1.1
            s.send(bytes(json.dumps(d), 'ascii'))
            # Asteapta o secunda
            time.sleep(0.05)
            print("-1.1")
    elif p>0.9:
        for j in range(1,50):
            d['Parameters'][0]['NumericValue']=1.1
            s.send(bytes(json.dumps(d), 'ascii'))
            # Asteapta o secunda
            time.sleep(0.05)
            print("1.1")
    else:
        d['Parameters'][0]['NumericValue']=v
        s.send(bytes(json.dumps(d), 'ascii'))
        # Asteapta o secunda
        time.sleep(0.05)
        print(v)
# Inchide conexiune
time.sleep(1)
s.close()