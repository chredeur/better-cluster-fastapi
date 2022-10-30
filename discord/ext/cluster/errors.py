from typing import Optional, Tuple


class ClusterBaseError(Exception):
    """Common base class for all exceptions"""
    __slots__: Tuple[str, ...] = ()
    traceback: Optional[str] = None

        
class NotConnected(ClusterBaseError):
    """Raised upon websocket not being connected"""
    pass
