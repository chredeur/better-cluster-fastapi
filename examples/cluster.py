import asyncio
import logging
from discord.utils import _ColourFormatter
from discord.ext.cluster import Cluster

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(_ColourFormatter())
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

if __name__ == "__main__":
    setup_logging()
    cluster = Cluster()
    asyncio.run(cluster.start())
