import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from src.analysis import PriceAnalyzer, PriceAnalysis, MarketInsight, CurrencyConverter
from src.database import PriceRecord, PhoneModel, Platform


class TestCurrencyConverter:
    """Test CurrencyConverter functionality"""
    
    def test_currency_converter_initialization(self):
        """Test CurrencyConverter initialization"""
        mock_session = Mock()
        converter = CurrencyConverter(mock_session)
        
        assert converter.db_session == mock_session
        assert converter.base_currency == 'USD'
        assert converter.cache_duration_hours == 24
        assert 'USD' in converter.fallback_rates
        assert converter.fallback_rates['USD'] == 1.0
    
    def test_convert_to_usd_same_currency(self):
        """Test converting USD to USD"""
        mock_session = Mock()
        converter = CurrencyConverter(mock_session)
        
        result = converter.convert_to_usd(100.0, 'USD')
        assert result == 100.0
    
    def test_convert_to_usd_with_fallback_rate(self):
        """Test converting to USD using fallback rates"""
        mock_session = Mock()
        converter = CurrencyConverter(mock_session)
        
        # Mock the get_exchange_rate to return fallback rate
        converter.get_exchange_rate = Mock(return_value=0.85)  # EUR to USD rate
        
        result = converter.convert_to_usd(100.0, 'EUR')
        assert result == 100.0 / 0.85  # Should divide by rate
    
    def test_get_fallback_rate(self):
        """Test getting fallback rates"""
        mock_session = Mock()
        converter = CurrencyConverter(mock_session)
        
        # Test EUR to USD
        rate = converter._get_fallback_rate('EUR', 'USD')
        assert rate == 1.0 / 0.85  # 1 / fallback_rate
        
        # Test same currency
        rate = converter._get_fallback_rate('USD', 'USD')
        assert rate == 1.0
        
        # Test unknown currency
        rate = converter._get_fallback_rate('UNKNOWN', 'USD')
        assert rate is None
    
    def test_get_supported_currencies(self):
        """Test getting supported currencies"""
        mock_session = Mock()
        converter = CurrencyConverter(mock_session)
        
        currencies = converter.get_supported_currencies()
        assert isinstance(currencies, list)
        assert 'USD' in currencies
        assert 'EUR' in currencies
        assert 'JPY' in currencies


class TestPriceAnalyzer:
    """Test PriceAnalyzer functionality"""
    
    def test_price_analyzer_initialization(self):
        """Test PriceAnalyzer initialization"""
        mock_session = Mock()
        analyzer = PriceAnalyzer(mock_session)
        
        assert analyzer.db_session == mock_session
        assert analyzer.price_change_threshold == 5.0
    
    def test_determine_trend_direction_stable(self):
        """Test trend direction determination for stable prices"""
        mock_session = Mock()
        analyzer = PriceAnalyzer(mock_session)
        
        # Create mock DataFrame with stable prices
        import pandas as pd
        df = pd.DataFrame({
            'price_usd': [100.0, 101.0, 99.5, 100.5, 100.2]
        })
        
        trend = analyzer._determine_trend_direction(df)
        assert trend == 'stable'
    
    def test_determine_trend_direction_up(self):
        """Test trend direction determination for increasing prices"""
        mock_session = Mock()
        analyzer = PriceAnalyzer(mock_session)
        
        import pandas as pd
        df = pd.DataFrame({
            'price_usd': [100.0, 105.0, 110.0, 115.0, 120.0]
        })
        
        trend = analyzer._determine_trend_direction(df)
        assert trend == 'up'
    
    def test_determine_trend_direction_down(self):
        """Test trend direction determination for decreasing prices"""
        mock_session = Mock()
        analyzer = PriceAnalyzer(mock_session)
        
        import pandas as pd
        df = pd.DataFrame({
            'price_usd': [120.0, 115.0, 110.0, 105.0, 100.0]
        })
        
        trend = analyzer._determine_trend_direction(df)
        assert trend == 'down'
    
    def test_calculate_confidence_score(self):
        """Test confidence score calculation"""
        mock_session = Mock()
        analyzer = PriceAnalyzer(mock_session)
        
        import pandas as pd
        import numpy as np
        
        # Create mock DataFrame with good data (many points, low volatility, recent)
        now = datetime.utcnow()
        timestamps = [now - timedelta(days=i) for i in range(20)]
        
        df = pd.DataFrame({
            'price_usd': [100 + np.random.normal(0, 1) for _ in range(20)],
            'timestamp': pd.to_datetime(timestamps)
        })
        
        volatility = df['price_usd'].std()
        confidence = analyzer._calculate_confidence_score(df, volatility)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be high confidence with good data
    
    def test_calculate_confidence_score_low_data(self):
        """Test confidence score with insufficient data"""
        mock_session = Mock()
        analyzer = PriceAnalyzer(mock_session)
        
        import pandas as pd
        df = pd.DataFrame({'price_usd': [100.0]})  # Only one data point
        
        confidence = analyzer._calculate_confidence_score(df, 0.0)
        assert confidence == 0.3  # Should return default low confidence


