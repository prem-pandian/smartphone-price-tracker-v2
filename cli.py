#!/usr/bin/env python3
"""
Smartphone Price Tracker CLI

A comprehensive tool for tracking smartphone prices across multiple secondary markets.
"""

import click
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import settings, PHONE_MODELS, PLATFORMS
from src.database import init_database, db_manager, get_db_session
from src.scrapers import ScraperFactory, PriceData
from src.analysis import PriceAnalyzer, CurrencyConverter
from src.reporting import EmailReporter, ChartGenerator
from src.scheduler import TaskScheduler
from src.utils import setup_logging, get_logger, TimedLogger


def setup_cli_logging():
    """Setup logging for CLI"""
    log_file = settings.log_file if hasattr(settings, 'log_file') else 'logs/cli.log'
    setup_logging(log_level=settings.log_level, log_file=log_file)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
@click.pass_context
def cli(ctx, debug, config):
    """Smartphone Price Tracker - Monitor refurbished phone prices globally"""
    ctx.ensure_object(dict)
    
    if debug:
        ctx.obj['log_level'] = 'DEBUG'
    
    setup_cli_logging()
    logger = get_logger(__name__)
    logger.info("Starting Smartphone Price Tracker CLI")


@cli.command()
@click.option('--drop-existing', is_flag=True, help='Drop existing tables first')
def init(drop_existing):
    """Initialize the database and load default data"""
    logger = get_logger(__name__)
    
    with TimedLogger(logger, "database initialization"):
        if drop_existing:
            click.echo("Dropping existing database tables...")
            db_manager.drop_tables()
        
        click.echo("Initializing database...")
        init_database()
        click.echo("✅ Database initialized successfully!")


@cli.command()
@click.option('--region', type=click.Choice(['US', 'Europe', 'Japan', 'India']), 
              help='Specific region to scrape')
@click.option('--platform', help='Specific platform to scrape')
@click.option('--model', help='Specific phone model to scrape (e.g., "iPhone 16")')
@click.option('--dry-run', is_flag=True, help='Run scraping without saving to database')
@click.option('--max-workers', default=5, help='Maximum concurrent scrapers')
def scrape(region, platform, model, dry_run, max_workers):
    """Scrape phone prices from configured platforms"""
    logger = get_logger(__name__)
    
    if dry_run:
        click.echo("🔍 Running in dry-run mode (no data will be saved)")
    
    with TimedLogger(logger, "price scraping"):
        asyncio.run(_run_scraping(region, platform, model, dry_run, max_workers))


async def _run_scraping(region: Optional[str], platform: Optional[str], 
                       model: Optional[str], dry_run: bool, max_workers: int):
    """Run the scraping process"""
    logger = get_logger(__name__)
    
    # Filter platforms based on parameters
    platforms_to_scrape = {}
    
    for region_name, region_platforms in PLATFORMS.items():
        if region and region_name != region:
            continue
        
        for platform_name, platform_config in region_platforms.items():
            if platform and platform_name.lower() != platform.lower():
                continue
            
            platform_config['region'] = region_name
            platforms_to_scrape[platform_name] = platform_config
    
    if not platforms_to_scrape:
        click.echo("❌ No platforms match the specified criteria")
        return
    
    # Filter models
    models_to_scrape = []
    for brand, models in PHONE_MODELS.items():
        for model_name, storage_options in models.items():
            if model and model.lower() not in model_name.lower():
                continue
            
            for storage in storage_options:
                models_to_scrape.append(f"{brand} {model_name} {storage}")
    
    click.echo(f"📱 Scraping {len(models_to_scrape)} phone models from {len(platforms_to_scrape)} platforms")
    
    # Create scrapers and run
    total_records = 0
    successful_records = 0
    
    for platform_name, platform_config in platforms_to_scrape.items():
        try:
            click.echo(f"\n🔍 Scraping {platform_name} ({platform_config['region']})...")
            
            scraper = ScraperFactory.create_scraper(platform_name, platform_config)
            price_data = await scraper.scrape_phone_prices(models_to_scrape)
            
            if price_data:
                click.echo(f"   Found {len(price_data)} price records")
                total_records += len(price_data)
                
                if not dry_run:
                    success = await _save_price_data(price_data)
                    if success:
                        successful_records += len(price_data)
                        click.echo(f"   ✅ Saved {len(price_data)} records")
                    else:
                        click.echo(f"   ❌ Failed to save records")
                else:
                    click.echo(f"   🔍 Dry run - would save {len(price_data)} records")
            else:
                click.echo(f"   ⚠️  No data found")
                
        except Exception as e:
            logger.error(f"Error scraping {platform_name}: {e}")
            click.echo(f"   ❌ Error: {e}")
    
    click.echo(f"\n📊 Scraping completed!")
    click.echo(f"   Total records found: {total_records}")
    if not dry_run:
        click.echo(f"   Successfully saved: {successful_records}")


