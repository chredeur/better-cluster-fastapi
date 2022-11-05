from __future__ import annotations

import json
import uvicorn
import os
import traceback

from uuid import uuid4
from typing import Callable, List, Dict, Any, Optional, Tuple, Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

secret_key = "my_secret_key"


class ShardsManager:
    def __init__(self):
        self.shards: Dict[str, Tuple[WebSocket, List, int]] = {}
        self.waiters: Dict[str, WebSocket] = {}

    async def initialize_shard(self, websocket: WebSocket, data):
        id = websocket.headers["Shard-ID"]
        print(self.shards)
        if self.shards.get(id):
            await websocket.send_text(json.dumps({"message": f"Shard with ID {id!r} already exists!", "code": 500}, separators=(", ", ": ")))
            await websocket.close()
            return 500
        else:
            if not os.path.isdir("db"):
                os.mkdir(f'db')
            if not data.get("response")['endpoints']:
                with open(f"db/{id}.json", 'r') as f:
                    js = json.load(f)
                    f.close()
                self.shards[id] = websocket, js['endpoints'], data.get("response")["client_id"]
            else:
                with open(f"db/{id}.json", "w+") as e:
                    dict_finaly = {"endpoints": data.get("response")['endpoints']}
                    json.dump(dict_finaly, e, sort_keys=True, indent=4)
                    e.close()
                self.shards[id] = websocket, data.get("response")['endpoints'], data.get("response")["client_id"]
            await websocket.send_text(json.dumps({"message": "Successfuly connected to the cluster!", "code": 200}, separators=(", ", ": ")))
            return 200

    async def disconnect(self, websocket: WebSocket):
        id = websocket.headers["Shard-ID"]
        print('disconnect')
        if (shard := self.shards.get(id)):
            if websocket == shard[0]:
                del self.shards[id]

    async def return_response(self, websocket: WebSocket, data: Dict):
        await self.waiters[data.get("uuid")].send_text(json.dumps(data.get("response"), separators=(", ", ": ")))
        await self.waiters[data.get("uuid")].close()
        del self.waiters[data.get("uuid")]

    async def create_request(self, websocket: WebSocket, data: Dict):
        if not (id := websocket.headers["Shard-ID"]):
            await websocket.send_text(json.dumps({"message": "Missing shard ID!", "code": 500}, separators=(", ", ": ")))
            await websocket.close()
            return 500

        if not (shard := self.shards.get(id)):
            await websocket.send_text(json.dumps({"message": f"Shard with ID {id!r} doesn't exists!", "code": 404}, separators=(", ", ": ")))
            await websocket.close()
            return 404

        endpoint: Optional[str] = data["endpoint"]
        kwargs: Dict[str, Any] = data["kwargs"]

        if not endpoint in shard[1]:
            await websocket.send_text(json.dumps({"message": f"Unknown endpoint!", "404": 404}, separators=(", ", ": ")))
            await websocket.close()
            return 404
        else:
            ID = str(uuid4())
            await shard[0].send_text(json.dumps({"endpoint": endpoint, "data": kwargs, "uuid": ID}, separators=(", ", ": ")))
            self.waiters[ID] = websocket


shards_manager = ShardsManager()


def is_secure(headers_secret_key: Union[str, int]) -> bool:
    if key := headers_secret_key:
        return str(key) == str(secret_key)
    return bool(headers_secret_key is None)


@app.websocket("/")
async def websocket_request_manager(websocket: WebSocket):
    await websocket.accept()
    if not is_secure(str(websocket.headers['Secret-Key'])):
        await websocket.send_text(json.dumps({"message": "Invalid secret key!", "code": 403}, separators=(", ", ": ")))
        return await websocket.close()
    if not websocket.headers["Shard-ID"]:
        await websocket.send_text(json.dumps({"message": "Missing shard ID!", "code": 500}, separators=(", ", ": ")))
        return await websocket.close()

    try:
        while True:
            data = await websocket.receive_json()
            if "Endpoints" not in websocket.headers and data.get("endpoint_choosen") in ["initialize_shard", "return_response"]:
                if data.get("endpoint_choosen") == "initialize_shard":
                    result = await shards_manager.initialize_shard(websocket=websocket, data=data)
                    if result != 200:
                        break
                else:
                    result = await shards_manager.initialize_shard(websocket=websocket, data=data)
                    if result != 200:
                        break
            elif "Endpoints" in websocket.headers and websocket.headers["Endpoints"] == "create_request":
                if "connection_test" in data:
                    await websocket.send_text(json.dumps({"message": "Successful connection", "code": 200}, separators=(", ", ": ")))
                else:
                    await shards_manager.create_request(websocket=websocket, data=data.get("response"))
            else:
                await websocket.send_text(json.dumps({"message": "Endpoint unknown", "code": 500}, separators=(", ", ": ")))
                return await websocket.close()
    except WebSocketDisconnect:
        await shards_manager.disconnect(websocket=websocket)


if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", host="0.0.0.0", port=9999, reload=True, workers=9)
