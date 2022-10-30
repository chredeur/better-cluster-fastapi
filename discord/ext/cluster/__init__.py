"""
Better Cluster
~~~~~~~~~~~~~~~~~~~

A high-performance inter-process communication library designed 
to handle communication between multiple shards

:copyright: (c) 2022-present DaPandaOfficial
:license: MIT, see LICENSE for more details.

"""

__version__ = "1.0.0"
__title__ = "better-cluster"
__author__ = "DaPandaOfficial"

from .cluster import Cluster
from .client import Client
from .shard import Shard
from .objects import ClientPayload