class TestPriceAnalysis:
    """Test PriceAnalysis dataclass"""
    
    def test_price_analysis_creation(self):
        """Test creating PriceAnalysis instance"""
        analysis = PriceAnalysis(
            phone_model='iPhone 16',
            brand='Apple',
            storage='128GB',
            platform='Swappa',
            region='US',
            condition='Excellent',
            current_price=799.99,
            previous_price=829.99,
            price_change_amount=-30.0,
            price_change_percent=-3.6,
            avg_price_7d=815.0,
            avg_price_30d=825.0,
            min_price_7d=799.99,
            max_price_7d=839.99,
            volatility=15.5,
            trend_direction='down',
            confidence_score=0.85
        )
        
        assert analysis.phone_model == 'iPhone 16'
        assert analysis.brand == 'Apple'
        assert analysis.storage == '128GB'
        assert analysis.platform == 'Swappa'
        assert analysis.region == 'US'
        assert analysis.condition == 'Excellent'
        assert analysis.current_price == 799.99
        assert analysis.previous_price == 829.99
        assert analysis.price_change_amount == -30.0
        assert analysis.price_change_percent == -3.6
        assert analysis.trend_direction == 'down'
        assert analysis.confidence_score == 0.85


class TestMarketInsight:
    """Test MarketInsight dataclass"""
    
    def test_market_insight_creation(self):
        """Test creating MarketInsight instance"""
        insight = MarketInsight(
            insight_type='price_drop',
            title='Significant Price Drop',
            description='iPhone 16 price dropped by 10% on Swappa',
            phone_model='iPhone 16',
            platform='Swappa',
            region='US',
            value=10.0,
            confidence=0.9
        )
        
        assert insight.insight_type == 'price_drop'
        assert insight.title == 'Significant Price Drop'
        assert insight.description == 'iPhone 16 price dropped by 10% on Swappa'
        assert insight.phone_model == 'iPhone 16'
        assert insight.platform == 'Swappa'
        assert insight.region == 'US'
        assert insight.value == 10.0
        assert insight.confidence == 0.9


class TestPriceAnalyzerQueries:
    """Test PriceAnalyzer database query methods"""
    
    @pytest.fixture
    def mock_analyzer(self):
        """Create mock analyzer with session"""
        mock_session = Mock()
        return PriceAnalyzer(mock_session)
    
    def test_generate_market_summary(self, mock_analyzer):
        """Test market summary generation"""
        # Mock database queries
        mock_analyzer.db_session.query.return_value.count.return_value = 1000
        mock_analyzer.db_session.query.return_value.filter.return_value.count.return_value = 150
        
        # Mock brand averages query
        brand_avg_mock = Mock()
        brand_avg_mock.all.return_value = [
            Mock(brand='Apple', avg_price=Decimal('800.00')),
            Mock(brand='Samsung', avg_price=Decimal('700.00')),
        ]
        mock_analyzer.db_session.query.return_value.join.return_value.filter.return_value.group_by.return_value = brand_avg_mock
        
        # Mock popular models query
        popular_mock = Mock()
        popular_mock.limit.return_value.all.return_value = [
            Mock(brand='Apple', model_name='iPhone 16', record_count=50),
            Mock(brand='Samsung', model_name='Galaxy S24', record_count=40),
        ]
        mock_analyzer.db_session.query.return_value.join.return_value.filter.return_value.group_by.return_value.order_by.return_value = popular_mock
        
        # Mock platform activity query  
        platform_mock = Mock()
        platform_mock.all.return_value = [
            Mock(name='Swappa', record_count=60),
            Mock(name='Back Market', record_count=50),
        ]
        mock_analyzer.db_session.query.return_value.join.return_value.filter.return_value.group_by.return_value.order_by.return_value = platform_mock
        
        summary = mock_analyzer.generate_market_summary()
        
        assert isinstance(summary, dict)
        assert 'total_records' in summary
        assert 'recent_records' in summary
        assert 'brand_avg_prices' in summary
        assert 'popular_models' in summary
        assert 'platform_activity' in summary
        assert 'last_updated' in summary


class TestAnalysisIntegration:
    """Integration tests for analysis components"""
    
    def test_end_to_end_analysis_workflow(self):
        """Test complete analysis workflow"""
        # This would test the full workflow from raw data to insights
        # Using mocked database sessions and data
        
        mock_session = Mock()
        analyzer = PriceAnalyzer(mock_session)
        
        # Mock the database queries to return empty results
        mock_analyzer.db_session.query.return_value.distinct.return_value.all.return_value = []
        
        analyses = analyzer.analyze_price_trends(days_back=7)
        assert isinstance(analyses, list)
        
        insights = analyzer.find_arbitrage_opportunities()
        assert isinstance(insights, list)
        
        best_deals = analyzer.find_best_deals()
        assert isinstance(best_deals, list)
        
        summary = analyzer.generate_market_summary()
        assert isinstance(summary, dict)