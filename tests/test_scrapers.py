import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.scrapers import BaseScraper, MockScraper, PriceData, ScraperFactory
from src.scrapers.swappa_scraper import SwappaScraper


class TestPriceData:
    """Test PriceData dataclass"""
    
    def test_price_data_creation(self):
        """Test creating PriceData instance"""
        data = PriceData(
            phone_model="iPhone 16",
            brand="Apple",
            storage="128GB",
            condition="Excellent",
            price=699.99,
            currency="USD",
            platform="Swappa",
            region="US"
        )
        
        assert data.phone_model == "iPhone 16"
        assert data.brand == "Apple"
        assert data.storage == "128GB"
        assert data.condition == "Excellent"
        assert data.price == 699.99
        assert data.currency == "USD"
        assert data.platform == "Swappa"
        assert data.region == "US"
        assert data.availability is True
        assert isinstance(data.scraped_at, datetime)
    
    def test_price_data_with_optional_fields(self):
        """Test PriceData with optional fields"""
        scraped_time = datetime.utcnow()
        
        data = PriceData(
            phone_model="Pixel 9",
            brand="Google",
            storage="256GB",
            condition="Good",
            price=549.99,
            currency="USD",
            platform="Back Market",
            region="US",
            availability=False,
            stock_count=5,
            product_url="https://example.com/product/123",
            scraped_at=scraped_time
        )
        
        assert data.availability is False
        assert data.stock_count == 5
        assert data.product_url == "https://example.com/product/123"
        assert data.scraped_at == scraped_time


class TestBaseScraper:
    """Test BaseScraper abstract class"""
    
    def test_base_scraper_initialization(self):
        """Test BaseScraper initialization"""
        config = {
            'name': 'Test Platform',
            'base_url': 'https://test.com',
            'region': 'US',
            'rate_limit': 2.0,
            'scraper_type': 'html'
        }
        
        scraper = MockScraper(config)  # Use MockScraper since BaseScraper is abstract
        
        assert scraper.platform_name == 'Test Platform'
        assert scraper.base_url == 'https://test.com'
        assert scraper.region == 'US'
        assert scraper.rate_limit == 2.0
        assert scraper.scraper_type == 'html'
    
    def test_parse_price_valid(self):
        """Test price parsing with valid input"""
        scraper = MockScraper({'name': 'Test', 'base_url': 'http://test.com', 'region': 'US'})
        
        assert scraper._parse_price('$599.99') == 599.99
        assert scraper._parse_price('€450.50') == 450.50
        assert scraper._parse_price('1,299.99') == 1299.99
        assert scraper._parse_price('$1,999') == 1999.0
    
    def test_parse_price_invalid(self):
        """Test price parsing with invalid input"""
        scraper = MockScraper({'name': 'Test', 'base_url': 'http://test.com', 'region': 'US'})
        
        assert scraper._parse_price('') is None
        assert scraper._parse_price('N/A') is None
        assert scraper._parse_price('invalid') is None
    
    def test_normalize_condition(self):
        """Test condition normalization"""
        scraper = MockScraper({'name': 'Test', 'base_url': 'http://test.com', 'region': 'US'})
        
        assert scraper._normalize_condition('Excellent') == 'Excellent'
        assert scraper._normalize_condition('mint condition') == 'Excellent'
        assert scraper._normalize_condition('like new') == 'Excellent'
        assert scraper._normalize_condition('very good') == 'Good'
        assert scraper._normalize_condition('fair condition') == 'Fair'
        assert scraper._normalize_condition('worn') == 'Fair'
        assert scraper._normalize_condition('unknown') == 'Good'  # Default
    
    def test_validate_price_data_valid(self):
        """Test price data validation with valid data"""
        scraper = MockScraper({'name': 'Test', 'base_url': 'http://test.com', 'region': 'US'})
        
        valid_data = PriceData(
            phone_model="iPhone 16",
            brand="Apple",
            storage="128GB",
            condition="Excellent",
            price=699.99,
            currency="USD",
            platform="Test",
            region="US"
        )
        
        assert scraper.validate_price_data(valid_data) is True
    
    def test_validate_price_data_invalid(self):
        """Test price data validation with invalid data"""
        scraper = MockScraper({'name': 'Test', 'base_url': 'http://test.com', 'region': 'US'})
        
        # Invalid price
        invalid_price_data = PriceData(
            phone_model="iPhone 16",
            brand="Apple",
            storage="128GB",
            condition="Excellent",
            price=0,  # Invalid price
            currency="USD",
            platform="Test",
            region="US"
        )
        
        assert scraper.validate_price_data(invalid_price_data) is False
        
        # Missing phone model
        invalid_model_data = PriceData(
            phone_model="",  # Invalid model
            brand="Apple",
            storage="128GB",
            condition="Excellent",
            price=699.99,
            currency="USD",
            platform="Test",
            region="US"
        )
        
        assert scraper.validate_price_data(invalid_model_data) is False