async def _save_price_data(price_data: List[PriceData]) -> bool:
    """Save price data to database"""
    try:
        with db_manager.get_session() as session:
            # Convert PriceData objects to database records
            records = []
            
            for price_item in price_data:
                # Find phone model
                phone_model = session.query(db_manager.PhoneModel).filter_by(
                    brand=price_item.brand,
                    model_name=price_item.phone_model,
                    storage_capacity=price_item.storage
                ).first()
                
                # Find platform
                platform = session.query(db_manager.Platform).filter_by(
                    name=price_item.platform,
                    region=price_item.region
                ).first()
                
                if phone_model and platform:
                    # Convert to USD if needed
                    price_usd = price_item.price
                    if price_item.currency != 'USD':
                        converter = CurrencyConverter(session)
                        price_usd = converter.convert_to_usd(price_item.price, price_item.currency)
                    
                    record_data = {
                        'phone_model_id': phone_model.id,
                        'platform_id': platform.id,
                        'condition': price_item.condition,
                        'price': price_item.price,
                        'currency': price_item.currency,
                        'price_usd': price_usd,
                        'availability': price_item.availability,
                        'stock_count': price_item.stock_count,
                        'product_url': price_item.product_url
                    }
                    records.append(record_data)
            
            return db_manager.save_price_records(session, records)
            
    except Exception as e:
        logger.error(f"Error saving price data: {e}")
        return False


@cli.command()
@click.option('--days', default=30, help='Number of days to analyze')
@click.option('--output', type=click.Path(), help='Save analysis to file')
def analyze(days, output):
    """Analyze price trends and generate insights"""
    logger = get_logger(__name__)
    
    with TimedLogger(logger, "price analysis"):
        with db_manager.get_session() as session:
            analyzer = PriceAnalyzer(session)
            
            click.echo(f"📊 Analyzing price trends for the last {days} days...")
            
            # Get price analyses
            analyses = analyzer.analyze_price_trends(days_back=days)
            click.echo(f"   Found {len(analyses)} price analyses")
            
            # Get market insights
            insights = []
            insights.extend(analyzer.find_arbitrage_opportunities())
            insights.extend(analyzer.find_significant_price_changes())
            insights.extend(analyzer.find_best_deals())
            
            click.echo(f"   Generated {len(insights)} market insights")
            
            # Display top insights
            click.echo("\n🔍 Top Market Insights:")
            for i, insight in enumerate(insights[:5], 1):
                click.echo(f"   {i}. {insight.title}")
                click.echo(f"      {insight.description}")
            
            # Generate market summary
            summary = analyzer.generate_market_summary()
            click.echo(f"\n📈 Market Summary:")
            click.echo(f"   Total records: {summary['total_records']}")
            click.echo(f"   Recent records: {summary['recent_records']}")
            
            if output:
                # Save detailed analysis to file
                _save_analysis_to_file(output, analyses, insights, summary)
                click.echo(f"✅ Analysis saved to {output}")


def _save_analysis_to_file(file_path: str, analyses, insights, summary):
    """Save analysis results to a file"""
    import json
    from datetime import datetime
    
    data = {
        'generated_at': datetime.utcnow().isoformat(),
        'summary': summary,
        'analyses': [
            {
                'phone_model': a.phone_model,
                'brand': a.brand,
                'platform': a.platform,
                'region': a.region,
                'condition': a.condition,
                'current_price': a.current_price,
                'price_change_percent': a.price_change_percent,
                'trend_direction': a.trend_direction
            } for a in analyses
        ],
        'insights': [
            {
                'type': i.insight_type,
                'title': i.title,
                'description': i.description,
                'value': i.value,
                'confidence': i.confidence
            } for i in insights
        ]
    }
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


