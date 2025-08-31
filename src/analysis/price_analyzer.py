from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
import logging
from dataclasses import dataclass
from ..database import PriceRecord, PhoneModel, Platform, PriceTrend

logger = logging.getLogger(__name__)


@dataclass
class PriceAnalysis:
    phone_model: str
    brand: str
    storage: str
    platform: str
    region: str
    condition: str
    
    current_price: float
    previous_price: Optional[float]
    price_change_amount: float
    price_change_percent: float
    
    avg_price_7d: float
    avg_price_30d: float
    min_price_7d: float
    max_price_7d: float
    volatility: float
    
    trend_direction: str  # 'up', 'down', 'stable'
    confidence_score: float


@dataclass
class MarketInsight:
    insight_type: str  # 'price_drop', 'arbitrage', 'trend_change', 'best_deal'
    title: str
    description: str
    phone_model: str
    platform: str
    region: str
    value: float  # Price, percentage, or score
    confidence: float


class PriceAnalyzer:
    """Analyzes price data and generates insights"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.price_change_threshold = 5.0  # 5% threshold for significant changes
    
    def analyze_price_trends(self, days_back: int = 30) -> List[PriceAnalysis]:
        """Analyze price trends for all phone models and platforms"""
        analyses = []
        
        # Get all unique phone model/platform/condition combinations
        combinations = self.db_session.query(
            PriceRecord.phone_model_id,
            PriceRecord.platform_id,
            PriceRecord.condition
        ).distinct().all()
        
        for phone_model_id, platform_id, condition in combinations:
            try:
                analysis = self._analyze_single_combination(
                    phone_model_id, platform_id, condition, days_back
                )
                if analysis:
                    analyses.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing combination {phone_model_id}/{platform_id}/{condition}: {e}")
        
        return analyses
    
    def _analyze_single_combination(self, phone_model_id: int, platform_id: int, 
                                  condition: str, days_back: int) -> Optional[PriceAnalysis]:
        """Analyze price trends for a single phone/platform/condition combination"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get price records for this combination
        prices_query = self.db_session.query(PriceRecord).filter(
            and_(
                PriceRecord.phone_model_id == phone_model_id,
                PriceRecord.platform_id == platform_id,
                PriceRecord.condition == condition,
                PriceRecord.scrape_timestamp >= cutoff_date,
                PriceRecord.price_usd.isnot(None)
            )
        ).order_by(desc(PriceRecord.scrape_timestamp))
        
        prices = prices_query.all()
        
        if len(prices) < 2:
            return None
        
        # Get phone model and platform details
        phone_model = self.db_session.query(PhoneModel).get(phone_model_id)
        platform = self.db_session.query(Platform).get(platform_id)
        
        if not phone_model or not platform:
            return None
        
        # Convert to pandas for analysis
        df = pd.DataFrame([{
            'timestamp': p.scrape_timestamp,
            'price_usd': p.price_usd,
            'price': p.price,
            'currency': p.currency
        } for p in prices])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Calculate metrics
        current_price = df['price_usd'].iloc[-1]
        previous_price = df['price_usd'].iloc[-2] if len(df) > 1 else None
        
        price_change_amount = current_price - previous_price if previous_price else 0
        price_change_percent = (price_change_amount / previous_price * 100) if previous_price else 0
        
        # Calculate averages and volatility
        df_7d = df[df['timestamp'] >= (datetime.utcnow() - timedelta(days=7))]
        df_30d = df[df['timestamp'] >= (datetime.utcnow() - timedelta(days=30))]
        
        avg_price_7d = df_7d['price_usd'].mean() if len(df_7d) > 0 else current_price
        avg_price_30d = df_30d['price_usd'].mean() if len(df_30d) > 0 else current_price
        min_price_7d = df_7d['price_usd'].min() if len(df_7d) > 0 else current_price
        max_price_7d = df_7d['price_usd'].max() if len(df_7d) > 0 else current_price
        
        volatility = df['price_usd'].std() if len(df) > 1 else 0.0
        
        # Determine trend direction
        trend_direction = self._determine_trend_direction(df)
        confidence_score = self._calculate_confidence_score(df, volatility)
        
        return PriceAnalysis(
            phone_model=phone_model.model_name,
            brand=phone_model.brand,
            storage=phone_model.storage_capacity,
            platform=platform.name,
            region=platform.region,
            condition=condition,
            current_price=current_price,
            previous_price=previous_price,
            price_change_amount=price_change_amount,
            price_change_percent=price_change_percent,
            avg_price_7d=avg_price_7d,
            avg_price_30d=avg_price_30d,
            min_price_7d=min_price_7d,
            max_price_7d=max_price_7d,
            volatility=volatility,
            trend_direction=trend_direction,
            confidence_score=confidence_score
        )
    
    def _determine_trend_direction(self, df: pd.DataFrame) -> str:
        """Determine overall trend direction from price data"""
        if len(df) < 3:
            return 'stable'
        
        # Calculate trend using linear regression slope
        x = np.arange(len(df))
        y = df['price_usd'].values
        
        slope, _ = np.polyfit(x, y, 1)
        
        # Normalize slope by average price
        avg_price = y.mean()
        normalized_slope = (slope / avg_price) * 100  # Convert to percentage per day
        
        if normalized_slope > 0.5:  # More than 0.5% increase per day on average
            return 'up'
        elif normalized_slope < -0.5:  # More than 0.5% decrease per day on average
            return 'down'
        else:
            return 'stable'
    
    def _calculate_confidence_score(self, df: pd.DataFrame, volatility: float) -> float:
        """Calculate confidence score for the trend analysis"""
        if len(df) < 3:
            return 0.3
        
        # More data points = higher confidence
        data_score = min(len(df) / 20.0, 1.0)  # Max confidence at 20+ data points
        
        # Lower volatility = higher confidence  
        avg_price = df['price_usd'].mean()
        volatility_ratio = volatility / avg_price if avg_price > 0 else 1.0
        volatility_score = max(0, 1.0 - volatility_ratio * 2)  # Penalize high volatility
        
        # Recency score - more recent data is better
        days_span = (df['timestamp'].max() - df['timestamp'].min()).days
        recency_score = min(days_span / 30.0, 1.0)  # Max confidence with 30+ days of data
        
        # Combine scores
        confidence = (data_score * 0.4 + volatility_score * 0.4 + recency_score * 0.2)
        return max(0.1, min(1.0, confidence))
    
    def find_arbitrage_opportunities(self, min_profit_percent: float = 10.0) -> List[MarketInsight]:
        """Find arbitrage opportunities between regions/platforms"""
        insights = []
        
        # Get latest prices grouped by phone model and condition
        latest_prices_subquery = self.db_session.query(
            PriceRecord.phone_model_id,
            PriceRecord.platform_id,
            PriceRecord.condition,
            func.max(PriceRecord.scrape_timestamp).label('latest_timestamp')
        ).group_by(
            PriceRecord.phone_model_id,
            PriceRecord.platform_id,
            PriceRecord.condition
        ).subquery()
        
        latest_prices = self.db_session.query(PriceRecord).join(
            latest_prices_subquery,
            and_(
                PriceRecord.phone_model_id == latest_prices_subquery.c.phone_model_id,
                PriceRecord.platform_id == latest_prices_subquery.c.platform_id,
                PriceRecord.condition == latest_prices_subquery.c.condition,
                PriceRecord.scrape_timestamp == latest_prices_subquery.c.latest_timestamp
            )
        ).all()
        
        # Group by phone model and condition
        price_groups = {}
        for price in latest_prices:
            key = (price.phone_model_id, price.condition)
            if key not in price_groups:
                price_groups[key] = []
            price_groups[key].append(price)
        
        # Find arbitrage opportunities within each group
        for (phone_model_id, condition), prices in price_groups.items():
            if len(prices) < 2:
                continue
            
            phone_model = self.db_session.query(PhoneModel).get(phone_model_id)
            if not phone_model:
                continue
            
            # Sort by price (lowest first)
            prices_sorted = sorted(prices, key=lambda p: p.price_usd or float('inf'))
            
            min_price = prices_sorted[0]
            max_price = prices_sorted[-1]
            
            if not min_price.price_usd or not max_price.price_usd:
                continue
            
            profit_percent = ((max_price.price_usd - min_price.price_usd) / min_price.price_usd) * 100
            
            if profit_percent >= min_profit_percent:
                min_platform = self.db_session.query(Platform).get(min_price.platform_id)
                max_platform = self.db_session.query(Platform).get(max_price.platform_id)
                
                insights.append(MarketInsight(
                    insight_type='arbitrage',
                    title=f'Arbitrage Opportunity: {phone_model.brand} {phone_model.model_name}',
                    description=f'Buy from {min_platform.name} (${min_price.price_usd:.2f}) '
                              f'and sell on {max_platform.name} (${max_price.price_usd:.2f}) '
                              f'for {profit_percent:.1f}% profit',
                    phone_model=f'{phone_model.brand} {phone_model.model_name}',
                    platform=f'{min_platform.name} → {max_platform.name}',
                    region=f'{min_platform.region} → {max_platform.region}',
                    value=profit_percent,
                    confidence=0.8
                ))
        
        return sorted(insights, key=lambda x: x.value, reverse=True)
    
    def find_significant_price_changes(self, min_change_percent: float = 10.0) -> List[MarketInsight]:
        """Find significant price changes in the last week"""
        insights = []
        
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        
        # Get recent price trends
        recent_trends = self.db_session.query(PriceTrend).filter(
            and_(
                PriceTrend.trend_date >= one_week_ago,
                PriceTrend.trend_period == 'weekly',
                func.abs(PriceTrend.price_change_percent) >= min_change_percent
            )
        ).order_by(desc(func.abs(PriceTrend.price_change_percent))).all()
        
        for trend in recent_trends:
            phone_model = self.db_session.query(PhoneModel).get(trend.phone_model_id)
            platform = self.db_session.query(Platform).get(trend.platform_id)
            
            if not phone_model or not platform:
                continue
            
            change_type = 'price_drop' if trend.price_change_percent < 0 else 'price_increase'
            change_direction = 'dropped' if trend.price_change_percent < 0 else 'increased'
            
            insights.append(MarketInsight(
                insight_type=change_type,
                title=f'Significant Price Change: {phone_model.brand} {phone_model.model_name}',
                description=f'Price {change_direction} by {abs(trend.price_change_percent):.1f}% '
                          f'on {platform.name} to ${trend.current_price_usd:.2f}',
                phone_model=f'{phone_model.brand} {phone_model.model_name}',
                platform=platform.name,
                region=platform.region,
                value=abs(trend.price_change_percent),
                confidence=0.9
            ))
        
        return insights
    
    def find_best_deals(self, top_n: int = 10) -> List[MarketInsight]:
        """Find the best deals across all platforms"""
        insights = []
        
        # For each phone model/condition, find the lowest current price
        latest_prices_subquery = self.db_session.query(
            PriceRecord.phone_model_id,
            PriceRecord.condition,
            func.min(PriceRecord.price_usd).label('min_price')
        ).filter(
            and_(
                PriceRecord.scrape_timestamp >= datetime.utcnow() - timedelta(days=3),
                PriceRecord.price_usd.isnot(None),
                PriceRecord.availability == True
            )
        ).group_by(
            PriceRecord.phone_model_id,
            PriceRecord.condition
        ).subquery()
        
        best_deals = self.db_session.query(PriceRecord).join(
            latest_prices_subquery,
            and_(
                PriceRecord.phone_model_id == latest_prices_subquery.c.phone_model_id,
                PriceRecord.condition == latest_prices_subquery.c.condition,
                PriceRecord.price_usd == latest_prices_subquery.c.min_price
            )
        ).order_by(PriceRecord.price_usd).limit(top_n).all()
        
        for deal in best_deals:
            phone_model = self.db_session.query(PhoneModel).get(deal.phone_model_id)
            platform = self.db_session.query(Platform).get(deal.platform_id)
            
            if not phone_model or not platform:
                continue
            
            # Calculate how good this deal is compared to average market price
            avg_price = self.db_session.query(func.avg(PriceRecord.price_usd)).filter(
                and_(
                    PriceRecord.phone_model_id == deal.phone_model_id,
                    PriceRecord.condition == deal.condition,
                    PriceRecord.scrape_timestamp >= datetime.utcnow() - timedelta(days=30),
                    PriceRecord.price_usd.isnot(None)
                )
            ).scalar()
            
            if avg_price and deal.price_usd:
                savings_percent = ((avg_price - deal.price_usd) / avg_price) * 100
                
                insights.append(MarketInsight(
                    insight_type='best_deal',
                    title=f'Best Deal: {phone_model.brand} {phone_model.model_name}',
                    description=f'${deal.price_usd:.2f} on {platform.name} '
                              f'({savings_percent:.1f}% below average)',
                    phone_model=f'{phone_model.brand} {phone_model.model_name}',
                    platform=platform.name,
                    region=platform.region,
                    value=deal.price_usd,
                    confidence=0.7
                ))
        
        return insights
    
    def generate_market_summary(self) -> Dict[str, Any]:
        """Generate overall market summary statistics"""
        now = datetime.utcnow()
        one_week_ago = now - timedelta(days=7)
        
        # Total number of records
        total_records = self.db_session.query(PriceRecord).count()
        recent_records = self.db_session.query(PriceRecord).filter(
            PriceRecord.scrape_timestamp >= one_week_ago
        ).count()
        
        # Average prices by brand
        brand_avg_prices = self.db_session.query(
            PhoneModel.brand,
            func.avg(PriceRecord.price_usd).label('avg_price')
        ).join(PhoneModel, PriceRecord.phone_model_id == PhoneModel.id).filter(
            and_(
                PriceRecord.scrape_timestamp >= one_week_ago,
                PriceRecord.price_usd.isnot(None)
            )
        ).group_by(PhoneModel.brand).all()
        
        # Most tracked models
        popular_models = self.db_session.query(
            PhoneModel.brand,
            PhoneModel.model_name,
            func.count(PriceRecord.id).label('record_count')
        ).join(PhoneModel, PriceRecord.phone_model_id == PhoneModel.id).filter(
            PriceRecord.scrape_timestamp >= one_week_ago
        ).group_by(PhoneModel.brand, PhoneModel.model_name).order_by(
            desc('record_count')
        ).limit(5).all()
        
        # Platform activity
        platform_activity = self.db_session.query(
            Platform.name,
            func.count(PriceRecord.id).label('record_count')
        ).join(Platform, PriceRecord.platform_id == Platform.id).filter(
            PriceRecord.scrape_timestamp >= one_week_ago
        ).group_by(Platform.name).order_by(desc('record_count')).all()
        
        return {
            'total_records': total_records,
            'recent_records': recent_records,
            'brand_avg_prices': {brand: float(avg_price) for brand, avg_price in brand_avg_prices},
            'popular_models': [(brand, model, count) for brand, model, count in popular_models],
            'platform_activity': [(platform, count) for platform, count in platform_activity],
            'last_updated': now.isoformat()
        }