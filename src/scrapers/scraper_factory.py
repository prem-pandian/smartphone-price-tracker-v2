from typing import Dict, List, Type
import logging
from .base_scraper import BaseScraper, MockScraper
from .swappa_scraper import SwappaScraper, BackMarketScraper

logger = logging.getLogger(__name__)


class ScraperFactory:
    """Factory class to create appropriate scrapers for different platforms"""
    
    _scraper_classes: Dict[str, Type[BaseScraper]] = {
        'Swappa': SwappaScraper,
        'Back Market': BackMarketScraper,
        'Back Market EU': BackMarketScraper,
        'Gazelle': MockScraper,  # Using mock for now
        'eBay Refurbished': MockScraper,  # Using mock for now
        'Refurbed': MockScraper,
        'Rebuy': MockScraper,
        'Mercari': MockScraper,
        'Yahoo Auctions': MockScraper,
        'Sofmap': MockScraper,
        'Cashify': MockScraper,
        'ShopClues': MockScraper,
        'OLX': MockScraper,
    }
    
    @classmethod
    def create_scraper(cls, platform_name: str, platform_config: dict, 
                      proxy_list: List[str] = None) -> BaseScraper:
        """Create a scraper instance for the given platform"""
        
        scraper_class = cls._scraper_classes.get(platform_name)
        
        if not scraper_class:
            logger.warning(f"No specific scraper found for {platform_name}, using MockScraper")
            scraper_class = MockScraper
        
        try:
            config_with_name = {**platform_config, 'name': platform_name}
            scraper = scraper_class(config_with_name, proxy_list)
            logger.info(f"Created scraper for {platform_name}")
            return scraper
            
        except Exception as e:
            logger.error(f"Failed to create scraper for {platform_name}: {e}")
            # Fallback to MockScraper
            config_with_name = {**platform_config, 'name': platform_name}
            return MockScraper(config_with_name, proxy_list)
    
    @classmethod
    def get_available_platforms(cls) -> List[str]:
        """Get list of supported platform names"""
        return list(cls._scraper_classes.keys())
    
    @classmethod
    def register_scraper(cls, platform_name: str, scraper_class: Type[BaseScraper]):
        """Register a new scraper class for a platform"""
        if not issubclass(scraper_class, BaseScraper):
            raise ValueError(f"Scraper class must inherit from BaseScraper")
        
        cls._scraper_classes[platform_name] = scraper_class
        logger.info(f"Registered scraper for {platform_name}")


# Additional scraper implementations for other platforms
class GazelleScraper(BaseScraper):
    """Scraper for Gazelle - US phone trade-in service"""
    
    async def scrape_phone_prices(self, phone_models: List[str]) -> List[PriceData]:
        # Implementation would go here
        # For now, using mock data
        mock_scraper = MockScraper(
            {'name': self.platform_name, 'base_url': self.base_url, 'region': self.region}
        )
        return await mock_scraper.scrape_phone_prices(phone_models)
    
    def build_search_url(self, brand: str, model: str, storage: str) -> str:
        return f"{self.base_url}/sell/{brand.lower()}/{model.lower().replace(' ', '-')}"


class EbayScraper(BaseScraper):
    """Scraper for eBay Refurbished section"""
    
    def __init__(self, platform_config: dict, proxy_list: List[str] = None):
        super().__init__(platform_config, proxy_list)
        self.api_key = platform_config.get('api_key')
    
    async def scrape_phone_prices(self, phone_models: List[str]) -> List[PriceData]:
        # Would implement eBay API integration
        mock_scraper = MockScraper(
            {'name': self.platform_name, 'base_url': self.base_url, 'region': self.region}
        )
        return await mock_scraper.scrape_phone_prices(phone_models)
    
    def build_search_url(self, brand: str, model: str, storage: str) -> str:
        query = f"{brand} {model} {storage} refurbished".replace(' ', '%20')
        return f"{self.base_url}/sch/i.html?_nkw={query}"


class RefurbedScraper(BaseScraper):
    """Scraper for Refurbed - European refurbished electronics marketplace"""
    
    async def scrape_phone_prices(self, phone_models: List[str]) -> List[PriceData]:
        mock_scraper = MockScraper(
            {'name': self.platform_name, 'base_url': self.base_url, 'region': self.region}
        )
        return await mock_scraper.scrape_phone_prices(phone_models)
    
    def build_search_url(self, brand: str, model: str, storage: str) -> str:
        query = f"{brand}-{model}".lower().replace(' ', '-')
        return f"{self.base_url}/products/{query}"


class MercariScraper(BaseScraper):
    """Scraper for Mercari - Japanese marketplace"""
    
    async def scrape_phone_prices(self, phone_models: List[str]) -> List[PriceData]:
        mock_scraper = MockScraper(
            {'name': self.platform_name, 'base_url': self.base_url, 'region': self.region}
        )
        return await mock_scraper.scrape_phone_prices(phone_models)
    
    def build_search_url(self, brand: str, model: str, storage: str) -> str:
        query = f"{brand} {model}".replace(' ', '%20')
        return f"{self.base_url}/search?keyword={query}"


class CashifyScraper(BaseScraper):
    """Scraper for Cashify - Indian phone trade-in service"""
    
    async def scrape_phone_prices(self, phone_models: List[str]) -> List[PriceData]:
        mock_scraper = MockScraper(
            {'name': self.platform_name, 'base_url': self.base_url, 'region': self.region}
        )
        return await mock_scraper.scrape_phone_prices(phone_models)
    
    def build_search_url(self, brand: str, model: str, storage: str) -> str:
        brand_clean = brand.lower().replace(' ', '-')
        model_clean = model.lower().replace(' ', '-')
        return f"{self.base_url}/sell-old-{brand_clean}-{model_clean}"


# Register additional scrapers
ScraperFactory.register_scraper('Gazelle', GazelleScraper)
ScraperFactory.register_scraper('eBay Refurbished', EbayScraper)
ScraperFactory.register_scraper('Refurbed', RefurbedScraper)
ScraperFactory.register_scraper('Mercari', MercariScraper)
ScraperFactory.register_scraper('Cashify', CashifyScraper)