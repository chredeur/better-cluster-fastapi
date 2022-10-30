from __future__ import annotations

import asyncio
import json
import logging

from websockets.client import connect
from discord.ext.commands import Bot, Cog, AutoShardedBot
from discord.ext.cluster.errors import NotConnected
from discord.ext.cluster.objects import ClientPayload
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import InvalidHandshake, ConnectionClosed
from typing import TYPE_CHECKING, Any, Tuple, Optional, Callable, TypeVar, Dict, Union, Type, List

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, TypeAlias
    
    P = ParamSpec('P')
    T = TypeVar('T')
    
    RouteFunc: TypeAlias = Callable[P, T]


class Shard:
    """|class|
    
    The inter-process communication server. Usually used on the bot process for receiving
    requests from the client.

    Parameters:
    ----------
    bot: `discord.ext.commands.Bot`
        Your bot instance
    shard_id: `str | int`
        This is how the bot will be identified in the cluster
    host: `str`
        The host of the cluster
    port: `int`
        The port of the cluster
    secret_key: `str`
        Used for authentication when handling requests.
    endpoints_list: `list`
        The list of all endpoints.
    """

    __slots__: Tuple[str] = (
        "bot", 
        "shard_id", 
        "endpoints_list", 
        "host", 
        "port", 
        "secret_key", 
        "logger", 
        "websocket", 
        "task"
    )

    endpoints: Dict[int, Dict[str, Tuple[Union[int, str], RouteFunc]]] = {}

    def __init__(
        self,
        bot: Union[Bot, AutoShardedBot],
        shard_id: Union[str, int],
        endpoints_list: List[Tuple[str, RouteFunc]],
        host: str = "127.0.0.1",
        port: int = 20000,
        secret_key: str = None,
    ) -> None:
        self.bot = bot
        self.shard_id = shard_id
        self.endpoints_list = endpoints_list
        self.host = host
        self.port = port
        self.secret_key = secret_key
        self.logger = logging.getLogger("discord.ext.cluster")
        self.websocket: WebSocketServerProtocol = None
        self.task: asyncio.Task = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} connected={self.connected}>"

    def __find_cls__(self, func: str) -> Union[Bot, Cog]:
        for cog in self.bot.cogs.values():
            if func in dir(cog):
                return cog
        return self.bot

    @property
    def connected(self) -> bool:
        return self.websocket is not None

    @property
    def base_url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    async def handle_request(self, request: Dict) -> None:
        self.logger.debug(f"Received request: {request!r}")

        endpoint: str = request.get("endpoint")

        shard_id, func = self.endpoints[self.bot.user.id].get(endpoint)
        cls = self.__find_cls__(endpoint)
        
        arguments = (cls, ClientPayload(request))

        try:
            response: Optional[Union[Dict, Any]] = await func(*arguments)
        except Exception as exception:
            self.bot.dispatch("shard_error", endpoint, exception)
            self.logger.error(f"Received error while executing {endpoint!r}", exc_info=exception)
            response = {
                "error": "Something went wrong while calling the route!",
                "code": 500,
            }

        response = response or {}
        if not isinstance(response, Dict):
            response = {
                "error": f"Expected type `Dict` as response, got {response.__class__.__name__!r} instead!", 
                "code": 500
            }
        
        if not response.get("code"):
            response["code"] = 200
        
        async with connect(
            self.base_url + "/return_response",
            extra_headers={
                "Secret-Key": str(self.secret_key),
                "UUID": request["uuid"]
            }
        ) as ws:
            await ws.send(json.dumps(response, separators=(", ", ": ")))
            self.logger.debug(f"Sending response: {response!r}")

    async def wait_for_requests(self) -> None:
        while True:
            try:
                raw = await self.websocket.recv()
            except ConnectionClosed:
                break
            else:
                data: Dict = json.loads(raw)
                asyncio.create_task(self.handle_request(data))

    async def connect(self) -> None:
        """|coro|
        
        Connects to the cluster with given shard id and registers all endpoints that belong to the mentioned shard id
        
        """
        try:
            self.websocket = await connect(
                self.base_url + "/initialize_shard", 
                extra_headers={
                    "Secret-Key": str(self.secret_key),
                    "Shard-ID": self.shard_id,
                }
            )
        except (ConnectionRefusedError, InvalidHandshake):
            return self.logger.critical("Failed to connect to the cluster!")
        else:
            if self.bot.user.id in self.endpoints:
                del self.endpoints[self.bot.user.id]
            self.endpoints[self.bot.user.id] = {}
            for x in self.endpoints_list:
                self.endpoints[self.bot.user.id][f"{x[0]}"] = (self.shard_id, x[1])
            await self.websocket.send(
                json.dumps({
                    "endpoints": [x[0] for x in self.endpoints[self.bot.user.id].items()],
                    "client_id": self.bot.user.id
                })
            )
            message: Dict[str, Any] = json.loads(await self.websocket.recv())
            if message["code"] == 200:
                self.task = asyncio.Task(self.wait_for_requests())
                self.logger.info("Successfully connected to the cluster!")
                if self.bot.is_ready():
                    self.bot.dispatch("shard_ready")
                else:
                    asyncio.create_task(self.wait_bot_is_ready())
            del self.endpoints_list

    async def disconnect(self) -> None:
        """|coro|

        The only proper way to disconnect an already connected shard from the cluster

        """

        if self.websocket:
            async with connect(
                self.base_url + "/disconnect_shard",
                extra_headers={
                    "Secret-Key": str(self.secret_key).encode("UTF-8"),
                    "Shard-ID": self.shard_id
                }
            ):
                pass
            await self.websocket.close()
        else:
            raise NotConnected

    async def wait_bot_is_ready(self) -> None:
        await self.bot.wait_until_ready()
        self.bot.dispatch("shard_ready")
