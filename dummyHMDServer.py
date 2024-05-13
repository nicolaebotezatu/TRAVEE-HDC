import asyncio
from websockets.server import serve

async def echo(websocket):
    print("Client ", websocket.remote_address, "connected")
    while True:
        try:
            async for message in websocket:
                print(message)
        except:
            break
    print("Client ", "disconnected")

async def main():
    async with serve(echo, "localhost", 22222):
        await asyncio.Future()  # run forever

asyncio.run(main())