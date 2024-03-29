from __future__ import annotations

import asyncio
import json
import uvicorn
import os

from uuid import uuid4
from typing import List, Dict, Any, Optional, Tuple, Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

secret_key = "my_secret_key"


class ShardsManager:
    def __init__(self):
        self.shards: Dict[str, Dict[str, Tuple[WebSocket, List]]] = {}
        self.waiters: Dict[str, WebSocket] = {}
        self.waiters_all_shards: Dict[str, Union[str, Dict]] = {}
        self.cache_shard_request_custom: Dict = {}

    async def initialize_shard(self, websocket: WebSocket, data: Dict):
        bot_id = websocket.headers["Bot-ID"]
        identifier = websocket.headers["Identifier"]
        data_response = data.get('response')
        if bot_id in self.shards and identifier in self.shards.get(bot_id):
            await websocket.send_text(json.dumps({"message": f"Shard with ID {identifier!r} already exists!", "code": 500}, separators=(", ", ": ")))
            await websocket.close()
            return 500
        if not os.path.isdir("db"):
            os.mkdir(f'db')
        if not data_response.get('endpoints'):
            with open(f"db/{bot_id}/{identifier}.json", 'r') as f:
                js = json.load(f)
                f.close()
            if bot_id not in self.shards:
                self.shards[bot_id] = {identifier: (websocket, js['endpoints'])}
            else:
                self.shards[bot_id][identifier] = (websocket, js['endpoints'])
        else:
            with open(f"db/{bot_id}/{identifier}.json", "w+") as e:
                dict_finaly = {"endpoints": data_response.get('endpoints')}
                json.dump(dict_finaly, e, sort_keys=True, indent=4)
                e.close()
            if bot_id not in self.shards:
                self.shards[bot_id] = {identifier: (websocket, data_response['endpoints'])}
            else:
                self.shards[bot_id][identifier] = (websocket, data_response['endpoints'])
        await websocket.send_text(json.dumps({"message": "Successfuly connected to the cluster!", "code": 200}, separators=(", ", ": ")))
        return 200

    async def disconnect_shard(self, websocket: WebSocket, data: Dict):
        bot_id = websocket.headers["Bot-ID"]
        identifier = websocket.headers["Identifier"]
        if bot_id in self.shards and identifier in self.shards[bot_id]:
            shard = self.shards[bot_id].get(identifier)
            if websocket == shard[0]:
                try:
                    os.remove(f"db/{bot_id}/{identifier}.json")
                except:
                    pass
                await shard[0].close()
                del self.shards[bot_id][identifier]
                return 200
            else:
                await websocket.close()
                return 500
        await websocket.close()
        return 500

    async def disconnect(self, websocket: WebSocket):
        bot_id = str(websocket.headers["Bot-ID"])
        identifier = str(websocket.headers["Identifier"])
        if bot_id in self.shards and identifier in self.shards[bot_id]:
            shard = self.shards[bot_id].get(identifier)
            if websocket == shard[0]:
                del self.shards[bot_id][identifier]
                if not self.shards[bot_id]:
                    del self.shards[bot_id]

    async def return_response(self, websocket: WebSocket, data: Dict):
        if data.get("uuid") in self.waiters_all_shards:
            get_waiter = self.waiters_all_shards.get(data.get("uuid"))
            if not get_waiter['wait_finish']:
                del self.waiters_all_shards[data.get("uuid")]
                return
            self.cache_shard_request_custom[get_waiter['id']][data.get("identifier")] = {"response": data.get("response")}
            del self.waiters_all_shards[data.get("uuid")]
            return
        await self.waiters[data.get("uuid")].send_text(json.dumps(data.get("response"), separators=(", ", ": ")))
        del self.waiters[data.get("uuid")]

    async def create_request(self, websocket: WebSocket, data: Dict):
        if not (identifier := websocket.headers["Identifier"]):
            await websocket.send_text(json.dumps({"message": "Missing shard ID!", "code": 500}, separators=(", ", ": ")))
            await websocket.close()
            return 500
        if not (bot_id := websocket.headers["Bot-ID"]):
            await websocket.send_text(json.dumps({"message": "Missing bot ID!", "code": 500}, separators=(", ", ": ")))
            await websocket.close()
            return 500
        if bot_id not in self.shards:
            await websocket.send_text(json.dumps({"message": f"Bot with ID {bot_id!r} doesn't exists!", "code": 404}, separators=(", ", ": ")))
            await websocket.close()
            return 404
        if identifier not in self.shards.get(bot_id):
            await websocket.send_text(json.dumps({"message": f"Shard with ID {identifier!r} doesn't exists!", "code": 404}, separators=(", ", ": ")))
            await websocket.close()
            return 404

        shard = self.shards.get(bot_id)[identifier]

        endpoint: Optional[str] = data["endpoint"]
        kwargs: Dict[str, Any] = data["kwargs"]

        if not endpoint in shard[1]:
            await websocket.send_text(json.dumps({"message": f"Unknown endpoint!", "404": 404}, separators=(", ", ": ")))
            await websocket.close()
            return 404
        else:
            ID = str(uuid4())
            await shard[0].send_text(json.dumps({"endpoint": endpoint, "data": kwargs, "uuid": ID, "identifier": identifier}, separators=(", ", ": ")))
            self.waiters[ID] = websocket
            return 200

    async def create_request_all_shard(self, websocket: WebSocket, data: Dict):
        if not (bot_id := str(websocket.headers["Bot-ID"])):
            await websocket.send_text(json.dumps({"message": "Missing bot ID!", "code": 500}, separators=(", ", ": ")))
            await websocket.close()
            return 500
        if bot_id not in self.shards:
            await websocket.send_text(json.dumps({"message": f"Bot with ID {bot_id!r} doesn't exists!", "code": 404}, separators=(", ", ": ")))
            await websocket.close()
            return 404

        ID_request = str(uuid4())
        endpoint: Optional[str] = data["endpoint"]
        wait_finish: Optional[bool] = data['wait_finish']
        kwargs: Dict[str, Any] = data["kwargs"]

        if endpoint not in self.shards.get(bot_id)[list(self.shards.get(bot_id).keys())[0]][1]:
            await websocket.send_text(json.dumps({"message": f"Unknown endpoint!", "code": 404}, separators=(", ", ": ")))
            await websocket.close()
            return 404

        self.cache_shard_request_custom[ID_request] = {}
        for identifier in self.shards[bot_id]:
            async def shard_task(id):
                try:
                    ID = str(uuid4())
                    await self.shards[bot_id][id][0].send_text(json.dumps({"endpoint": endpoint, "identifier": str(id), "data": kwargs, "uuid": ID}, separators=(", ", ": ")))
                    self.waiters_all_shards[ID] = {'id': ID_request, 'wait_finish': wait_finish}
                except:
                    if wait_finish:
                        self.cache_shard_request_custom[ID_request][id] = {}
            asyncio.create_task(shard_task(identifier))
        if wait_finish:
            while True:
                await asyncio.sleep(0.1)
                if len(self.cache_shard_request_custom[ID_request]) >= len(self.shards[bot_id]):
                    break

            await websocket.send_text(json.dumps({"message": "The requests have been made.", "data": self.cache_shard_request_custom[ID_request], "code": 200}, separators=(", ", ": ")))
            del self.cache_shard_request_custom[ID_request]
            return 200
        else:
            await websocket.send_text(json.dumps({"message": "The requests were sent.", "code": 200}, separators=(", ", ": ")))
            del self.cache_shard_request_custom[ID_request]
            return 200


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
    if not websocket.headers["Bot-ID"]:
        await websocket.send_text(json.dumps({"message": "Missing bot ID!", "code": 500}, separators=(", ", ": ")))
        return await websocket.close()
    if not websocket.headers["identifier"]:
        await websocket.send_text(json.dumps({"message": "Missing identifier!", "code": 500}, separators=(", ", ": ")))
        return await websocket.close()
    try:
        while True:
            data = await websocket.receive_json()
            if "Endpoints" not in websocket.headers and data.get("endpoint_choosen") in ["initialize_shard", "return_response", "disconnect_shard"]:
                if data.get("endpoint_choosen") == "initialize_shard":
                    result = await shards_manager.initialize_shard(websocket=websocket, data=data)
                    if result != 200:
                        break
                else:
                    if data.get("endpoint_choosen") == "disconnect_shard":
                        await shards_manager.disconnect_shard(websocket=websocket, data=data)
                        break
                    else:
                        await shards_manager.return_response(websocket=websocket, data=data)
            elif "Endpoints" in websocket.headers and websocket.headers["Endpoints"] == "create_request":
                if "connection_test" in data:
                    await websocket.send_text(json.dumps({"message": "Successful connection", "code": 200}, separators=(", ", ": ")))
                else:
                    if websocket.headers["identifier"] == "all":
                        result = await shards_manager.create_request_all_shard(websocket=websocket, data=data.get("response"))
                        if result == 200:
                            pass
                        else:
                            break
                    else:
                        result = await shards_manager.create_request(websocket=websocket, data=data.get("response"))
                        if result == 200:
                            pass
                        else:
                            break
            else:
                await websocket.send_text(json.dumps({"message": "Endpoint unknown", "code": 500}, separators=(", ", ": ")))
                return await websocket.close()
    except WebSocketDisconnect:
        await shards_manager.disconnect(websocket=websocket)


if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", host="0.0.0.0", port=9999, reload=False)
