import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import seaborn as sns
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import io
import base64
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from ..database import PriceRecord, PhoneModel, Platform
from ..analysis import PriceAnalysis

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generates charts and visualizations for price analysis"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        
        # Set style preferences
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Configure matplotlib for better output
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.labelsize'] = 12
    
    def generate_price_trend_chart(self, 
                                 phone_model_id: int = None, 
                                 days_back: int = 30,
                                 output_format: str = 'base64') -> Optional[str]:
        """Generate price trend chart for specific model or overall market"""
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Query price data
            query = self.db_session.query(
                PriceRecord.scrape_timestamp,
                PriceRecord.price_usd,
                PhoneModel.brand,
                PhoneModel.model_name,
                Platform.name.label('platform_name'),
                PriceRecord.condition
            ).join(PhoneModel, PriceRecord.phone_model_id == PhoneModel.id)\
             .join(Platform, PriceRecord.platform_id == Platform.id)\
             .filter(
                 and_(
                     PriceRecord.scrape_timestamp >= cutoff_date,
                     PriceRecord.price_usd.isnot(None)
                 )
             )
            
            if phone_model_id:
                query = query.filter(PriceRecord.phone_model_id == phone_model_id)
            
            data = query.all()
            
            if not data:
                logger.warning("No data found for price trend chart")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': record.scrape_timestamp,
                'price_usd': record.price_usd,
                'model': f"{record.brand} {record.model_name}",
                'platform': record.platform_name,
                'condition': record.condition
            } for record in data])
            
            # Create the chart
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Group by model and plot trends
            models = df['model'].unique()
            colors = plt.cm.Set3(np.linspace(0, 1, len(models)))
            
            for i, model in enumerate(models[:5]):  # Limit to top 5 models
                model_data = df[df['model'] == model]
                
                # Calculate daily averages to smooth the data
                daily_avg = model_data.groupby(model_data['timestamp'].dt.date)['price_usd'].mean()
                
                ax.plot(daily_avg.index, daily_avg.values, 
                       marker='o', linewidth=2, markersize=4,
                       label=model, color=colors[i])
            
            # Formatting
            ax.set_title(f'Price Trends - Last {days_back} Days', fontsize=16, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Price (USD)')
            ax.grid(True, alpha=0.3)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days_back // 10)))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            return self._save_chart(fig, output_format)
            
        except Exception as e:
            logger.error(f"Error generating price trend chart: {e}")
            return None
    
    def generate_platform_comparison_chart(self, output_format: str = 'base64') -> Optional[str]:
        """Generate platform comparison chart showing average prices"""
        
        try:
            # Get average prices by platform for recent data
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            platform_avg = self.db_session.query(
                Platform.name,
                Platform.region,
                func.avg(PriceRecord.price_usd).label('avg_price'),
                func.count(PriceRecord.id).label('record_count')
            ).join(Platform, PriceRecord.platform_id == Platform.id)\
             .filter(
                 and_(
                     PriceRecord.scrape_timestamp >= cutoff_date,
                     PriceRecord.price_usd.isnot(None)
                 )
             ).group_by(Platform.name, Platform.region)\
             .having(func.count(PriceRecord.id) >= 5)\
             .order_by(desc('avg_price')).all()
            
            if not platform_avg:
                logger.warning("No data found for platform comparison chart")
                return None
            
            # Create DataFrame
            df = pd.DataFrame([{
                'platform': f"{record.name}\n({record.region})",
                'avg_price': float(record.avg_price),
                'record_count': record.record_count
            } for record in platform_avg])
            
            # Create chart
            fig, ax = plt.subplots(figsize=(12, 8))
            
            bars = ax.bar(df['platform'], df['avg_price'], 
                         color=plt.cm.viridis(np.linspace(0, 1, len(df))))
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'${height:.0f}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom')
            
            ax.set_title('Average Prices by Platform (Last 7 Days)', fontsize=16, fontweight='bold')
            ax.set_xlabel('Platform')
            ax.set_ylabel('Average Price (USD)')
            ax.grid(True, alpha=0.3, axis='y')
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            return self._save_chart(fig, output_format)
            
        except Exception as e:
            logger.error(f"Error generating platform comparison chart: {e}")
            return None
    
    def generate_brand_analysis_chart(self, output_format: str = 'base64') -> Optional[str]:
        """Generate brand analysis chart showing price distributions"""
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Get price data by brand
            brand_data = self.db_session.query(
                PhoneModel.brand,
                PriceRecord.price_usd,
                PriceRecord.condition
            ).join(PhoneModel, PriceRecord.phone_model_id == PhoneModel.id)\
             .filter(
                 and_(
                     PriceRecord.scrape_timestamp >= cutoff_date,
                     PriceRecord.price_usd.isnot(None)
                 )
             ).all()
            
            if not brand_data:
                logger.warning("No data found for brand analysis chart")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame([{
                'brand': record.brand,
                'price_usd': record.price_usd,
                'condition': record.condition
            } for record in brand_data])
            
            # Create subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. Box plot by brand
            brands = df['brand'].unique()
            brand_prices = [df[df['brand'] == brand]['price_usd'].values for brand in brands]
            
            box_plot = ax1.boxplot(brand_prices, labels=brands, patch_artist=True)
            colors = plt.cm.Set3(np.linspace(0, 1, len(brands)))
            for patch, color in zip(box_plot['boxes'], colors):
                patch.set_facecolor(color)
            
            ax1.set_title('Price Distribution by Brand')
            ax1.set_ylabel('Price (USD)')
            ax1.grid(True, alpha=0.3)
            
            # 2. Average price by brand
            brand_avg = df.groupby('brand')['price_usd'].mean().sort_values(ascending=False)
            bars = ax2.bar(brand_avg.index, brand_avg.values, color=colors[:len(brand_avg)])
            ax2.set_title('Average Price by Brand')
            ax2.set_ylabel('Average Price (USD)')
            ax2.grid(True, alpha=0.3, axis='y')
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax2.annotate(f'${height:.0f}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom')
            
            # 3. Price by condition
            condition_avg = df.groupby('condition')['price_usd'].mean().sort_values(ascending=False)
            ax3.pie(condition_avg.values, labels=condition_avg.index, autopct='%1.1f%%',
                   colors=plt.cm.Pastel1(np.linspace(0, 1, len(condition_avg))))
            ax3.set_title('Average Price Distribution by Condition')
            
            # 4. Brand market share (by number of listings)
            brand_counts = df['brand'].value_counts()
            ax4.pie(brand_counts.values, labels=brand_counts.index, autopct='%1.1f%%',
                   colors=plt.cm.Set2(np.linspace(0, 1, len(brand_counts))))
            ax4.set_title('Market Share by Brand (Listings)')
            
            plt.suptitle('Brand Analysis Overview', fontsize=18, fontweight='bold')
            plt.tight_layout()
            
            return self._save_chart(fig, output_format)
            
        except Exception as e:
            logger.error(f"Error generating brand analysis chart: {e}")
            return None
    
    def generate_volatility_chart(self, output_format: str = 'base64') -> Optional[str]:
        """Generate price volatility chart"""
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Calculate volatility for each model/platform combination
            volatility_data = []
            
            combinations = self.db_session.query(
                PriceRecord.phone_model_id,
                PriceRecord.platform_id
            ).distinct().all()
            
            for phone_model_id, platform_id in combinations:
                prices = self.db_session.query(PriceRecord.price_usd).filter(
                    and_(
                        PriceRecord.phone_model_id == phone_model_id,
                        PriceRecord.platform_id == platform_id,
                        PriceRecord.scrape_timestamp >= cutoff_date,
                        PriceRecord.price_usd.isnot(None)
                    )
                ).all()
                
                if len(prices) >= 5:  # Need at least 5 data points
                    price_values = [p.price_usd for p in prices]
                    volatility = np.std(price_values) / np.mean(price_values) * 100  # CV%
                    
                    phone_model = self.db_session.query(PhoneModel).get(phone_model_id)
                    platform = self.db_session.query(Platform).get(platform_id)
                    
                    if phone_model and platform:
                        volatility_data.append({
                            'model': f"{phone_model.brand} {phone_model.model_name}",
                            'platform': platform.name,
                            'volatility': volatility,
                            'avg_price': np.mean(price_values)
                        })
            
            if not volatility_data:
                logger.warning("No data found for volatility chart")
                return None
            
            # Convert to DataFrame and sort by volatility
            df = pd.DataFrame(volatility_data).sort_values('volatility', ascending=False)
            
            # Take top 15 most volatile
            df_top = df.head(15)
            
            # Create chart
            fig, ax = plt.subplots(figsize=(14, 10))
            
            # Create scatter plot
            scatter = ax.scatter(df_top['avg_price'], df_top['volatility'], 
                               s=100, alpha=0.7, c=range(len(df_top)), 
                               cmap='viridis')
            
            # Add labels for each point
            for i, row in df_top.iterrows():
                ax.annotate(f"{row['model']}\n({row['platform']})",
                           (row['avg_price'], row['volatility']),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, alpha=0.8)
            
            ax.set_title('Price Volatility vs Average Price', fontsize=16, fontweight='bold')
            ax.set_xlabel('Average Price (USD)')
            ax.set_ylabel('Price Volatility (CV %)')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            return self._save_chart(fig, output_format)
            
        except Exception as e:
            logger.error(f"Error generating volatility chart: {e}")
            return None
    
    def generate_all_charts(self, output_format: str = 'base64') -> Dict[str, Optional[str]]:
        """Generate all charts for the report"""
        
        charts = {}
        
        chart_methods = [
            ('price_trends', self.generate_price_trend_chart),
            ('platform_comparison', self.generate_platform_comparison_chart),
            ('brand_analysis', self.generate_brand_analysis_chart),
            ('volatility_analysis', self.generate_volatility_chart)
        ]
        
        for chart_name, method in chart_methods:
            try:
                logger.info(f"Generating {chart_name} chart...")
                chart_data = method(output_format=output_format)
                charts[chart_name] = chart_data
                
                if chart_data:
                    logger.info(f"Successfully generated {chart_name} chart")
                else:
                    logger.warning(f"Failed to generate {chart_name} chart")
                    
            except Exception as e:
                logger.error(f"Error generating {chart_name} chart: {e}")
                charts[chart_name] = None
        
        return charts
    
    def _save_chart(self, fig: plt.Figure, output_format: str) -> Optional[str]:
        """Save chart in specified format"""
        
        try:
            if output_format == 'base64':
                # Save to base64 string for email embedding
                buffer = io.BytesIO()
                fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                           facecolor='white', edgecolor='none')
                buffer.seek(0)
                
                chart_base64 = base64.b64encode(buffer.getvalue()).decode()
                buffer.close()
                plt.close(fig)
                
                return chart_base64
                
            elif output_format.startswith('file:'):
                # Save to file
                file_path = output_format.replace('file:', '')
                fig.savefig(file_path, dpi=300, bbox_inches='tight', 
                           facecolor='white', edgecolor='none')
                plt.close(fig)
                
                return file_path
                
            else:
                logger.error(f"Unsupported output format: {output_format}")
                plt.close(fig)
                return None
                
        except Exception as e:
            logger.error(f"Error saving chart: {e}")
            plt.close(fig)
            return None
    
    def create_interactive_chart(self, chart_type: str = 'price_trends') -> Optional[str]:
        """Create interactive Plotly chart (for web dashboard)"""
        
        try:
            if chart_type == 'price_trends':
                return self._create_interactive_price_trends()
            elif chart_type == 'platform_comparison':
                return self._create_interactive_platform_comparison()
            else:
                logger.warning(f"Unsupported interactive chart type: {chart_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating interactive chart: {e}")
            return None
    
    def _create_interactive_price_trends(self) -> Optional[str]:
        """Create interactive price trends chart using Plotly"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Get data
        data = self.db_session.query(
            PriceRecord.scrape_timestamp,
            PriceRecord.price_usd,
            PhoneModel.brand,
            PhoneModel.model_name,
            Platform.name.label('platform_name')
        ).join(PhoneModel, PriceRecord.phone_model_id == PhoneModel.id)\
         .join(Platform, PriceRecord.platform_id == Platform.id)\
         .filter(
             and_(
                 PriceRecord.scrape_timestamp >= cutoff_date,
                 PriceRecord.price_usd.isnot(None)
             )
         ).all()
        
        if not data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': record.scrape_timestamp,
            'price_usd': record.price_usd,
            'model': f"{record.brand} {record.model_name}",
            'platform': record.platform_name
        } for record in data])
        
        # Create interactive plot
        fig = px.line(df, x='timestamp', y='price_usd', color='model',
                     title='Interactive Price Trends (Last 30 Days)',
                     labels={'price_usd': 'Price (USD)', 'timestamp': 'Date'})
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig.to_html(include_plotlyjs=True)