class TestMockScraper:
    """Test MockScraper implementation"""
    
    @pytest.mark.asyncio
    async def test_mock_scraper_generates_data(self):
        """Test that MockScraper generates realistic mock data"""
        config = {
            'name': 'Mock Platform',
            'base_url': 'https://mock.com',
            'region': 'US'
        }
        
        scraper = MockScraper(config)
        models = ['iPhone 16 128GB', 'Pixel 9 Pro 256GB']
        
        price_data = await scraper.scrape_phone_prices(models)
        
        assert len(price_data) > 0
        assert all(isinstance(item, PriceData) for item in price_data)
        assert all(item.price > 0 for item in price_data)
        assert all(item.currency == 'USD' for item in price_data)
        assert all(item.condition in ['Excellent', 'Good', 'Fair'] for item in price_data)
    
    @pytest.mark.asyncio
    async def test_mock_scraper_different_regions(self):
        """Test MockScraper with different regions"""
        regions = ['US', 'Europe', 'Japan', 'India']
        
        for region in regions:
            config = {
                'name': 'Mock Platform',
                'base_url': 'https://mock.com',
                'region': region
            }
            
            scraper = MockScraper(config)
            price_data = await scraper.scrape_phone_prices(['iPhone 16 128GB'])
            
            assert len(price_data) > 0
            assert all(item.region == region for item in price_data)
            
            # Check currency matches region
            expected_currency = {'US': 'USD', 'Europe': 'EUR', 'Japan': 'JPY', 'India': 'INR'}
            assert all(item.currency == expected_currency[region] for item in price_data)


class TestSwappaScraper:
    """Test SwappaScraper implementation"""
    
    def test_swappa_scraper_initialization(self):
        """Test SwappaScraper initialization"""
        config = {
            'name': 'Swappa',
            'base_url': 'https://swappa.com',
            'region': 'US',
            'rate_limit': 1.0
        }
        
        scraper = SwappaScraper(config)
        
        assert scraper.platform_name == 'Swappa'
        assert scraper.base_url == 'https://swappa.com'
        assert scraper.base_search_url == 'https://swappa.com/buy'
    
    def test_build_search_url_iphone(self):
        """Test building search URL for iPhone"""
        config = {'name': 'Swappa', 'base_url': 'https://swappa.com', 'region': 'US'}
        scraper = SwappaScraper(config)
        
        url = scraper.build_search_url('iPhone', '16 Pro', '256GB')
        assert 'apple-iphone-16-pro' in url.lower()
    
    def test_build_search_url_pixel(self):
        """Test building search URL for Pixel"""
        config = {'name': 'Swappa', 'base_url': 'https://swappa.com', 'region': 'US'}
        scraper = SwappaScraper(config)
        
        url = scraper.build_search_url('Google Pixel', '9', '128GB')
        assert 'google-pixel-9' in url.lower()
    
    def test_build_search_url_galaxy(self):
        """Test building search URL for Galaxy"""
        config = {'name': 'Swappa', 'base_url': 'https://swappa.com', 'region': 'US'}
        scraper = SwappaScraper(config)
        
        url = scraper.build_search_url('Samsung Galaxy', 'S24 Ultra', '512GB')
        assert 'samsung-galaxy-s24-ultra' in url.lower()
    
    def test_parse_model_info_iphone(self):
        """Test parsing iPhone model info"""
        config = {'name': 'Swappa', 'base_url': 'https://swappa.com', 'region': 'US'}
        scraper = SwappaScraper(config)
        
        brand, model, storage = scraper._parse_model_info('iPhone 16 Pro Max 1TB')
        assert brand == 'iPhone'
        assert model == '16 Pro Max'
        assert storage == '1TB'
    
    def test_parse_model_info_pixel(self):
        """Test parsing Pixel model info"""
        config = {'name': 'Swappa', 'base_url': 'https://swappa.com', 'region': 'US'}
        scraper = SwappaScraper(config)
        
        brand, model, storage = scraper._parse_model_info('Google Pixel 9 Pro 512GB')
        assert brand == 'Google Pixel'
        assert model == '9 Pro'
        assert storage == '512GB'
    
    def test_parse_model_info_galaxy(self):
        """Test parsing Galaxy model info"""
        config = {'name': 'Swappa', 'base_url': 'https://swappa.com', 'region': 'US'}
        scraper = SwappaScraper(config)
        
        brand, model, storage = scraper._parse_model_info('Samsung Galaxy S24 256GB')
        assert brand == 'Samsung Galaxy'
        assert model == 'S24'
        assert storage == '256GB'


class TestScraperFactory:
    """Test ScraperFactory"""
    
    def test_create_known_scraper(self):
        """Test creating a known scraper"""
        config = {
            'name': 'Swappa',
            'base_url': 'https://swappa.com',
            'region': 'US'
        }
        
        scraper = ScraperFactory.create_scraper('Swappa', config)
        assert isinstance(scraper, SwappaScraper)
    
    def test_create_unknown_scraper_fallback(self):
        """Test creating scraper for unknown platform falls back to MockScraper"""
        config = {
            'name': 'Unknown Platform',
            'base_url': 'https://unknown.com',
            'region': 'US'
        }
        
        scraper = ScraperFactory.create_scraper('Unknown Platform', config)
        assert isinstance(scraper, MockScraper)
    
    def test_get_available_platforms(self):
        """Test getting list of available platforms"""
        platforms = ScraperFactory.get_available_platforms()
        assert isinstance(platforms, list)
        assert 'Swappa' in platforms
        assert 'Back Market' in platforms
    
    def test_register_scraper(self):
        """Test registering a new scraper"""
        class CustomScraper(BaseScraper):
            async def scrape_phone_prices(self, phone_models):
                return []
            
            def build_search_url(self, brand, model, storage):
                return "https://custom.com/search"
        
        ScraperFactory.register_scraper('Custom Platform', CustomScraper)
        
        config = {'name': 'Custom Platform', 'base_url': 'https://custom.com', 'region': 'US'}
        scraper = ScraperFactory.create_scraper('Custom Platform', config)
        
        assert isinstance(scraper, CustomScraper)
    
    def test_register_invalid_scraper(self):
        """Test registering invalid scraper raises error"""
        class InvalidScraper:
            pass
        
        with pytest.raises(ValueError):
            ScraperFactory.register_scraper('Invalid', InvalidScraper)