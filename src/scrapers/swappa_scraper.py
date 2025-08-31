from typing import List, Optional
from bs4 import BeautifulSoup
import re
import asyncio
import logging
from .base_scraper import BaseScraper, PriceData

logger = logging.getLogger(__name__)


class SwappaScraper(BaseScraper):
    """Scraper for Swappa.com - US marketplace for used phones"""
    
    def __init__(self, platform_config: dict, proxy_list: List[str] = None):
        super().__init__(platform_config, proxy_list)
        self.base_search_url = f"{self.base_url}/buy"
    
    async def scrape_phone_prices(self, phone_models: List[str]) -> List[PriceData]:
        """Scrape prices for phone models from Swappa"""
        all_price_data = []
        
        for model_info in phone_models:
            try:
                # Parse model info
                brand, model, storage = self._parse_model_info(model_info)
                logger.info(f"Scraping Swappa for {brand} {model} {storage}")
                
                # Build search URL
                search_url = self.build_search_url(brand, model, storage)
                
                # Make request
                response = self._make_request(search_url)
                if not response:
                    logger.warning(f"Failed to fetch {search_url}")
                    continue
                
                # Parse prices
                prices = self._parse_price_listings(response.text, brand, model, storage)
                all_price_data.extend(prices)
                
                # Small delay between requests
                await asyncio.sleep(self.rate_limit)
                
            except Exception as e:
                logger.error(f"Error scraping {model_info} from Swappa: {e}")
                continue
        
        return all_price_data
    
    def build_search_url(self, brand: str, model: str, storage: str) -> str:
        """Build Swappa search URL"""
        # Swappa uses specific URL patterns
        brand_lower = brand.lower().replace(' ', '-')
        model_lower = model.lower().replace(' ', '-').replace('+', '-plus')
        
        if 'iphone' in brand_lower:
            model_clean = model_lower.replace('iphone-', '')
            return f"{self.base_search_url}/apple-iphone-{model_clean}"
        elif 'pixel' in brand_lower or 'google' in brand_lower:
            model_clean = model_lower.replace('pixel-', '')
            return f"{self.base_search_url}/google-pixel-{model_clean}"
        elif 'galaxy' in brand_lower or 'samsung' in brand_lower:
            model_clean = model_lower.replace('galaxy-', '')
            return f"{self.base_search_url}/samsung-galaxy-{model_clean}"
        else:
            # Fallback to generic search
            query = f"{brand} {model}".replace(' ', '+')
            return f"{self.base_url}/search?q={query}"
    
    def _parse_model_info(self, model_info: str) -> tuple:
        """Parse model info string into brand, model, storage"""
        parts = model_info.split()
        
        if 'iPhone' in model_info:
            brand = 'iPhone'
            model_parts = []
            storage = '128GB'  # default
            
            for part in parts:
                if 'GB' in part or 'TB' in part:
                    storage = part
                elif part not in ['iPhone']:
                    model_parts.append(part)
            
            model = ' '.join(model_parts) if model_parts else parts[-1]
            
        elif 'Pixel' in model_info:
            brand = 'Google Pixel'
            model_parts = []
            storage = '128GB'
            
            for part in parts:
                if 'GB' in part or 'TB' in part:
                    storage = part
                elif part not in ['Google', 'Pixel']:
                    model_parts.append(part)
            
            model = ' '.join(model_parts) if model_parts else parts[-1]
            
        elif 'Galaxy' in model_info:
            brand = 'Samsung Galaxy'
            model_parts = []
            storage = '128GB'
            
            for part in parts:
                if 'GB' in part or 'TB' in part:
                    storage = part
                elif part not in ['Samsung', 'Galaxy']:
                    model_parts.append(part)
            
            model = ' '.join(model_parts) if model_parts else parts[-1]
            
        else:
            # Generic parsing
            brand = parts[0] if parts else 'Unknown'
            model = ' '.join(parts[1:-1]) if len(parts) > 2 else parts[1] if len(parts) > 1 else 'Unknown'
            storage = parts[-1] if parts and ('GB' in parts[-1] or 'TB' in parts[-1]) else '128GB'
        
        return brand, model, storage
    
    def _parse_price_listings(self, html: str, brand: str, model: str, storage: str) -> List[PriceData]:
        """Parse price listings from Swappa HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        price_data = []
        
        # Find listing containers (Swappa-specific selectors)
        listings = soup.find_all('div', class_=['listing_row', 'listing-item', 'phone-listing'])
        
        if not listings:
            # Try alternative selectors
            listings = soup.find_all('div', {'data-testid': 'listing-card'})
        
        if not listings:
            # Try more generic approach
            listings = soup.find_all('div', class_=re.compile(r'listing|item|card'))
        
        logger.info(f"Found {len(listings)} potential listings on Swappa")
        
        for listing in listings[:20]:  # Limit to first 20 listings
            try:
                price_data_item = self._extract_listing_data(listing, brand, model, storage)
                if price_data_item and self.validate_price_data(price_data_item):
                    price_data.append(price_data_item)
            except Exception as e:
                logger.debug(f"Error parsing individual listing: {e}")
                continue
        
        return price_data
    
    def _extract_listing_data(self, listing_element, brand: str, model: str, storage: str) -> Optional[PriceData]:
        """Extract price data from a single listing element"""
        # Try to find price
        price_element = listing_element.find(['span', 'div'], class_=re.compile(r'price|cost|amount'))
        if not price_element:
            price_element = listing_element.find(text=re.compile(r'\$\d+'))
            if price_element:
                price_element = price_element.parent
        
        if not price_element:
            return None
        
        price_text = price_element.get_text().strip()
        price = self._parse_price(price_text)
        if not price:
            return None
        
        # Try to find condition
        condition_element = listing_element.find(['span', 'div'], class_=re.compile(r'condition|grade|state'))
        condition_text = condition_element.get_text().strip() if condition_element else 'Good'
        condition = self._normalize_condition(condition_text)
        
        # Try to find product URL
        link_element = listing_element.find('a', href=True)
        product_url = None
        if link_element:
            href = link_element['href']
            if href.startswith('/'):
                product_url = f"{self.base_url}{href}"
            elif href.startswith('http'):
                product_url = href
        
        # Check availability (not sold)
        is_sold = listing_element.find(text=re.compile(r'sold|unavailable', re.I)) is not None
        availability = not is_sold
        
        return PriceData(
            phone_model=model,
            brand=brand,
            storage=storage,
            condition=condition,
            price=price,
            currency='USD',
            platform=self.platform_name,
            region=self.region,
            availability=availability,
            product_url=product_url
        )


class BackMarketScraper(BaseScraper):
    """Scraper for Back Market - focuses on refurbished devices"""
    
    def __init__(self, platform_config: dict, proxy_list: List[str] = None):
        super().__init__(platform_config, proxy_list)
        # Back Market has an API, but we'll use web scraping as fallback
        self.api_key = platform_config.get('api_key')
    
    async def scrape_phone_prices(self, phone_models: List[str]) -> List[PriceData]:
        """Scrape prices from Back Market"""
        all_price_data = []
        
        # If API key is available, use API approach
        if self.api_key:
            return await self._scrape_via_api(phone_models)
        
        # Otherwise use web scraping
        for model_info in phone_models:
            try:
                brand, model, storage = self._parse_model_info(model_info)
                logger.info(f"Scraping Back Market for {brand} {model} {storage}")
                
                search_url = self.build_search_url(brand, model, storage)
                response = self._make_request(search_url)
                
                if response:
                    prices = self._parse_back_market_listings(response.text, brand, model, storage)
                    all_price_data.extend(prices)
                
                await asyncio.sleep(self.rate_limit)
                
            except Exception as e:
                logger.error(f"Error scraping {model_info} from Back Market: {e}")
                continue
        
        return all_price_data
    
    def build_search_url(self, brand: str, model: str, storage: str) -> str:
        """Build Back Market search URL"""
        query = f"{brand} {model}".replace(' ', '%20')
        return f"{self.base_url}/search?q={query}"
    
    def _parse_model_info(self, model_info: str) -> tuple:
        """Parse model info - similar to Swappa but simpler"""
        parts = model_info.split()
        
        # Extract brand
        if 'iPhone' in model_info:
            brand = 'Apple'
        elif 'Pixel' in model_info:
            brand = 'Google'
        elif 'Galaxy' in model_info:
            brand = 'Samsung'
        else:
            brand = parts[0] if parts else 'Unknown'
        
        # Extract model and storage
        model_parts = []
        storage = '128GB'
        
        for part in parts:
            if 'GB' in part or 'TB' in part:
                storage = part
            elif part.lower() not in ['google', 'apple', 'samsung']:
                model_parts.append(part)
        
        model = ' '.join(model_parts) if model_parts else 'Unknown'
        return brand, model, storage
    
    def _parse_back_market_listings(self, html: str, brand: str, model: str, storage: str) -> List[PriceData]:
        """Parse Back Market listings"""
        soup = BeautifulSoup(html, 'html.parser')
        price_data = []
        
        # Back Market specific selectors
        listings = soup.find_all('div', class_=['product-card', 'product-item'])
        
        if not listings:
            listings = soup.find_all('article', class_=re.compile(r'product|item'))
        
        for listing in listings[:15]:
            try:
                # Extract price
                price_element = listing.find(['span', 'div'], class_=re.compile(r'price'))
                if not price_element:
                    continue
                
                price = self._parse_price(price_element.get_text())
                if not price:
                    continue
                
                # Extract condition (Back Market uses grade system)
                condition_element = listing.find(['span', 'div'], class_=re.compile(r'grade|condition'))
                if condition_element:
                    condition_text = condition_element.get_text().strip()
                    # Back Market uses grades like "Excellent", "Very Good", "Good"
                    condition = self._normalize_back_market_condition(condition_text)
                else:
                    condition = 'Good'
                
                # Extract product URL
                link = listing.find('a', href=True)
                product_url = link['href'] if link else None
                if product_url and product_url.startswith('/'):
                    product_url = f"{self.base_url}{product_url}"
                
                currency = 'EUR' if 'europe' in self.region.lower() or '.co.uk' in self.base_url else 'USD'
                
                price_data.append(PriceData(
                    phone_model=model,
                    brand=brand,
                    storage=storage,
                    condition=condition,
                    price=price,
                    currency=currency,
                    platform=self.platform_name,
                    region=self.region,
                    availability=True,  # Back Market usually shows available items
                    product_url=product_url
                ))
                
            except Exception as e:
                logger.debug(f"Error parsing Back Market listing: {e}")
                continue
        
        return price_data
    
    def _normalize_back_market_condition(self, condition_text: str) -> str:
        """Normalize Back Market specific condition grades"""
        condition_lower = condition_text.lower()
        
        if 'excellent' in condition_lower or 'pristine' in condition_lower:
            return 'Excellent'
        elif 'very good' in condition_lower or 'good' in condition_lower:
            return 'Good'
        elif 'fair' in condition_lower or 'correct' in condition_lower:
            return 'Fair'
        else:
            return 'Good'
    
    async def _scrape_via_api(self, phone_models: List[str]) -> List[PriceData]:
        """Use Back Market API if available"""
        # This would implement API-based scraping
        # For now, return empty list as API implementation would need actual API docs
        logger.info("API-based scraping not implemented yet for Back Market")
        return []