import schedule
import time
import asyncio
from typing import Callable, List, Dict, Any
from datetime import datetime, timedelta
import logging
from threading import Thread
import signal
import sys
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TaskScheduler:
    """Handles scheduling of scraping and reporting tasks"""
    
    def __init__(self):
        self.running = False
        self.scheduler_thread = None
        self.tasks = []
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def add_weekly_task(self, func: Callable, day: str = 'monday', time_str: str = '09:00'):
        """Add a weekly recurring task"""
        try:
            job = getattr(schedule.every(), day.lower()).at(time_str).do(func)
            self.tasks.append({
                'type': 'weekly',
                'function': func.__name__,
                'day': day,
                'time': time_str,
                'job': job
            })
            logger.info(f"Scheduled weekly task {func.__name__} for {day} at {time_str}")
        except Exception as e:
            logger.error(f"Error scheduling weekly task: {e}")
    
    def add_daily_task(self, func: Callable, time_str: str = '09:00'):
        """Add a daily recurring task"""
        try:
            job = schedule.every().day.at(time_str).do(func)
            self.tasks.append({
                'type': 'daily',
                'function': func.__name__,
                'time': time_str,
                'job': job
            })
            logger.info(f"Scheduled daily task {func.__name__} at {time_str}")
        except Exception as e:
            logger.error(f"Error scheduling daily task: {e}")
    
    def add_hourly_task(self, func: Callable, minute: int = 0):
        """Add an hourly recurring task"""
        try:
            job = schedule.every().hour.at(f":{minute:02d}").do(func)
            self.tasks.append({
                'type': 'hourly',
                'function': func.__name__,
                'minute': minute,
                'job': job
            })
            logger.info(f"Scheduled hourly task {func.__name__} at minute {minute}")
        except Exception as e:
            logger.error(f"Error scheduling hourly task: {e}")
    
    def add_interval_task(self, func: Callable, interval_minutes: int):
        """Add a task that runs at specified intervals"""
        try:
            job = schedule.every(interval_minutes).minutes.do(func)
            self.tasks.append({
                'type': 'interval',
                'function': func.__name__,
                'interval_minutes': interval_minutes,
                'job': job
            })
            logger.info(f"Scheduled interval task {func.__name__} every {interval_minutes} minutes")
        except Exception as e:
            logger.error(f"Error scheduling interval task: {e}")
    
    def start(self):
        """Start the scheduler in a separate thread"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Task scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Task scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Scheduler thread started")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Continue after error
        
        logger.info("Scheduler thread stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down scheduler...")
        self.stop()
        sys.exit(0)
    
    def get_next_run_times(self) -> List[Dict[str, Any]]:
        """Get next run times for all scheduled tasks"""
        next_runs = []
        
        for task in self.tasks:
            try:
                next_run = task['job'].next_run
                if next_run:
                    next_runs.append({
                        'function': task['function'],
                        'type': task['type'],
                        'next_run': next_run,
                        'next_run_str': next_run.strftime('%Y-%m-%d %H:%M:%S')
                    })
            except Exception as e:
                logger.error(f"Error getting next run time for {task['function']}: {e}")
        
        return sorted(next_runs, key=lambda x: x['next_run'])
    
    def clear_all_tasks(self):
        """Clear all scheduled tasks"""
        schedule.clear()
        self.tasks.clear()
        logger.info("All scheduled tasks cleared")
    
    def run_task_now(self, func: Callable):
        """Run a task immediately"""
        try:
            logger.info(f"Running task {func.__name__} immediately")
            func()
        except Exception as e:
            logger.error(f"Error running task {func.__name__}: {e}")


class AsyncTaskScheduler:
    """Async version of task scheduler for async functions"""
    
    def __init__(self):
        self.running = False
        self.tasks = []
        self.loop = None
    
    def add_async_task(self, coro_func: Callable, interval_minutes: int):
        """Add an async task that runs at specified intervals"""
        self.tasks.append({
            'function': coro_func,
            'interval_minutes': interval_minutes,
            'last_run': None
        })
        logger.info(f"Added async task {coro_func.__name__} with {interval_minutes} minute interval")
    
    async def start(self):
        """Start the async scheduler"""
        if self.running:
            logger.warning("Async scheduler is already running")
            return
        
        self.running = True
        self.loop = asyncio.get_event_loop()
        
        logger.info("Async task scheduler started")
        
        while self.running:
            current_time = datetime.utcnow()
            
            for task in self.tasks:
                try:
                    should_run = False
                    
                    if task['last_run'] is None:
                        should_run = True
                    else:
                        time_since_last = current_time - task['last_run']
                        if time_since_last >= timedelta(minutes=task['interval_minutes']):
                            should_run = True
                    
                    if should_run:
                        logger.info(f"Running async task {task['function'].__name__}")
                        await task['function']()
                        task['last_run'] = current_time
                        
                except Exception as e:
                    logger.error(f"Error running async task {task['function'].__name__}: {e}")
            
            # Sleep for 1 minute before next check
            await asyncio.sleep(60)
    
    def stop(self):
        """Stop the async scheduler"""
        self.running = False
        logger.info("Async task scheduler stopped")