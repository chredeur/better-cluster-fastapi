from __future__ import annotations

import logging

from .pool import Session
from typing import Any, Dict, Optional,  Union


class Client:
    """|class|
    
    Handles the web application side requests to the bot process 
    (intented to work as asynchronous context manager)

    Parameters:
    ----------
    host: :str:`str`
        The IP adress that hosts the server (the default is `127.0.0.1`).
    secret_key: :str:`str`
        The authentication that is used when creating the server (the default is `None`).
    standard_port: :str:`int`
        The port for the standard server (the default is `1025`)
        
        Please keep in mind that multicast clients cannot request routes that are only allowed for standard connections!
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        secret_key: Union[str, None] = None,
        standard_port: int = 1025,
    ) -> None:
        self.host = host
        self.standard_port = standard_port
        self.secret_key = secret_key

        self.logger = logging.getLogger(__name__)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} standard_port={self.standard_port!r}>"

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.standard_port}"

    async def is_alive(self, bot_id: Union[str, int], identifier: Union[str, int]) -> bool:
        """|coro|

        Performs a test to the connetion state
        
        """
        async with Session(self.url, bot_id, identifier, self.secret_key) as session:
            return await session.is_alive()

    async def request(self, bot_id: Union[str, int], identifier: Union[str, int], endpoint: str, **kwargs: Any) -> Optional[Dict]:
        """|coro|
        
        Make a request to the server process.

        ----------
        endpoint: `str`
            The endpoint to request on the server
        **kwargs: `Any`
            The data for the endpoint
        """
        async with Session(self.url, bot_id, identifier, self.secret_key) as session:
            return await session.request(endpoint, **kwargs)

    async def request_all(self, bot_id: Union[str, int], endpoint: str, wait_response: Optional[bool]=True, **kwargs: Any) -> Optional[Dict]:
        """|coro|

        Make a request to the server process.

        ----------
        endpoint: `str`
            The endpoint to request on the server
        **kwargs: `Any`
            The data for the endpoint
        """
        async with Session(self.url, bot_id, 'all', self.secret_key) as session:
            return await session.request(endpoint, **kwargs)
