from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import logging
from config.settings import settings
from .models import Base, PhoneModel, Platform, PriceRecord, PriceTrend, ScrapingSession, ExchangeRate

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_url
        
        # Configure engine based on database type
        if "sqlite" in self.database_url:
            self.engine = create_engine(
                self.database_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=False
            )
        else:
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables in the database"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all tables in the database"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def init_default_data(self):
        """Initialize database with default phone models and platforms"""
        from config.settings import PHONE_MODELS, PLATFORMS, CURRENCIES
        
        with self.get_session() as session:
            # Initialize phone models
            for brand, models in PHONE_MODELS.items():
                for model_name, storage_options in models.items():
                    for storage in storage_options:
                        existing = session.query(PhoneModel).filter_by(
                            brand=brand.title(),
                            model_name=model_name,
                            storage_capacity=storage
                        ).first()
                        
                        if not existing:
                            phone_model = PhoneModel(
                                brand=brand.title(),
                                model_name=model_name,
                                storage_capacity=storage
                            )
                            session.add(phone_model)
                            logger.info(f"Added phone model: {brand.title()} {model_name} {storage}")
            
            # Initialize platforms
            for region, platforms in PLATFORMS.items():
                for platform_name, config in platforms.items():
                    existing = session.query(Platform).filter_by(
                        name=platform_name,
                        region=region
                    ).first()
                    
                    if not existing:
                        platform = Platform(
                            name=platform_name,
                            region=region,
                            base_url=config["base_url"],
                            scraper_type=config["scraper_type"],
                            rate_limit=config["rate_limit"]
                        )
                        session.add(platform)
                        logger.info(f"Added platform: {platform_name} ({region})")
            
            session.commit()
            logger.info("Default data initialization completed")
    
    def get_phone_models(self, session: Session, active_only: bool = True):
        """Get all phone models"""
        query = session.query(PhoneModel)
        if active_only:
            query = query.filter(PhoneModel.is_active == True)
        return query.all()
    
    def get_platforms(self, session: Session, region: str = None, active_only: bool = True):
        """Get platforms, optionally filtered by region"""
        query = session.query(Platform)
        if active_only:
            query = query.filter(Platform.is_active == True)
        if region:
            query = query.filter(Platform.region == region)
        return query.all()
    
    def save_price_records(self, session: Session, price_records: list, session_id: str = None):
        """Save multiple price records efficiently"""
        try:
            for record_data in price_records:
                if session_id:
                    record_data['scrape_session_id'] = session_id
                
                price_record = PriceRecord(**record_data)
                session.add(price_record)
            
            session.commit()
            logger.info(f"Saved {len(price_records)} price records")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving price records: {e}")
            return False
    
    def get_latest_prices(self, session: Session, phone_model_id: int = None, platform_id: int = None):
        """Get latest prices with optional filters"""
        query = session.query(PriceRecord).order_by(PriceRecord.scrape_timestamp.desc())
        
        if phone_model_id:
            query = query.filter(PriceRecord.phone_model_id == phone_model_id)
        if platform_id:
            query = query.filter(PriceRecord.platform_id == platform_id)
        
        return query.all()
    
    def cleanup_old_records(self, session: Session, keep_days: int = 90):
        """Clean up old price records to prevent database bloat"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        
        deleted_count = session.query(PriceRecord).filter(
            PriceRecord.scrape_timestamp < cutoff_date
        ).delete()
        
        session.commit()
        logger.info(f"Cleaned up {deleted_count} old price records")
        return deleted_count
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


def get_db_session():
    """Dependency function for getting database sessions"""
    return db_manager.get_session()


def init_database():
    """Initialize the database with tables and default data"""
    db_manager.create_tables()
    db_manager.init_default_data()