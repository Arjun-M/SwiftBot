"""
Advanced Analytics Middleware
Copyright (c) 2025 Arjun-M/SwiftBot

Comprehensive analytics collection for bot performance monitoring:
- User engagement tracking
- Command usage statistics
- Performance metrics
- Real-time dashboard data
- Error analytics
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict

from .base import Middleware
from ..exceptions import MiddlewareError


@dataclass
class UserSession:
    """User session tracking"""
    user_id: int
    username: Optional[str]
    first_name: str
    start_time: float
    last_activity: float
    commands_used: List[str]
    messages_sent: int
    errors_encountered: int
    session_duration: float = 0


@dataclass
class CommandStats:
    """Command usage statistics"""
    command: str
    total_uses: int
    unique_users: int
    average_response_time: float
    success_rate: float
    last_used: float
    error_count: int


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    timestamp: float
    active_users: int
    messages_per_second: float
    average_response_time: float
    memory_usage: float
    cpu_usage: float
    error_rate: float


class AnalyticsCollector(Middleware):
    """
    Advanced Analytics Collection Middleware
    
    Features:
    - Real-time user session tracking
    - Command usage analytics
    - Performance monitoring
    - Error tracking and analysis
    - Customizable metrics collection
    - Export capabilities for dashboards
    """

    def __init__(
        self,
        storage_backend=None,
        session_timeout: int = 1800,  # 30 minutes
        metrics_interval: int = 60,   # 1 minute
        max_sessions: int = 10000,
        enable_real_time: bool = True,
        custom_metrics: Optional[Dict[str, Callable]] = None
    ):
        self.storage = storage_backend
        self.session_timeout = session_timeout
        self.metrics_interval = metrics_interval
        self.max_sessions = max_sessions
        self.enable_real_time = enable_real_time
        self.custom_metrics = custom_metrics or {}

        # In-memory analytics storage
        self.user_sessions: Dict[int, UserSession] = {}
        self.command_stats: Dict[str, CommandStats] = {}
        self.performance_history: deque = deque(maxlen=1440)  # 24 hours of minutes
        
        # Real-time metrics
        self.current_metrics = {
            'active_users': 0,
            'messages_per_second': 0,
            'commands_per_minute': 0,
            'error_rate': 0,
            'response_times': deque(maxlen=1000),
            'memory_usage': 0,
            'cpu_usage': 0
        }
        
        # Counters for rate calculations
        self.message_counter = 0
        self.command_counter = 0
        self.error_counter = 0
        self.last_reset_time = time.time()
        
        # Background tasks
        self._background_tasks = []
        self._running = False

    async def start(self):
        """Start analytics collection"""
        self._running = True
        
        # Start background tasks
        if self.enable_real_time:
            task = asyncio.create_task(self._metrics_collector_task())
            self._background_tasks.append(task)
        
        task = asyncio.create_task(self._session_cleanup_task())
        self._background_tasks.append(task)

    async def stop(self):
        """Stop analytics collection"""
        self._running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Save final analytics if storage is available
        if self.storage:
            await self._save_analytics()

    async def on_update(self, ctx, next_handler):
        """Process update and collect analytics"""
        start_time = time.time()
        
        try:
            # Track user session
            await self._track_user_session(ctx)
            
            # Track command usage if applicable
            if ctx.text and ctx.text.startswith('/'):
                command = ctx.text.split()[0]
                await self._track_command_usage(ctx, command)
            
            # Update message counter
            self.message_counter += 1
            
            # Call next handler
            await next_handler()
            
            # Track successful completion
            response_time = time.time() - start_time
            self.current_metrics['response_times'].append(response_time)
            
            # Update command success if applicable
            if ctx.text and ctx.text.startswith('/'):
                command = ctx.text.split()[0]
                if command in self.command_stats:
                    self._update_command_success(command, response_time)

        except Exception as e:
            # Track error
            await self._track_error(ctx, e, time.time() - start_time)
            raise

    async def on_error(self, ctx, error):
        """Handle errors and collect error analytics"""
        self.error_counter += 1
        await self._track_error(ctx, error, 0)

    async def _track_user_session(self, ctx):
        """Track user session data"""
        if not ctx.user:
            return

        user_id = ctx.user.id
        current_time = time.time()
        
        if user_id not in self.user_sessions:
            # Create new session
            session = UserSession(
                user_id=user_id,
                username=ctx.user.username,
                first_name=ctx.user.first_name,
                start_time=current_time,
                last_activity=current_time,
                commands_used=[],
                messages_sent=1,
                errors_encountered=0
            )
            self.user_sessions[user_id] = session
        else:
            # Update existing session
            session = self.user_sessions[user_id]
            session.last_activity = current_time
            session.messages_sent += 1
            session.session_duration = current_time - session.start_time

        # Cleanup old sessions if at capacity
        if len(self.user_sessions) > self.max_sessions:
            await self._cleanup_old_sessions()

    async def _track_command_usage(self, ctx, command: str):
        """Track command usage statistics"""
        current_time = time.time()
        
        if command not in self.command_stats:
            self.command_stats[command] = CommandStats(
                command=command,
                total_uses=1,
                unique_users=1,
                average_response_time=0,
                success_rate=100.0,
                last_used=current_time,
                error_count=0
            )
        else:
            stats = self.command_stats[command]
            stats.total_uses += 1
            stats.last_used = current_time
            
            # Track unique users (simplified - could use bloom filter for large scale)
            if ctx.user and ctx.user.id in self.user_sessions:
                session = self.user_sessions[ctx.user.id]
                if command not in session.commands_used:
                    session.commands_used.append(command)
                    stats.unique_users += 1

        self.command_counter += 1

    def _update_command_success(self, command: str, response_time: float):
        """Update command success metrics"""
        if command in self.command_stats:
            stats = self.command_stats[command]
            
            # Update average response time (exponential moving average)
            alpha = 0.1  # Smoothing factor
            stats.average_response_time = (
                alpha * response_time + (1 - alpha) * stats.average_response_time
            )
            
            # Update success rate
            total_attempts = stats.total_uses
            successful_attempts = total_attempts - stats.error_count
            stats.success_rate = (successful_attempts / total_attempts) * 100

    async def _track_error(self, ctx, error: Exception, response_time: float):
        """Track error analytics"""
        if ctx and ctx.text and ctx.text.startswith('/'):
            command = ctx.text.split()[0]
            if command in self.command_stats:
                self.command_stats[command].error_count += 1
        
        if ctx and ctx.user and ctx.user.id in self.user_sessions:
            self.user_sessions[ctx.user.id].errors_encountered += 1

    async def _metrics_collector_task(self):
        """Background task for collecting performance metrics"""
        while self._running:
            try:
                await self._collect_performance_metrics()
                await asyncio.sleep(self.metrics_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                print(f"Error in metrics collector: {e}")
                await asyncio.sleep(self.metrics_interval)

    async def _collect_performance_metrics(self):
        """Collect current performance metrics"""
        current_time = time.time()
        time_diff = current_time - self.last_reset_time
        
        # Calculate rates
        messages_per_second = self.message_counter / max(time_diff, 1)
        commands_per_minute = (self.command_counter / max(time_diff, 1)) * 60
        error_rate = (self.error_counter / max(self.message_counter, 1)) * 100
        
        # Calculate average response time
        avg_response_time = (
            sum(self.current_metrics['response_times']) / 
            max(len(self.current_metrics['response_times']), 1)
        )
        
        # Get system metrics
        try:
            import psutil
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent()
        except ImportError:
            memory_usage = 0
            cpu_usage = 0
        
        # Active users (users active in last session_timeout)
        active_users = len([
            s for s in self.user_sessions.values()
            if current_time - s.last_activity < self.session_timeout
        ])
        
        # Create performance snapshot
        metrics = PerformanceMetrics(
            timestamp=current_time,
            active_users=active_users,
            messages_per_second=messages_per_second,
            average_response_time=avg_response_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            error_rate=error_rate
        )
        
        self.performance_history.append(metrics)
        
        # Update current metrics
        self.current_metrics.update({
            'active_users': active_users,
            'messages_per_second': messages_per_second,
            'commands_per_minute': commands_per_minute,
            'error_rate': error_rate,
            'memory_usage': memory_usage,
            'cpu_usage': cpu_usage
        })
        
        # Reset counters
        self.message_counter = 0
        self.command_counter = 0
        self.error_counter = 0
        self.last_reset_time = current_time
        
        # Save to storage if available
        if self.storage:
            await self._save_metrics(metrics)

    async def _session_cleanup_task(self):
        """Background task for cleaning up old sessions"""
        while self._running:
            try:
                await self._cleanup_old_sessions()
                await asyncio.sleep(300)  # Run every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in session cleanup: {e}")
                await asyncio.sleep(300)

    async def _cleanup_old_sessions(self):
        """Clean up expired user sessions"""
        current_time = time.time()
        expired_sessions = [
            user_id for user_id, session in self.user_sessions.items()
            if current_time - session.last_activity > self.session_timeout
        ]
        
        for user_id in expired_sessions:
            # Save session data before removal if storage available
            if self.storage:
                await self._save_session(self.user_sessions[user_id])
            
            del self.user_sessions[user_id]

    async def _save_analytics(self):
        """Save analytics data to storage backend"""
        if not self.storage:
            return
        
        try:
            # Save command stats
            for command, stats in self.command_stats.items():
                await self.storage.set(f"command_stats:{command}", asdict(stats))
            
            # Save performance history
            performance_data = [asdict(m) for m in list(self.performance_history)]
            await self.storage.set("performance_history", performance_data)
            
            # Save active sessions
            session_data = {
                str(user_id): asdict(session) 
                for user_id, session in self.user_sessions.items()
            }
            await self.storage.set("active_sessions", session_data)
            
        except Exception as e:
            raise MiddlewareError(f"Failed to save analytics: {e}", middleware_name="AnalyticsCollector")

    async def _save_session(self, session: UserSession):
        """Save individual session data"""
        if self.storage:
            await self.storage.set(f"session:{session.user_id}:{int(session.start_time)}", asdict(session))

    async def _save_metrics(self, metrics: PerformanceMetrics):
        """Save performance metrics"""
        if self.storage:
            await self.storage.set(f"metrics:{int(metrics.timestamp)}", asdict(metrics))

    # Public API methods
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics"""
        return self.current_metrics.copy()

    def get_command_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get command usage statistics"""
        return {cmd: asdict(stats) for cmd, stats in self.command_stats.items()}

    def get_user_sessions(self) -> Dict[int, Dict[str, Any]]:
        """Get active user sessions"""
        return {user_id: asdict(session) for user_id, session in self.user_sessions.items()}

    def get_performance_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance history for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        return [
            asdict(metrics) for metrics in self.performance_history
            if metrics.timestamp > cutoff_time
        ]

    def get_top_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top commands by usage"""
        sorted_commands = sorted(
            self.command_stats.items(),
            key=lambda x: x[1].total_uses,
            reverse=True
        )
        return [asdict(stats) for _, stats in sorted_commands[:limit]]

    def get_user_engagement_stats(self) -> Dict[str, Any]:
        """Get user engagement statistics"""
        current_time = time.time()
        active_sessions = [
            s for s in self.user_sessions.values()
            if current_time - s.last_activity < self.session_timeout
        ]
        
        if not active_sessions:
            return {
                'total_active_users': 0,
                'average_session_duration': 0,
                'average_messages_per_session': 0,
                'total_commands_used': 0
            }
        
        total_duration = sum(s.session_duration for s in active_sessions)
        total_messages = sum(s.messages_sent for s in active_sessions)
        total_commands = sum(len(s.commands_used) for s in active_sessions)
        
        return {
            'total_active_users': len(active_sessions),
            'average_session_duration': total_duration / len(active_sessions),
            'average_messages_per_session': total_messages / len(active_sessions),
            'total_commands_used': total_commands
        }

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary"""
        return {
            'current_metrics': self.get_current_metrics(),
            'command_stats': len(self.command_stats),
            'top_commands': self.get_top_commands(5),
            'user_engagement': self.get_user_engagement_stats(),
            'system_info': {
                'total_sessions_tracked': len(self.user_sessions),
                'performance_data_points': len(self.performance_history),
                'analytics_uptime': time.time() - self.last_reset_time
            }
        }

    def reset_analytics(self):
        """Reset all analytics data"""
        self.user_sessions.clear()
        self.command_stats.clear()
        self.performance_history.clear()
        self.current_metrics = {
            'active_users': 0,
            'messages_per_second': 0,
            'commands_per_minute': 0,
            'error_rate': 0,
            'response_times': deque(maxlen=1000),
            'memory_usage': 0,
            'cpu_usage': 0
        }
        self.message_counter = 0
        self.command_counter = 0
        self.error_counter = 0
        self.last_reset_time = time.time()
