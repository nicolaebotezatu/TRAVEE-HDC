import socket
import time
import json
import random

d = {'Name':"BCI_VALUE", 'Parameters':[{'Name':"Update",'NumericValue':1}]}

# Creaza un socket IPv4, TCP
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Conectare la serverul care asculta pe portul 5000
s.connect(('127.0.0.1', 37456))

s.send(b'}, "ABC":123}')

for i in range(1,50):
    # Trimite date
    d['Parameters'][0]['NumericValue']=random.random()
    s.send(bytes(json.dumps(d), 'ascii'))
    # Asteapta o secunda
    time.sleep(0.1)
# Inchide conexiune
time.sleep(1)
s.close()