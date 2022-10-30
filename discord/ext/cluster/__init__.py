"""
Better Cluster
~~~~~~~~~~~~~~~~~~~

A high-performance inter-process communication library designed 
to handle communication between multiple shards

:copyright: (c) 2022-present DaPandaOfficial remade by chredeur
:license: MIT, see LICENSE for more details.

"""

__version__ = "2.0"
__title__ = "better-cluster-fastapi"
__author__ = "DaPandaOfficial and chredeur"

from .client import Client
from .shard import Shard
from .objects import ClientPayload
