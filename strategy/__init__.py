"""
Strategy module for QQQ trading strategies.
"""

from .base_strategy import BaseStrategy
from .sma_strategy import SMA50250Strategy

__all__ = ['BaseStrategy', 'SMA50250Strategy']
