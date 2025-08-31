#!/usr/bin/env python3
"""
Background worker for Smartphone Price Tracker on Render.com

This worker handles long-running scraping tasks and can be scaled independently.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import SmartphonePriceTracker
from src.utils import setup_logging, get_logger
from config.settings import settings


class RenderWorker:
    """Background worker for Render.com deployment"""
    
    def __init__(self):
        # Setup logging for Render
        setup_logging(
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=None  # Log to stdout for Render
        )
        
        self.logger = get_logger(__name__)
        self.tracker = SmartphonePriceTracker()
        self.running = False
    
    async def start(self):
        """Start the background worker"""
        self.logger.info("🚀 Starting Render background worker...")
        self.running = True
        
        # Initialize database on first run
        try:
            self.tracker._init_database()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            return
        
        # Main worker loop
        while self.running:
            try:
                await self.run_worker_cycle()
            except Exception as e:
                self.logger.error(f"❌ Worker cycle failed: {e}")
            
            # Wait before next cycle (6 hours)
            self.logger.info("⏰ Waiting 6 hours until next cycle...")
            await asyncio.sleep(6 * 60 * 60)  # 6 hours
    
    async def run_worker_cycle(self):
        """Run a single worker cycle"""
        self.logger.info("🔄 Starting worker cycle...")
        
        # Run scraping
        result = await self.tracker.run_full_scraping_cycle()
        
        self.logger.info(
            f"📊 Scraping completed: {result['total_saved']}/{result['total_found']} "
            f"records saved ({result['success_rate']:.1%} success rate)"
        )
        
        # Run maintenance if it's been a day
        if self.should_run_maintenance():
            self.logger.info("🧹 Running maintenance tasks...")
            await self.tracker.run_maintenance_tasks()
        
        # Generate report if it's Monday (or enough data was collected)
        if self.should_generate_report(result):
            self.logger.info("📧 Generating weekly report...")
            success = await self.tracker.generate_weekly_report()
            
            if success:
                self.logger.info("✅ Weekly report sent successfully")
            else:
                self.logger.warning("⚠️ Failed to send weekly report")
    
    def should_run_maintenance(self) -> bool:
        """Check if maintenance should be run"""
        # Run maintenance once per day
        now = datetime.utcnow()
        return now.hour == 2  # Run at 2 AM UTC
    
    def should_generate_report(self, scraping_result: dict) -> bool:
        """Check if report should be generated"""
        now = datetime.utcnow()
        
        # Generate report on Mondays or if significant data was collected
        is_monday = now.weekday() == 0
        significant_data = scraping_result['total_saved'] > 100
        
        return is_monday or significant_data
    
    def stop(self):
        """Stop the worker gracefully"""
        self.logger.info("🛑 Stopping worker...")
        self.running = False


async def main():
    """Main entry point for the worker"""
    worker = RenderWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        worker.stop()
        worker.logger.info("👋 Worker stopped by user")
    except Exception as e:
        worker.logger.error(f"💥 Worker crashed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # For Render, we want to run the worker continuously
    asyncio.run(main())