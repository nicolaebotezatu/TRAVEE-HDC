import asyncio
from websockets.server import serve
import websockets

clients = []

async def echo(websocket):
    print("Client ", websocket.remote_address, "connected")
    clients.append(websocket)
    while True:
        try:
            message = await websocket.recv()
            print(message)
        except websockets.ConnectionClosedOK:
            break
    print("Client ", "disconnected")
    clients.remove(websocket)

async def srv():
    async with serve(echo, "localhost", 22222):
        await asyncio.Future()  # run forever

async def websocket_handler():
    while True:
        await asyncio.sleep(3)
        for c in clients:
            await c.send("START_VIBRATION")


async def main():
    # Run device connection management and WebSocket handler concurrently
    await asyncio.gather(
        srv(),
        websocket_handler()
    )

asyncio.run(main())