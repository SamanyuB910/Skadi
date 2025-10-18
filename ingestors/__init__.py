"""Ingestors package initialization."""
from ingestors.mock_generators import MockDataGenerator
from ingestors.foss import FOSSAdapter, foss_adapter

__all__ = ['MockDataGenerator', 'FOSSAdapter', 'foss_adapter']
