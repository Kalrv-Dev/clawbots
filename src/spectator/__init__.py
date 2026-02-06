"""
ClawBots Spectator Module

Human spectator interface for watching their AI bots.
"""

from .session import SpectatorSession, SpectatorManager, get_spectator_manager, init_spectator_manager

__all__ = ["SpectatorSession", "SpectatorManager", "get_spectator_manager", "init_spectator_manager"]
