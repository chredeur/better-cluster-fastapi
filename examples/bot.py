import asyncio
import discord
import logging

from discord.ext import commands
from typing import Optional

from discord.ext.cluster import Shard, ClientPayload
from discord.ext.cluster.errors import ClusterBaseError

logging.basicConfig(level=logging.INFO)

logging.getLogger("discord.http").disabled = True
logging.getLogger("discord.client").disabled = True
logging.getLogger("discord.gateway").disabled = True

endpoints_list = []

class MyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.all()

        super().__init__(
            command_prefix="$.",
            intents=intents
        )

        self.shard = Shard(self, shard_id=1, endpoints_list=endpoints_list)

    async def setup_hook(self) -> None:
        await self.shard.connect()

    @staticmethod
    def route(name: Optional[str] = None):
        def decorator(func):
            endpoints_list.append((name or func.__name__, func))
            return func
        return decorator
        
    @route()
    async def get_user_data(self, data: ClientPayload):
        user = self.get_user(data.user_id)
        return user._to_minimal_user_json()
    
    @bot.event
    async def on_shard_error(self, endpoint: str, error: ClusterBaseError):
        raise error

    @bot.event
    async def on_shard_ready(self):
        print(f'shard On')

        
if __name__ == '__main__':
    bot = MyBot()
    asyncio.run(bot.run(...))
