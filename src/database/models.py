from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class PhoneModel(Base):
    __tablename__ = 'phone_models'
    
    id = Column(Integer, primary_key=True)
    brand = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    storage_capacity = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    prices = relationship("PriceRecord", back_populates="phone_model")
    
    # Indexes
    __table_args__ = (
        Index('idx_brand_model', 'brand', 'model_name'),
        Index('idx_active_models', 'is_active'),
    )
    
    def __repr__(self):
        return f"<PhoneModel(brand='{self.brand}', model='{self.model_name}', storage='{self.storage_capacity}')>"


class Platform(Base):
    __tablename__ = 'platforms'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    region = Column(String(50), nullable=False)
    base_url = Column(String(500), nullable=False)
    scraper_type = Column(String(20), nullable=False)  # 'html' or 'api'
    rate_limit = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    prices = relationship("PriceRecord", back_populates="platform")
    
    # Indexes
    __table_args__ = (
        Index('idx_region', 'region'),
        Index('idx_active_platforms', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Platform(name='{self.name}', region='{self.region}')>"


class PriceRecord(Base):
    __tablename__ = 'price_records'
    
    id = Column(Integer, primary_key=True)
    phone_model_id = Column(Integer, ForeignKey('phone_models.id'), nullable=False)
    platform_id = Column(Integer, ForeignKey('platforms.id'), nullable=False)
    condition = Column(String(20), nullable=False)  # Excellent, Good, Fair
    price = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    price_usd = Column(Float)  # Normalized price in USD
    availability = Column(Boolean, default=True)
    stock_count = Column(Integer)
    product_url = Column(Text)
    scrape_timestamp = Column(DateTime, default=datetime.utcnow)
    scrape_session_id = Column(String(36), default=lambda: str(uuid.uuid4()))
    
    # Relationships
    phone_model = relationship("PhoneModel", back_populates="prices")
    platform = relationship("Platform", back_populates="prices")
    
    # Indexes
    __table_args__ = (
        Index('idx_phone_platform', 'phone_model_id', 'platform_id'),
        Index('idx_scrape_timestamp', 'scrape_timestamp'),
        Index('idx_condition', 'condition'),
        Index('idx_session', 'scrape_session_id'),
        Index('idx_price_usd', 'price_usd'),
    )
    
    def __repr__(self):
        return f"<PriceRecord(phone={self.phone_model_id}, platform={self.platform_id}, price=${self.price} {self.currency})>"


class PriceTrend(Base):
    __tablename__ = 'price_trends'
    
    id = Column(Integer, primary_key=True)
    phone_model_id = Column(Integer, ForeignKey('phone_models.id'), nullable=False)
    platform_id = Column(Integer, ForeignKey('platforms.id'), nullable=False)
    condition = Column(String(20), nullable=False)
    
    # Trend metrics
    current_price_usd = Column(Float)
    previous_price_usd = Column(Float)
    price_change_amount = Column(Float)
    price_change_percent = Column(Float)
    
    # Time periods
    trend_period = Column(String(20), nullable=False)  # 'weekly', 'monthly'
    trend_date = Column(DateTime, default=datetime.utcnow)
    
    # Statistical metrics
    avg_price = Column(Float)
    min_price = Column(Float)
    max_price = Column(Float)
    volatility = Column(Float)  # Standard deviation
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    phone_model = relationship("PhoneModel")
    platform = relationship("Platform")
    
    # Indexes
    __table_args__ = (
        Index('idx_trend_phone_platform', 'phone_model_id', 'platform_id'),
        Index('idx_trend_date', 'trend_date'),
        Index('idx_trend_period', 'trend_period'),
    )
    
    def __repr__(self):
        return f"<PriceTrend(phone={self.phone_model_id}, change={self.price_change_percent}%)>"


class ScrapingSession(Base):
    __tablename__ = 'scraping_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String(20), default='running')  # running, completed, failed
    total_records = Column(Integer, default=0)
    successful_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    error_log = Column(Text)
    
    # Indexes
    __table_args__ = (
        Index('idx_session_status', 'status'),
        Index('idx_session_start', 'start_time'),
    )
    
    def __repr__(self):
        return f"<ScrapingSession(id='{self.session_id}', status='{self.status}')>"


class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'
    
    id = Column(Integer, primary_key=True)
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False, default='USD')
    rate = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50), default='api')
    
    # Indexes
    __table_args__ = (
        Index('idx_currency_pair', 'from_currency', 'to_currency'),
        Index('idx_rate_date', 'date'),
    )
    
    def __repr__(self):
        return f"<ExchangeRate({self.from_currency}/{self.to_currency}={self.rate})>"