# Better Cluster Fastapi


<a><img src="https://img.shields.io/pypi/pyversions/better-cluster">
<img src="https://img.shields.io/github/last-commit/chredeur0/better-cluster-fastapi">
<img src="https://img.shields.io/github/license/chredeur0/better-cluster-fastapi">
<a href="https://discord.gg/Q8EHcWkmZU" target="_blank"><img src="https://img.shields.io/discord/1004840384091922473?label=discord"></a>

## A high-performance inter-process communication library designed to handle communication between multiple shards

<img src="https://raw.githubusercontent.com/chredeur0/better-cluster-fastapi/main/images/banner.png">

#### This library is made to handle multiple discord clients. If you want something simpler or have only one client, check out [better-ipc](https://github.com/MiroslavRosenov/better-ipc)

# Installation
> ### Stable version
#### For Linux
```shell
python3 -m pip install -U git+https://github.com/chredeur0/better-cluster-fastapi
```
#### For Windows
```shell
py -m pip install -U git+https://github.com/chredeur0/better-cluster-fastapi
```

# Support

You can join the support server [here](https://discord.gg/Q8EHcWkmZU)

# Examples

## Example of a shard
```python
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
```


## Example of web client
```python
from quart import Quart
from discord.ext import cluster

app = Quart(__name__)
ipc = cluster.Client()

@app.route('/')
async def main():
    return await ipc.request("get_user_data", 1, user_id=383946213629624322)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
```
