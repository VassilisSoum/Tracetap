"""
TraceTap Replay Module

Traffic replay and mock server functionality for captured HTTP traffic.

This module provides:
- Request replay with variable substitution
- Mock server generation from captures
- Response comparison and validation
- Test scenario generation
"""

from .replayer import TrafficReplayer
from .variables import VariableExtractor, VariableSubstitutor
from .replay_config import ReplayConfig

__all__ = [
    'TrafficReplayer',
    'VariableExtractor',
    'VariableSubstitutor',
    'ReplayConfig',
]

__version__ = '1.0.0'
