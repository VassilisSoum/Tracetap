"""
TraceTap Analytics - Privacy-First Usage Tracking

Provides anonymous, opt-in usage analytics with no external dependencies.
Tracks command usage, success rates, and performance metrics locally.

Key principles:
- Disabled by default (opt-in only)
- No PII, no traffic data
- Local storage only
- Easy opt-out
- No external dependencies
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class AnalyticsManager:
    """
    Privacy-first analytics manager for tracking command usage and performance.

    Features:
    - Anonymous usage tracking (opt-in)
    - Command success/failure tracking
    - Performance metrics (duration, request counts)
    - Local-only storage (no network)
    - Easy opt-in/opt-out with clear consent
    - No external dependencies
    """

    # Default analytics directory
    DEFAULT_ANALYTICS_DIR = Path.home() / '.tracetap' / 'analytics'
    DEFAULT_STATS_FILE = 'usage_stats.json'
    DEFAULT_CONFIG_FILE = 'analytics_config.json'

    def __init__(self, analytics_dir: Optional[Path] = None):
        """
        Initialize analytics manager.

        Args:
            analytics_dir: Optional custom directory for analytics files.
                          Defaults to ~/.tracetap/analytics
        """
        self.analytics_dir = Path(analytics_dir) if analytics_dir else self.DEFAULT_ANALYTICS_DIR
        self.stats_file = self.analytics_dir / self.DEFAULT_STATS_FILE
        self.config_file = self.analytics_dir / self.DEFAULT_CONFIG_FILE

        # Create directory if needed
        self.analytics_dir.mkdir(parents=True, exist_ok=True)

        # Initialize config if not exists
        if not self.config_file.exists():
            self._init_config()

    def _init_config(self) -> None:
        """Initialize analytics configuration with opt-in disabled by default."""
        config = {
            'enabled': False,
            'version': '1.0',
            'created_at': datetime.utcnow().isoformat(),
            'consent_given_at': None,
            'notes': 'Change enabled to true to opt-in to analytics. Set to false to opt-out.'
        }
        self._write_config(config)

    def _read_config(self) -> Dict[str, Any]:
        """
        Read analytics configuration.

        Returns:
            Configuration dictionary
        """
        if not self.config_file.exists():
            self._init_config()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {'enabled': False}

    def _write_config(self, config: Dict[str, Any]) -> None:
        """
        Write analytics configuration.

        Args:
            config: Configuration dictionary to write
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't write config

    def is_enabled(self) -> bool:
        """
        Check if analytics is enabled.

        Returns:
            True if analytics is enabled, False otherwise
        """
        config = self._read_config()
        return config.get('enabled', False)

    def enable(self, verbose: bool = False) -> None:
        """
        Enable analytics (opt-in).

        Args:
            verbose: If True, print confirmation message
        """
        config = self._read_config()
        config['enabled'] = True
        config['consent_given_at'] = datetime.utcnow().isoformat()
        self._write_config(config)

        if verbose:
            print(
                "Analytics enabled. Thank you for helping improve TraceTap!\n"
                "To opt-out: tracetap analytics --disable\n"
                "Your data is stored locally at: ~/.tracetap/analytics/"
            )

    def disable(self, verbose: bool = False) -> None:
        """
        Disable analytics (opt-out).

        Args:
            verbose: If True, print confirmation message
        """
        config = self._read_config()
        config['enabled'] = False
        self._write_config(config)

        if verbose:
            print("Analytics disabled.")

    def _read_stats(self) -> Dict[str, Any]:
        """
        Read statistics file.

        Returns:
            Statistics dictionary, or empty dict if file doesn't exist
        """
        if not self.stats_file.exists():
            return self._init_stats()

        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._init_stats()

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize empty statistics structure."""
        return {
            'version': '1.0',
            'created_at': datetime.utcnow().isoformat(),
            'commands': {},
            'summary': {
                'total_commands': 0,
                'total_successes': 0,
                'total_failures': 0,
                'average_duration': 0.0,
            }
        }

    def _write_stats(self, stats: Dict[str, Any]) -> None:
        """
        Write statistics to file.

        Args:
            stats: Statistics dictionary to write
        """
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't write stats

    def track_command(
        self,
        command_name: str,
        success: bool,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track a command execution.

        Silently does nothing if analytics is disabled.

        Args:
            command_name: Name of the command (e.g., 'capture', 'analyze', 'replay')
            success: Whether the command succeeded
            duration: Duration of command in seconds
            metadata: Optional additional metadata (e.g., request_count, error_type)

        Example:
            analytics.track_command('capture', True, 2.5, {'request_count': 42})
            analytics.track_command('analyze', False, 1.2, {'error': 'timeout'})
        """
        if not self.is_enabled():
            return

        try:
            stats = self._read_stats()

            # Initialize command entry if needed
            if command_name not in stats['commands']:
                stats['commands'][command_name] = {
                    'count': 0,
                    'successes': 0,
                    'failures': 0,
                    'total_duration': 0.0,
                    'min_duration': float('inf'),
                    'max_duration': 0.0,
                    'executions': []
                }

            cmd_stats = stats['commands'][command_name]

            # Update command stats
            cmd_stats['count'] += 1
            cmd_stats['total_duration'] += duration
            cmd_stats['min_duration'] = min(cmd_stats['min_duration'], duration)
            cmd_stats['max_duration'] = max(cmd_stats['max_duration'], duration)

            if success:
                cmd_stats['successes'] += 1
            else:
                cmd_stats['failures'] += 1

            # Store execution record (keep last 100)
            execution_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'success': success,
                'duration': duration,
            }
            if metadata:
                execution_record['metadata'] = metadata

            cmd_stats['executions'].append(execution_record)
            cmd_stats['executions'] = cmd_stats['executions'][-100:]

            # Update summary
            stats['summary']['total_commands'] += 1
            stats['summary']['total_successes'] += (1 if success else 0)
            stats['summary']['total_failures'] += (0 if success else 1)

            # Recalculate average duration across all commands
            total_duration = sum(
                c['total_duration'] for c in stats['commands'].values()
            )
            total_cmds = stats['summary']['total_commands']
            stats['summary']['average_duration'] = (
                total_duration / total_cmds if total_cmds > 0 else 0.0
            )

            self._write_stats(stats)

        except Exception:
            pass  # Silently fail - analytics errors shouldn't break the app

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get local usage statistics.

        Returns:
            Dictionary containing usage statistics.
            Returns empty dict if analytics is disabled or no data available.

        Example:
            stats = analytics.get_usage_stats()
            print(f"Total commands: {stats['summary']['total_commands']}")
            print(f"Success rate: {stats['summary']['total_successes']} / {stats['summary']['total_commands']}")
        """
        if not self.is_enabled():
            return {}

        stats = self._read_stats()

        # Clean up inf values for JSON serialization
        if 'commands' in stats:
            for cmd_stats in stats['commands'].values():
                if cmd_stats['min_duration'] == float('inf'):
                    cmd_stats['min_duration'] = 0.0

        return stats

    def get_command_stats(self, command_name: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific command.

        Args:
            command_name: Name of the command

        Returns:
            Command statistics or None if not found / analytics disabled

        Example:
            capture_stats = analytics.get_command_stats('capture')
            if capture_stats:
                print(f"Success rate: {capture_stats['successes']}/{capture_stats['count']}")
        """
        if not self.is_enabled():
            return None

        stats = self._read_stats()
        cmd_stats = stats.get('commands', {}).get(command_name)

        if cmd_stats and cmd_stats['min_duration'] == float('inf'):
            cmd_stats['min_duration'] = 0.0

        return cmd_stats

    def export_stats(self, export_file: str) -> None:
        """
        Export statistics to a file for debugging/analysis.

        Exported file contains the same data as get_usage_stats().

        Args:
            export_file: Path to export file

        Example:
            analytics.export_stats('~/my-stats.json')
        """
        stats = self.get_usage_stats()

        if not stats:
            print("No statistics available to export.")
            return

        try:
            export_path = Path(export_file).expanduser()
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)

            print(f"Statistics exported to: {export_path}")
        except IOError as e:
            print(f"Error exporting statistics: {e}")

    def clear_stats(self) -> None:
        """Clear all collected statistics."""
        if self.stats_file.exists():
            try:
                self.stats_file.unlink()
            except IOError:
                pass

    def get_config_path(self) -> Path:
        """
        Get the path to the analytics config file.

        Useful for users who want to manually edit config.

        Returns:
            Path to config file
        """
        return self.config_file

    def get_stats_path(self) -> Path:
        """
        Get the path to the statistics file.

        Useful for users who want to inspect or manually manage stats.

        Returns:
            Path to stats file
        """
        return self.stats_file


# Global singleton instance
_analytics_instance: Optional[AnalyticsManager] = None


def get_analytics() -> AnalyticsManager:
    """
    Get or create the global analytics instance.

    Returns:
        Global AnalyticsManager instance
    """
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = AnalyticsManager()
    return _analytics_instance


def track_command(
    command_name: str,
    success: bool,
    duration: float,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Convenience function to track a command using the global analytics instance.

    Args:
        command_name: Name of the command
        success: Whether the command succeeded
        duration: Duration in seconds
        metadata: Optional additional metadata
    """
    get_analytics().track_command(command_name, success, duration, metadata)
