#!/usr/bin/env python3
"""
Main entry point for Smartphone Price Tracker

This module provides the main orchestration logic for the price tracking system.
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import settings, PHONE_MODELS, PLATFORMS
from src.database import init_database, db_manager
from src.scrapers import ScraperFactory, PriceData
from src.analysis import PriceAnalyzer, CurrencyConverter
from src.reporting import EmailReporter, ChartGenerator
from src.scheduler import AsyncTaskScheduler
from src.utils import setup_logging, get_logger, TimedLogger


class SmartphonePriceTracker:
    """Main application class for the smartphone price tracker"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.scheduler = AsyncTaskScheduler()
        
        # Initialize components
        self._init_logging()
        self._init_database()
    
    def _init_logging(self):
        """Initialize logging system"""
        setup_logging(
            log_level=settings.log_level,
            log_file=settings.log_file
        )
        self.logger.info("Smartphone Price Tracker initialized")
    
    def _init_database(self):
        """Initialize database connection and schema"""
        try:
            # Test database connection
            if not db_manager.test_connection():
                raise Exception("Database connection failed")
            
            # Create tables if they don't exist
            db_manager.create_tables()
            
            # Initialize default data
            db_manager.init_default_data()
            
            self.logger.info("Database initialization completed")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    async def run_full_scraping_cycle(self) -> Dict[str, Any]:
        """Run a complete scraping cycle for all platforms and models"""
        self.logger.info("Starting full scraping cycle")
        
        session_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        total_records = 0
        successful_records = 0
        failed_platforms = []
        
        with TimedLogger(self.logger, "full scraping cycle"):
            # Get all models to scrape
            models_to_scrape = self._get_models_list()
            
            for region_name, region_platforms in PLATFORMS.items():
                for platform_name, platform_config in region_platforms.items():
                    try:
                        platform_config['region'] = region_name
                        
                        self.logger.info(f"Scraping {platform_name} ({region_name})")
                        
                        # Create scraper
                        proxy_list = settings.proxy_list if settings.use_proxy else []
                        scraper = ScraperFactory.create_scraper(
                            platform_name, platform_config, proxy_list
                        )
                        
                        # Scrape prices
                        price_data = await scraper.scrape_phone_prices(models_to_scrape)
                        
                        if price_data:
                            total_records += len(price_data)
                            
                            # Save to database
                            success_count = await self._save_price_data(price_data, session_id)
                            successful_records += success_count
                            
                            self.logger.info(
                                f"Scraped {len(price_data)} records from {platform_name}, "
                                f"saved {success_count}"
                            )
                        
                    except Exception as e:
                        self.logger.error(f"Error scraping {platform_name}: {e}")
                        failed_platforms.append(platform_name)
        
        result = {
            'session_id': session_id,
            'total_found': total_records,
            'total_saved': successful_records,
            'failed_platforms': failed_platforms,
            'success_rate': successful_records / total_records if total_records > 0 else 0
        }
        
        self.logger.info(
            f"Scraping cycle completed: {successful_records}/{total_records} records saved "
            f"({result['success_rate']:.1%} success rate)"
        )
        
        return result
    
    def _get_models_list(self) -> List[str]:
        """Get list of phone models to scrape"""
        models = []
        
        for brand, brand_models in PHONE_MODELS.items():
            for model_name, storage_options in brand_models.items():
                for storage in storage_options:
                    models.append(f"{brand} {model_name} {storage}")
        
        return models
    
    async def _save_price_data(self, price_data: List[PriceData], session_id: str) -> int:
        """Save price data to database and return count of successful saves"""
        try:
            with db_manager.get_session() as session:
                converter = CurrencyConverter(session)
                records = []
                
                for price_item in price_data:
                    # Find phone model in database
                    from src.database import PhoneModel, Platform
                    
                    phone_model = session.query(PhoneModel).filter_by(
                        brand=price_item.brand,
                        model_name=price_item.phone_model,
                        storage_capacity=price_item.storage
                    ).first()
                    
                    # Find platform in database
                    platform = session.query(Platform).filter_by(
                        name=price_item.platform,
                        region=price_item.region
                    ).first()
                    
                    if phone_model and platform:
                        # Convert price to USD
                        price_usd = price_item.price
                        if price_item.currency != 'USD':
                            converted = converter.convert_to_usd(
                                price_item.price, price_item.currency
                            )
                            if converted:
                                price_usd = converted
                        
                        record_data = {
                            'phone_model_id': phone_model.id,
                            'platform_id': platform.id,
                            'condition': price_item.condition,
                            'price': price_item.price,
                            'currency': price_item.currency,
                            'price_usd': price_usd,
                            'availability': price_item.availability,
                            'stock_count': price_item.stock_count,
                            'product_url': price_item.product_url,
                            'scrape_session_id': session_id
                        }
                        records.append(record_data)
                
                # Save records
                if records:
                    success = db_manager.save_price_records(session, records, session_id)
                    return len(records) if success else 0
                
                return 0
                
        except Exception as e:
            self.logger.error(f"Error saving price data: {e}")
            return 0
    
    async def generate_weekly_report(self) -> bool:
        """Generate and send weekly report"""
        self.logger.info("Generating weekly report")
        
        try:
            with db_manager.get_session() as session:
                # Generate analysis
                analyzer = PriceAnalyzer(session)
                
                with TimedLogger(self.logger, "price analysis"):
                    analyses = analyzer.analyze_price_trends(days_back=7)
                    
                    insights = []
                    insights.extend(analyzer.find_arbitrage_opportunities())
                    insights.extend(analyzer.find_significant_price_changes())
                    insights.extend(analyzer.find_best_deals())
                    
                    summary = analyzer.generate_market_summary()
                
                # Generate charts
                charts = {}
                if settings.email_from:  # Only generate charts if email is configured
                    with TimedLogger(self.logger, "chart generation"):
                        chart_generator = ChartGenerator(session)
                        charts = chart_generator.generate_all_charts()
                
                # Create and send email report
                if settings.email_to and settings.smtp_username:
                    smtp_config = {
                        'smtp_server': settings.smtp_server,
                        'smtp_port': settings.smtp_port,
                        'smtp_username': settings.smtp_username,
                        'smtp_password': settings.smtp_password,
                        'email_from': settings.email_from
                    }
                    
                    reporter = EmailReporter(smtp_config)
                    
                    with TimedLogger(self.logger, "report generation"):
                        html_content = reporter.generate_weekly_report(
                            analyses, insights, summary, charts
                        )
                    
                    subject = f"Weekly Smartphone Price Report - {datetime.now().strftime('%B %d, %Y')}"
                    
                    success = reporter.send_email_report(
                        settings.email_to, subject, html_content
                    )
                    
                    if success:
                        self.logger.info("Weekly report sent successfully")
                        return True
                    else:
                        self.logger.error("Failed to send weekly report")
                        return False
                
                else:
                    self.logger.warning("Email not configured, skipping report sending")
                    return False
        
        except Exception as e:
            self.logger.error(f"Error generating weekly report: {e}")
            return False
    
    async def run_maintenance_tasks(self):
        """Run maintenance tasks like database cleanup"""
        self.logger.info("Running maintenance tasks")
        
        try:
            with db_manager.get_session() as session:
                # Clean up old price records
                deleted_count = db_manager.cleanup_old_records(session, keep_days=90)
                self.logger.info(f"Cleaned up {deleted_count} old price records")
                
                # Update currency rates
                converter = CurrencyConverter(session)
                converter.update_fallback_rates()
                self.logger.info("Updated currency exchange rates")
        
        except Exception as e:
            self.logger.error(f"Error in maintenance tasks: {e}")
    
    async def start_scheduler(self):
        """Start the async task scheduler"""
        self.logger.info("Starting task scheduler")
        
        # Add scheduled tasks
        self.scheduler.add_async_task(self.run_full_scraping_cycle, interval_minutes=360)  # 6 hours
        self.scheduler.add_async_task(self.generate_weekly_report, interval_minutes=10080)  # 7 days
        self.scheduler.add_async_task(self.run_maintenance_tasks, interval_minutes=1440)   # 24 hours
        
        # Start the scheduler
        await self.scheduler.start()
    
    async def run_once(self):
        """Run a single scraping and reporting cycle"""
        self.logger.info("Running single cycle")
        
        # Run scraping
        scraping_result = await self.run_full_scraping_cycle()
        
        # Generate report if we got data
        if scraping_result['total_saved'] > 0:
            await self.generate_weekly_report()
        
        # Run maintenance
        await self.run_maintenance_tasks()
        
        return scraping_result


# Create Flask app for Render web service
def create_app():
    """Create Flask app for web service"""
    try:
        from app import app
        return app
    except ImportError:
        # Fallback if app.py not available
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/health')
        def health():
            return {'status': 'healthy'}, 200
            
        return app

# For Gunicorn on Render
app = create_app()


async def main():
    """Main entry point"""
    tracker = SmartphonePriceTracker()
    
    # Check if running with scheduler or once
    if len(sys.argv) > 1 and sys.argv[1] == '--scheduler':
        await tracker.start_scheduler()
    else:
        result = await tracker.run_once()
        print(f"Scraping completed: {result['total_saved']}/{result['total_found']} records saved")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Smartphone Price Tracker stopped by user")