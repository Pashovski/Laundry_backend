import logging
import os
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware


from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from typing import Union
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

clients = {}

origins = [
    "http://192.168.1.230:8001/",
    "http://192.168.1.230:8002/",
    "http://localhost:8001/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=[""],
    allow_headers=[""],
)

def get_washer_state():
    token = os.getenv("INFLUXDB_TOKEN")
    org = "docker"
    bucket = "home_assistant"
    client = InfluxDBClient(url="http://influx.pash.home/", token=token)
    query = f'''
        from(bucket: "home_assistant")
        |> range(start: -24h)
        |> filter(fn: (r) => r["entity_id"] == "washer_state")
        |> filter(fn: (r) => r["_field"] == "state")
        |> last()
    '''
    tables = client.query_api().query(query, org="docker")
    logging.info(f'Query: {query}')
    logging.info(f'Result: {tables.to_json(indent=5)}')
    return tables.to_json(indent=5)

@app.get("/")
async def read_root():
    return 'Hello World'

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    try:
        await websocket.accept()
        clients[client_id] = websocket
        output = get_washer_state()
        print(output)  # Add this line for debugging
        while True:
            data = await websocket.receive_text()
            # Your logic for handling incoming messages
            logging.info(data)
            logging.info(clients)
            if data == "ping":
                await websocket.send_text("pong")
            else:
                await websocket.send_text(output)
    except WebSocketDisconnect:
        # Handle disconnection, remove the client from the dictionary, etc.
        print(f"WebSocket client {client_id} disconnected")
        del clients[client_id]
    except Exception as e:
        # Handle other exceptions that might occur during WebSocket communication
        print(f"WebSocket error: {e}")
    finally:
        # Clean up resources, if necessary
        print(f"WebSocket connection for client {client_id} closed")

@app.get("/send-status/{status}")
async def send_message(status:str):
    print(clients)
    if len(clients) > 0:
        for client_id in clients:
            await clients[client_id].send_text(status)
    else:
        return {"message": "WebSocket connection not established"}