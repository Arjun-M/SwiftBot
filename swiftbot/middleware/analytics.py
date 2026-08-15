"""
Analytics middleware with cache-based storage
Copyright (c) 2025 Arjun-M/SwiftBot
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict, deque
from .base import Middleware


class AnalyticsCollector(Middleware):
    """
    Analytics collection middleware with cache-based storage.

    Features:
    - User session tracking
    - Command usage statistics
    - Performance monitoring
    - Error tracking
    - Real-time metrics

    Copyright (c) 2025 Arjun-M/SwiftBot
    """

    def __init__(
        self,
        session_timeout: int = 1800,
        max_sessions: int = 10000,
        enable_real_time: bool = True,
        cleanup_interval: int = 300
    ):
        self.session_timeout = session_timeout
        self.max_sessions = max_sessions
        self.enable_real_time = enable_real_time
        self.cleanup_interval = cleanup_interval

        # Cache-based storage
        self.user_sessions = {}
        self.command_stats = {}
        self.performance_history = deque(maxlen=1440)  # 24 hours

        # Real-time metrics
        self.current_metrics = {
            'active_users': 0,
            'messages_per_second': 0,
            'error_rate': 0,
            'response_times': deque(maxlen=1000)
        }

        # Counters
        self.message_counter = 0
        self.error_counter = 0
        self.last_reset_time = time.time()
        self.last_cleanup = time.time()

    async def on_update(self, ctx, next_handler):
        """Process update and collect analytics"""
        start_time = time.time()

        try:
            # Track user session
            self._track_user_session(ctx)

            # Track command usage
            if ctx.text and ctx.text.startswith('/'):
                command = ctx.text.split()[0]
                self._track_command_usage(ctx, command)

            self.message_counter += 1

            # Periodic cleanup
            if start_time - self.last_cleanup > self.cleanup_interval:
                self._cleanup_old_data(start_time)

            await next_handler()

            # Track response time
            response_time = time.time() - start_time
            self.current_metrics['response_times'].append(response_time)

        except Exception as e:
            self.error_counter += 1
            raise

    def _track_user_session(self, ctx):
        """Track user session in cache"""
        if not ctx.user:
            return

        user_id = ctx.user.id
        current_time = time.time()

        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'user_id': user_id,
                'username': ctx.user.username,
                'start_time': current_time,
                'last_activity': current_time,
                'messages_sent': 1,
                'commands_used': set(),
                'errors': 0
            }
        else:
            session = self.user_sessions[user_id]
            session['last_activity'] = current_time
            session['messages_sent'] += 1

        # Cleanup if at capacity
        if len(self.user_sessions) > self.max_sessions:
            self._cleanup_old_sessions(current_time)

    def _track_command_usage(self, ctx, command: str):
        """Track command usage in cache"""
        current_time = time.time()

        if command not in self.command_stats:
            self.command_stats[command] = {
                'command': command,
                'total_uses': 1,
                'unique_users': set(),
                'response_times': deque(maxlen=100),
                'last_used': current_time,
                'errors': 0
            }
        else:
            self.command_stats[command]['total_uses'] += 1
            self.command_stats[command]['last_used'] = current_time

        # Track unique users
        if ctx.user:
            self.command_stats[command]['unique_users'].add(ctx.user.id)
            if ctx.user.id in self.user_sessions:
                self.user_sessions[ctx.user.id]['commands_used'].add(command)

    def _cleanup_old_sessions(self, current_time: float):
        """Clean up old sessions from cache"""
        expired_sessions = [
            user_id for user_id, session in self.user_sessions.items()
            if current_time - session['last_activity'] > self.session_timeout
        ]

        for user_id in expired_sessions:
            del self.user_sessions[user_id]

    def _cleanup_old_data(self, current_time: float):
        """Clean up old analytics data"""
        self._cleanup_old_sessions(current_time)

        # Clean up command stats (remove commands not used in last 24 hours)
        cutoff_time = current_time - 86400  # 24 hours
        old_commands = [
            cmd for cmd, stats in self.command_stats.items()
            if stats['last_used'] < cutoff_time
        ]

        for cmd in old_commands:
            del self.command_stats[cmd]

        self.last_cleanup = current_time

    async def on_error(self, ctx, error):
        """Track error analytics"""
        self.error_counter += 1

        if ctx and ctx.user and ctx.user.id in self.user_sessions:
            self.user_sessions[ctx.user.id]['errors'] += 1

        if ctx and ctx.text and ctx.text.startswith('/'):
            command = ctx.text.split()[0]
            if command in self.command_stats:
                self.command_stats[command]['errors'] += 1

    def get_stats(self) -> dict:
        """Get analytics statistics"""
        current_time = time.time()
        active_users = len([
            s for s in self.user_sessions.values()
            if current_time - s['last_activity'] < 300  # 5 minutes
        ])

        return {
            'active_sessions': len(self.user_sessions),
            'active_users_5min': active_users,
            'total_commands_tracked': len(self.command_stats),
            'messages_processed': self.message_counter,
            'errors_tracked': self.error_counter,
        }

    def get_current_metrics(self) -> dict:
        """Get current real-time metrics"""
        current_time = time.time()
        time_diff = current_time - self.last_reset_time

        messages_per_second = self.message_counter / max(time_diff, 1) if time_diff > 0 else 0
        error_rate = (self.error_counter / max(self.message_counter, 1)) * 100

        avg_response_time = (
            sum(self.current_metrics['response_times']) / 
            max(len(self.current_metrics['response_times']), 1)
        )

        return {
            'messages_per_second': round(messages_per_second, 2),
            'error_rate': round(error_rate, 2),
            'average_response_time': round(avg_response_time * 1000, 2),  # ms
            'active_sessions': len(self.user_sessions)
        }
