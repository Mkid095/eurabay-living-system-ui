"""
Custom migration system for EURABAY Living System.

This module provides a lightweight, custom migration system for SQLite database
schema evolution. It tracks applied migrations and supports rollback operations.
"""
from .migration_base import Migration
from .migration_manager import MigrationManager

__all__ = ["Migration", "MigrationManager"]
