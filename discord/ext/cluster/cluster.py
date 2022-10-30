from __future__ import annotations

import asyncio
import contextlib
import logging
import json

from uuid import UUID, uuid4
from typing import Callable, List, Dict, Any, Optional, Tuple, Union
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from websockets.server import serve, WebSocketServerProtocol


class Cluster:
    """|class|
    
    The inter-process communication cluster. 
    Used to handle communication between shards and clients

    Parameters:
    ----------
    host: `str`
        The host for the cluster
    port: `int`
        The port for the cluster
    secret_key: `str`
        Used for authentication when handling requests.
    """

    __slots__: Tuple[str] = ("host", "port", "secret_key", "logger", "shards", "waiters", "handlers")

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 20000,
        secret_key: str = None
    ) -> None:
        self.host = host
        self.port = port
        self.secret_key = secret_key
        self.logger = logging.getLogger("discord.ext.cluster")
        
        self.shards: Dict[str, Tuple[WebSocketServerProtocol, List, int]] = {}
        self.waiters: Dict[UUID, WebSocketServerProtocol] = {}
        self.handlers: Dict[str, Callable] = {
            "/initialize_shard": self.initialize_shard,
            "/disconnect_shard": self.disconnect_shard,
            "/create_request": self.create_request,
            "/return_response": self.return_response
        }

    def is_secure(self, websocket: WebSocketServerProtocol) -> bool:
        if (key := websocket.request_headers.get("Secret-Key")):
            return str(key) == str(self.secret_key)
        return bool(self.secret_key is None)

    async def initialize_shard(self, websocket: WebSocketServerProtocol, message: Union[str, bytes]) -> None:
        if not self.is_secure(websocket):
            return await websocket.send(
                json.dumps({
                    "error": "Invalid secret key!",
                    "code": 403
                }, separators=(", ", ": "))
            )

        if not (id := websocket.request_headers.get("Shard-ID")):
            return await websocket.send(
                json.dumps({
                    "error": "Missing shard ID!",
                    "code": 500
                }, separators=(", ", ": "))
            )
        
        if (data := self.shards.get(id)):
            try:
                await (await data[0].ping())
            except ConnectionClosed:
                del self.shards[id]
                self.logger.warning(f"Shard {id!r} (ID: {data[2]}) has been replaced by {websocket.id}. The reason is PING timeout")
            
                data: Dict[str, Any] = json.loads(message)

                self.shards[id] = websocket, data.get("endpoints"), data.get("client_id")
                return await websocket.send(
                    json.dumps({
                        "message": "Successfuly connected to the cluster!",
                        "code": 200
                    }, separators=(", ", ": "))
                )
            else:
                return await websocket.send(
                    json.dumps({
                        "error": f"Shard with ID {id!r} already exists!",
                        "code": 500
                    }, separators=(", ", ": "))
                )
        
        else:
            data: Dict[str, Any] = json.loads(message)
            
            self.shards[id] = websocket, data.get("endpoints"), data.get("client_id")
            
            await websocket.send(
                json.dumps({
                    "message": "Successfuly connected to the cluster!",
                    "code": 200
                }, separators=(", ", ": "))
            )

            self.logger.info(f"Shard {id!r} has been connected!")

    async def disconnect_shard(self, websocket: WebSocketServerProtocol, message: Union[str, bytes]) -> None:
        if not self.is_secure(websocket):
            return await websocket.send(
                json.dumps({
                    "error": "Invalid secret key!",
                    "code": 403
                }, separators=(", ", ": "))
            )

        if not (id := websocket.request_headers.get("Shard-ID")):
            return await websocket.send(
                json.dumps({
                    "error": "Missing shard ID!",
                    "code": 500
                }, separators=(", ", ": "))
            )

        if not self.shards.get(id):
            return await websocket.send(
                json.dumps({
                    "error": f"Shard with ID {id!r} doesn't exists!",
                    "code": 404
                }, separators=(", ", ": "))
            )
        
        else:
            ws = self.shards.pop(id)[0]

            await ws.send(
                json.dumps({
                    "message": "Successfuly disconnected from the cluster!",
                    "code": 200
                }
            ), separators=(", ", ": "))
            
        self.logger.warning(f"Shard {id!r} has been disconnected manually")

    async def create_request(self, websocket: WebSocketServerProtocol, message: Union[str, bytes]) -> None:
        if not self.is_secure(websocket):
            return await websocket.send(
                json.dumps({
                    "error": "Invalid secret key!",
                    "code": 401
                }, separators=(", ", ": "))
            )

        if not (id := websocket.request_headers.get("Shard-ID")):
            return await websocket.send(
                json.dumps({
                    "error": "Missing shard ID!",
                    "code": 500
                }, separators=(", ", ": "))
            )

        if not (shard := self.shards.get(id)):
            return await websocket.send(
                json.dumps({
                    "error": f"Shard with ID {id!r} doesn't exists!",
                    "code": 404
                }, separators=(", ", ": "))
            )
        
        data: Dict[str, Any] = json.loads(message)
        endpoint: Optional[str] = data.get("endpoint")
        kwargs: Dict[str, Any] = data.get("kwargs")

        if not endpoint in shard[1]:
            return await websocket.send(
                json.dumps({
                    "error": "Unknown endpoint!",
                    "code": 404
                }, separators=(", ", ": "))
            )

        else:
            ID = str(uuid4())

            await shard[0].send(json.dumps({
                "endpoint": endpoint,
                "data": kwargs,
                "uuid": ID
            }, separators=(", ", ": ")))

            self.waiters[ID] = websocket

    async def return_response(self, websocket: WebSocketServerProtocol, message: Union[str, bytes]) -> None:
        if not self.is_secure(websocket):
            return await websocket.send(
                json.dumps({
                    "error": "Invalid secret key!",
                    "code": 401
                }, separators=(", ", ": "))
            )
    
        if not (id := websocket.request_headers.get("UUID", None)):
            return await websocket.send(
                json.dumps({
                    "error": "Missing UUID!",
                    "code": 500
                }, separators=(", ", ": "))
            )

        else:
            await self.waiters[id].send(message)

    async def handle_requests(self, websocket: WebSocketServerProtocol) -> None:
        with contextlib.suppress(ConnectionClosedError):
            async for message in websocket:
                if not (handler := self.handlers.get(websocket.path)):
                    await websocket.send(
                        json.dumps({
                            "error": "Unknown path",
                            "code": 404
                        }, separators=(", ", ": "))
                    )
                await handler(websocket, message)

    async def start(self) -> None:
        """|coro
            
        Starts a servewr that handles connection between shards and clients.

        """
        async with serve(self.handle_requests, self.host, self.port):
            await asyncio.Future() # run forever
