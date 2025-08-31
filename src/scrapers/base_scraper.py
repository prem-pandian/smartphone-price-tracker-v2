from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
import random
import requests
from fake_useragent import UserAgent
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    phone_model: str
    brand: str
    storage: str
    condition: str
    price: float
    currency: str
    platform: str
    region: str
    availability: bool = True
    stock_count: Optional[int] = None
    product_url: Optional[str] = None
    scraped_at: datetime = None
    
    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.utcnow()


class BaseScraper(ABC):
    def __init__(self, platform_config: Dict[str, Any], proxy_list: List[str] = None):
        self.platform_name = platform_config.get('name', '')
        self.base_url = platform_config.get('base_url', '')
        self.region = platform_config.get('region', '')
        self.rate_limit = platform_config.get('rate_limit', 1.0)
        self.scraper_type = platform_config.get('scraper_type', 'html')
        self.proxy_list = proxy_list or []
        
        self.user_agent = UserAgent()
        self.session = requests.Session()
        self.last_request_time = 0
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': self.user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """Get a random proxy from the proxy list"""
        if not self.proxy_list:
            return None
        
        proxy = random.choice(self.proxy_list)
        return {
            'http': f'http://{proxy}',
            'https': f'https://{proxy}'
        }
    
    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make a request with rate limiting and error handling"""
        self._wait_for_rate_limit()
        
        # Rotate user agent occasionally
        if random.random() < 0.1:  # 10% chance
            self.session.headers['User-Agent'] = self.user_agent.random
        
        try:
            # Use proxy if available
            if self.proxy_list and random.random() < 0.3:  # 30% chance to use proxy
                kwargs['proxies'] = self._get_proxy()
            
            kwargs.setdefault('timeout', 30)
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            
            logger.debug(f"Successfully scraped {url}")
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price text and extract numeric value"""
        if not price_text:
            return None
        
        # Remove common currency symbols and text
        import re
        price_text = re.sub(r'[^\d.,]', '', price_text.replace(',', ''))
        
        try:
            return float(price_text)
        except ValueError:
            logger.warning(f"Could not parse price: {price_text}")
            return None
    
    def _normalize_condition(self, condition_text: str) -> str:
        """Normalize condition text to standard values"""
        if not condition_text:
            return "Unknown"
        
        condition_lower = condition_text.lower()
        
        if any(word in condition_lower for word in ['excellent', 'mint', 'like new', 'pristine']):
            return "Excellent"
        elif any(word in condition_lower for word in ['good', 'very good', 'fine']):
            return "Good"
        elif any(word in condition_lower for word in ['fair', 'acceptable', 'worn']):
            return "Fair"
        else:
            return "Good"  # Default fallback
    
    @abstractmethod
    async def scrape_phone_prices(self, phone_models: List[str]) -> List[PriceData]:
        """Scrape prices for given phone models. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def build_search_url(self, brand: str, model: str, storage: str) -> str:
        """Build search URL for a specific phone model. Must be implemented by subclasses."""
        pass
    
    def validate_price_data(self, price_data: PriceData) -> bool:
        """Validate scraped price data"""
        if not price_data.price or price_data.price <= 0:
            return False
        
        if not price_data.phone_model or not price_data.brand:
            return False
        
        if price_data.condition not in ['Excellent', 'Good', 'Fair']:
            return False
        
        return True
    
    def get_currency_for_region(self) -> str:
        """Get currency code for the platform's region"""
        currency_map = {
            'US': 'USD',
            'Europe': 'EUR',
            'Japan': 'JPY',
            'India': 'INR'
        }
        return currency_map.get(self.region, 'USD')


class MockScraper(BaseScraper):
    """Mock scraper for testing purposes with sample data"""
    
    async def scrape_phone_prices(self, phone_models: List[str]) -> List[PriceData]:
        """Generate mock price data for testing"""
        mock_data = []
        
        for model_info in phone_models:
            brand, model, storage = model_info.split(' ', 2) if ' ' in model_info else (model_info, model_info, '128GB')
            
            # Generate mock prices for different conditions
            base_price = self._get_mock_base_price(brand, model)
            currency = self.get_currency_for_region()
            
            for condition in ['Excellent', 'Good', 'Fair']:
                price_multiplier = {'Excellent': 0.95, 'Good': 0.85, 'Fair': 0.7}[condition]
                price = base_price * price_multiplier
                
                # Add some random variance
                price *= random.uniform(0.9, 1.1)
                
                mock_data.append(PriceData(
                    phone_model=model,
                    brand=brand,
                    storage=storage,
                    condition=condition,
                    price=round(price, 2),
                    currency=currency,
                    platform=self.platform_name,
                    region=self.region,
                    availability=random.choice([True, True, True, False]),  # 75% availability
                    stock_count=random.randint(1, 10) if random.random() > 0.3 else None,
                    product_url=f"{self.base_url}/product/{model.lower().replace(' ', '-')}"
                ))
        
        # Simulate some delay
        await asyncio.sleep(random.uniform(1, 3))
        
        return mock_data
    
    def _get_mock_base_price(self, brand: str, model: str) -> float:
        """Generate realistic mock base prices"""
        price_ranges = {
            'iPhone': {'16': 800, '16 Plus': 900, '16 Pro': 1000, '16 Pro Max': 1200},
            'Pixel': {'9': 600, '9 Pro': 900, '9 Pro XL': 1000, '9 Pro Fold': 1600},
            'Galaxy': {'S24': 700, 'S24+': 900, 'S24 Ultra': 1100, 'Z Fold6': 1700}
        }
        
        brand_key = brand.replace('Samsung ', '').replace('Google ', '')
        model_key = model.replace('iPhone ', '').replace('Pixel ', '').replace('Galaxy ', '')
        
        base_price = price_ranges.get(brand_key, {}).get(model_key, 600)
        
        # Convert to local currency if needed
        if self.region == 'Europe':
            base_price *= 0.85  # EUR is typically lower numerically
        elif self.region == 'Japan':
            base_price *= 110  # Convert to JPY
        elif self.region == 'India':
            base_price *= 75   # Convert to INR
        
        return base_price
    
    def build_search_url(self, brand: str, model: str, storage: str) -> str:
        return f"{self.base_url}/search?q={brand}+{model}+{storage}"


# Import asyncio at the end to avoid circular imports
import asyncio