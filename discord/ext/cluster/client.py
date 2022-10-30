from __future__ import annotations

import json
import logging
from types import TracebackType

from typing import Any, Dict, Optional, Union, Type, Tuple
from websockets.client import connect
from websockets import ConnectionClosed


class Client:
    """|class|
    
    Handles the web application side requests to the bot process 

    Parameters:
    ----------
    host: `str`
        The host of the cluster
    port: `int`
        The port of the cluster
    secret_key: `str`
        The authentication that is used when communicating with the cluster
    """

    __slots__: Tuple[str] = ("host", "port", "secret_key", "logger")

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

    @property
    def base_url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    async def __aenter__(self) -> Client:
        return await self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        return None

    async def request(self, endpoint: str, shard_id: Union[str, int], **kwargs: Any) -> Dict:
        """|coro|
        
        Make a request to the server process.

        ----------
        endpoint: `str`
            The endpoint to be requestes at the cluster
        shard_id: `str | int`
            Which shard should be handling the request
        **kwargs: `Any`
            The data for the endpoint
        """

        async with connect(
            self.base_url + "/create_request",
            extra_headers={
                "Secret-Key": str(self.secret_key),
                "Shard-ID": shard_id,
            }
        ) as ws:
            await ws.send(json.dumps({
                "endpoint": endpoint,
                "kwargs": {**kwargs}
            }))
            try:
                js_return = json.loads(await ws.recv())
                await ws.close()
                return js_return
            except ConnectionClosed:
                pass
            await ws.close()
            return None
