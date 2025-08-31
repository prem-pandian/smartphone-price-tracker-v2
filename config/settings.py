from typing import List, Dict, Any
from pydantic import BaseSettings, validator
import os


class Settings(BaseSettings):
    database_url: str = "sqlite:///./price_tracker.db"
    
    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""
    
    # API Keys
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    back_market_api_key: str = ""
    
    # Scraping settings
    scraping_delay: int = 2
    max_retries: int = 3
    timeout: int = 30
    use_proxy: bool = False
    proxy_list: str = ""
    
    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/price_tracker.log"
    
    # Application settings
    default_currency: str = "USD"
    price_change_threshold: float = 5.0
    max_price_records_per_model: int = 1000
    
    @validator('email_to')
    def split_email_to(cls, v):
        return [email.strip() for email in v.split(',') if email.strip()]
    
    @validator('proxy_list')
    def split_proxy_list(cls, v):
        if not v:
            return []
        return [proxy.strip() for proxy in v.split(',') if proxy.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Phone models configuration
PHONE_MODELS = {
    "pixel": {
        "Pixel 9": ["128GB", "256GB"],
        "Pixel 9 Pro": ["128GB", "256GB", "512GB", "1TB"],
        "Pixel 9 Pro XL": ["128GB", "256GB", "512GB", "1TB"],
        "Pixel 9 Pro Fold": ["256GB", "512GB"]
    },
    "iphone": {
        "iPhone 16": ["128GB", "256GB", "512GB"],
        "iPhone 16 Plus": ["128GB", "256GB", "512GB"],
        "iPhone 16 Pro": ["128GB", "256GB", "512GB", "1TB"],
        "iPhone 16 Pro Max": ["256GB", "512GB", "1TB"]
    },
    "samsung": {
        "Galaxy S24": ["128GB", "256GB", "512GB"],
        "Galaxy S24+": ["256GB", "512GB"],
        "Galaxy S24 Ultra": ["256GB", "512GB", "1TB"],
        "Galaxy Z Fold6": ["256GB", "512GB", "1TB"]
    }
}

# Platform configuration
PLATFORMS = {
    "US": {
        "Swappa": {
            "base_url": "https://swappa.com",
            "scraper_type": "html",
            "rate_limit": 1
        },
        "Back Market": {
            "base_url": "https://www.backmarket.com",
            "scraper_type": "api",
            "rate_limit": 0.5
        },
        "Gazelle": {
            "base_url": "https://www.gazelle.com",
            "scraper_type": "html",
            "rate_limit": 2
        },
        "eBay Refurbished": {
            "base_url": "https://www.ebay.com",
            "scraper_type": "api",
            "rate_limit": 0.5
        }
    },
    "Europe": {
        "Back Market EU": {
            "base_url": "https://www.backmarket.co.uk",
            "scraper_type": "api",
            "rate_limit": 0.5
        },
        "Refurbed": {
            "base_url": "https://www.refurbed.com",
            "scraper_type": "html",
            "rate_limit": 1
        },
        "Rebuy": {
            "base_url": "https://www.rebuy.de",
            "scraper_type": "html",
            "rate_limit": 1
        }
    },
    "Japan": {
        "Mercari": {
            "base_url": "https://mercari.com",
            "scraper_type": "html",
            "rate_limit": 2
        },
        "Yahoo Auctions": {
            "base_url": "https://auctions.yahoo.co.jp",
            "scraper_type": "html",
            "rate_limit": 2
        },
        "Sofmap": {
            "base_url": "https://www.sofmap.com",
            "scraper_type": "html",
            "rate_limit": 1
        }
    },
    "India": {
        "Cashify": {
            "base_url": "https://www.cashify.in",
            "scraper_type": "html",
            "rate_limit": 1
        },
        "ShopClues": {
            "base_url": "https://www.shopclues.com",
            "scraper_type": "html",
            "rate_limit": 1
        },
        "OLX": {
            "base_url": "https://www.olx.in",
            "scraper_type": "html",
            "rate_limit": 2
        }
    }
}

# Currency configuration
CURRENCIES = {
    "US": "USD",
    "Europe": "EUR", 
    "Japan": "JPY",
    "India": "INR"
}

# Condition mapping
CONDITIONS = ["Excellent", "Good", "Fair"]

settings = Settings()