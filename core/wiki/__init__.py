"""Wiki module for Asubarnipal V2 - Modular architecture.

Re-exports Wiki and WikiReader from submodules for backward compatibility.
"""

from core.wiki.base import Wiki
from core.wiki.reader import WikiReader

__all__ = ["Wiki", "WikiReader"]
