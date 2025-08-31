import requests
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..database import ExchangeRate

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """Handles currency conversion for price normalization"""
    
    def __init__(self, db_session: Session, api_key: Optional[str] = None):
        self.db_session = db_session
        self.api_key = api_key
        self.base_currency = 'USD'
        self.cache_duration_hours = 24
        
        # Fallback exchange rates (updated periodically)
        self.fallback_rates = {
            'USD': 1.0,
            'EUR': 0.85,
            'GBP': 0.73,
            'JPY': 110.0,
            'INR': 75.0,
            'CAD': 1.25,
            'AUD': 1.35
        }
    
    def convert_to_usd(self, amount: float, from_currency: str) -> Optional[float]:
        """Convert amount from source currency to USD"""
        if from_currency == 'USD':
            return amount
        
        rate = self.get_exchange_rate(from_currency, 'USD')
        if rate:
            return amount / rate
        
        return None
    
    def get_exchange_rate(self, from_currency: str, to_currency: str = 'USD') -> Optional[float]:
        """Get exchange rate, using cache first, then API, then fallback"""
        
        # Check cache first
        cached_rate = self._get_cached_rate(from_currency, to_currency)
        if cached_rate:
            logger.debug(f"Using cached rate {from_currency}/{to_currency}: {cached_rate}")
            return cached_rate
        
        # Try to fetch from API
        api_rate = self._fetch_rate_from_api(from_currency, to_currency)
        if api_rate:
            self._cache_rate(from_currency, to_currency, api_rate)
            logger.info(f"Fetched API rate {from_currency}/{to_currency}: {api_rate}")
            return api_rate
        
        # Use fallback rate
        fallback_rate = self._get_fallback_rate(from_currency, to_currency)
        if fallback_rate:
            logger.warning(f"Using fallback rate {from_currency}/{to_currency}: {fallback_rate}")
            return fallback_rate
        
        logger.error(f"Could not get exchange rate for {from_currency}/{to_currency}")
        return None
    
    def _get_cached_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Get exchange rate from database cache"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.cache_duration_hours)
        
        cached_rate = self.db_session.query(ExchangeRate).filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
            ExchangeRate.date >= cutoff_time
        ).order_by(ExchangeRate.date.desc()).first()
        
        if cached_rate:
            return cached_rate.rate
        
        return None
    
    def _cache_rate(self, from_currency: str, to_currency: str, rate: float):
        """Cache exchange rate in database"""
        try:
            exchange_rate = ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                source='api'
            )
            self.db_session.add(exchange_rate)
            self.db_session.commit()
        except Exception as e:
            logger.error(f"Error caching exchange rate: {e}")
            self.db_session.rollback()
    
    def _fetch_rate_from_api(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Fetch exchange rate from external API"""
        
        # Try multiple free APIs
        apis = [
            self._fetch_from_exchangerate_api,
            self._fetch_from_fixer_io,
            self._fetch_from_free_forex_api
        ]
        
        for api_func in apis:
            try:
                rate = api_func(from_currency, to_currency)
                if rate:
                    return rate
            except Exception as e:
                logger.debug(f"API call failed: {e}")
                continue
        
        return None
    
    def _fetch_from_exchangerate_api(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Fetch from exchangerate-api.com (free tier available)"""
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            rates = data.get('rates', {})
            
            return rates.get(to_currency)
            
        except Exception as e:
            logger.debug(f"ExchangeRate-API error: {e}")
            return None
    
    def _fetch_from_fixer_io(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Fetch from fixer.io (requires API key)"""
        if not self.api_key:
            return None
        
        try:
            url = f"http://data.fixer.io/api/latest"
            params = {
                'access_key': self.api_key,
                'base': from_currency,
                'symbols': to_currency
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                rates = data.get('rates', {})
                return rates.get(to_currency)
            
        except Exception as e:
            logger.debug(f"Fixer.io error: {e}")
            return None
    
    def _fetch_from_free_forex_api(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Fetch from free forex API"""
        try:
            url = f"https://api.exchangerate.host/convert"
            params = {
                'from': from_currency,
                'to': to_currency,
                'amount': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                return data.get('result')
            
        except Exception as e:
            logger.debug(f"ExchangeRate.host error: {e}")
            return None
    
    def _get_fallback_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Get fallback exchange rate from hardcoded values"""
        if from_currency == to_currency:
            return 1.0
        
        # Convert via USD if needed
        if to_currency != 'USD':
            from_rate = self.fallback_rates.get(from_currency)
            to_rate = self.fallback_rates.get(to_currency)
            
            if from_rate and to_rate:
                # Convert from_currency -> USD -> to_currency
                return to_rate / from_rate
        else:
            # Direct conversion to USD
            from_rate = self.fallback_rates.get(from_currency)
            if from_rate:
                return 1.0 / from_rate
        
        return None
    
    def update_fallback_rates(self):
        """Update fallback rates from latest successful API calls"""
        try:
            # Get latest rates from database for each currency
            currencies = ['EUR', 'GBP', 'JPY', 'INR', 'CAD', 'AUD']
            
            for currency in currencies:
                latest_rate = self.db_session.query(ExchangeRate).filter(
                    ExchangeRate.from_currency == currency,
                    ExchangeRate.to_currency == 'USD'
                ).order_by(ExchangeRate.date.desc()).first()
                
                if latest_rate:
                    self.fallback_rates[currency] = latest_rate.rate
                    logger.info(f"Updated fallback rate for {currency}: {latest_rate.rate}")
        
        except Exception as e:
            logger.error(f"Error updating fallback rates: {e}")
    
    def get_supported_currencies(self) -> list:
        """Get list of supported currencies"""
        return list(self.fallback_rates.keys())
    
    def bulk_convert_to_usd(self, amounts_and_currencies: list) -> list:
        """Convert multiple amounts to USD efficiently"""
        results = []
        
        # Group by currency to minimize API calls
        currency_groups = {}
        for amount, currency, index in amounts_and_currencies:
            if currency not in currency_groups:
                currency_groups[currency] = []
            currency_groups[currency].append((amount, index))
        
        # Convert each currency group
        for currency, items in currency_groups.items():
            rate = self.get_exchange_rate(currency, 'USD') if currency != 'USD' else 1.0
            
            for amount, index in items:
                if rate:
                    usd_amount = amount / rate if currency != 'USD' else amount
                    results.append((index, usd_amount))
                else:
                    results.append((index, None))
        
        # Sort by original index
        results.sort(key=lambda x: x[0])
        return [result[1] for result in results]