@cli.command()
@click.option('--recipient', multiple=True, help='Email recipients (can be used multiple times)')
@click.option('--subject', default='Weekly Smartphone Price Report', help='Email subject')
@click.option('--include-charts', is_flag=True, help='Include charts in the report')
@click.option('--save-html', type=click.Path(), help='Also save HTML report to file')
def report(recipient, subject, include_charts, save_html):
    """Generate and send email report"""
    logger = get_logger(__name__)
    
    with TimedLogger(logger, "report generation"):
        recipients = list(recipient) if recipient else settings.email_to
        
        if not recipients:
            click.echo("❌ No email recipients specified")
            return
        
        with db_manager.get_session() as session:
            # Generate analysis data
            analyzer = PriceAnalyzer(session)
            analyses = analyzer.analyze_price_trends()
            
            insights = []
            insights.extend(analyzer.find_arbitrage_opportunities())
            insights.extend(analyzer.find_significant_price_changes())
            insights.extend(analyzer.find_best_deals())
            
            summary = analyzer.generate_market_summary()
            
            # Generate charts if requested
            charts = {}
            if include_charts:
                click.echo("📊 Generating charts...")
                chart_generator = ChartGenerator(session)
                charts = chart_generator.generate_all_charts()
            
            # Create email reporter
            smtp_config = {
                'smtp_server': settings.smtp_server,
                'smtp_port': settings.smtp_port,
                'smtp_username': settings.smtp_username,
                'smtp_password': settings.smtp_password,
                'email_from': settings.email_from
            }
            
            reporter = EmailReporter(smtp_config)
            
            # Generate HTML report
            click.echo("📧 Generating HTML report...")
            html_content = reporter.generate_weekly_report(analyses, insights, summary, charts)
            
            # Save HTML file if requested
            if save_html:
                reporter.save_report_to_file(html_content, save_html)
                click.echo(f"💾 HTML report saved to {save_html}")
            
            # Send email
            click.echo(f"📨 Sending email to {len(recipients)} recipients...")
            success = reporter.send_email_report(recipients, subject, html_content)
            
            if success:
                click.echo("✅ Email report sent successfully!")
            else:
                click.echo("❌ Failed to send email report")


@cli.command()
@click.option('--start', is_flag=True, help='Start the scheduler daemon')
@click.option('--status', is_flag=True, help='Show scheduler status')
@click.option('--stop', is_flag=True, help='Stop the scheduler daemon')
def schedule(start, status, stop):
    """Manage the task scheduler"""
    logger = get_logger(__name__)
    
    if start:
        click.echo("🕒 Starting task scheduler...")
        
        scheduler = TaskScheduler()
        
        # Add weekly scraping task
        def weekly_scrape():
            click.echo("Running scheduled weekly scrape...")
            asyncio.run(_run_scraping(None, None, None, False, 5))
        
        # Add weekly report task  
        def weekly_report():
            click.echo("Sending scheduled weekly report...")
            # Implementation would call report generation
        
        scheduler.add_weekly_task(weekly_scrape, 'monday', '06:00')
        scheduler.add_weekly_task(weekly_report, 'monday', '08:00')
        
        scheduler.start()
        
        click.echo("✅ Scheduler started! Press Ctrl+C to stop.")
        
        try:
            while True:
                click.pause()
        except KeyboardInterrupt:
            click.echo("\n🛑 Stopping scheduler...")
            scheduler.stop()
    
    elif status:
        # Show next run times
        click.echo("📅 Scheduler status: (Implementation needed)")
    
    elif stop:
        click.echo("🛑 Stopping scheduler... (Implementation needed)")
    
    else:
        click.echo("Please specify --start, --status, or --stop")


@cli.command()
def status():
    """Show system status and statistics"""
    logger = get_logger(__name__)
    
    try:
        # Test database connection
        if db_manager.test_connection():
            click.echo("✅ Database: Connected")
        else:
            click.echo("❌ Database: Connection failed")
        
        with db_manager.get_session() as session:
            # Count records
            from src.database import PriceRecord, PhoneModel, Platform
            
            total_records = session.query(PriceRecord).count()
            total_models = session.query(PhoneModel).filter(PhoneModel.is_active == True).count()
            total_platforms = session.query(Platform).filter(Platform.is_active == True).count()
            
            recent_records = session.query(PriceRecord).filter(
                PriceRecord.scrape_timestamp >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            click.echo(f"📊 Statistics:")
            click.echo(f"   Total price records: {total_records:,}")
            click.echo(f"   Records this week: {recent_records:,}")
            click.echo(f"   Active phone models: {total_models}")
            click.echo(f"   Active platforms: {total_platforms}")
        
        # Test email configuration
        smtp_config = {
            'smtp_server': settings.smtp_server,
            'smtp_port': settings.smtp_port,
            'smtp_username': settings.smtp_username,
            'smtp_password': settings.smtp_password,
            'email_from': settings.email_from
        }
        
        if smtp_config['smtp_username'] and smtp_config['smtp_password']:
            reporter = EmailReporter(smtp_config)
            if reporter.test_email_connection():
                click.echo("✅ Email: Configuration valid")
            else:
                click.echo("❌ Email: Configuration invalid")
        else:
            click.echo("⚠️  Email: Not configured")
        
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        click.echo(f"❌ Error: {e}")


@cli.command()
@click.option('--sample-size', default=100, help='Number of sample records to create')
def demo(sample_size):
    """Generate demo data for testing"""
    click.echo(f"🎭 Generating {sample_size} sample records...")
    
    # This would create mock data for demonstration
    # Implementation would use MockScraper to generate realistic test data
    
    click.echo("✅ Demo data generated!")


if __name__ == '__main__':
    cli()