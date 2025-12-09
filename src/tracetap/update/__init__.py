"""
TraceTap Collection Update Module

This module provides functionality to update existing Postman collections
with data from new captures while preserving user customizations.
"""

from .updater import CollectionUpdater, UpdateConfig, UpdateResult

__all__ = ['CollectionUpdater', 'UpdateConfig', 'UpdateResult']
