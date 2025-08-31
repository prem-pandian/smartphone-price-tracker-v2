#!/usr/bin/env python3
"""
Web application for Smartphone Price Tracker on Render.com

Provides a simple web interface and API endpoints for monitoring.
"""

from flask import Flask, jsonify, render_template_string, request
import os
import sys
import asyncio
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import db_manager, PriceRecord, PhoneModel, Platform
from src.analysis import PriceAnalyzer
from src.utils import setup_logging, get_logger
from config.settings import settings

# Initialize Flask app
app = Flask(__name__)

# Setup logging
setup_logging(log_level='INFO', log_file=None)
logger = get_logger(__name__)

# Initialize database connection
try:
    db_manager.create_tables()
    logger.info("Database connection established")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")


@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    try:
        # Test database connection
        db_healthy = db_manager.test_connection()
        
        return jsonify({
            'status': 'healthy' if db_healthy else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected' if db_healthy else 'disconnected',
            'version': '1.0.0'
        }), 200 if db_healthy else 503
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/')
def dashboard():
    """Simple dashboard showing recent activity"""
    try:
        with db_manager.get_session() as session:
            # Get basic stats
            total_records = session.query(PriceRecord).count()
            recent_records = session.query(PriceRecord).filter(
                PriceRecord.scrape_timestamp >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            total_models = session.query(PhoneModel).filter(PhoneModel.is_active == True).count()
            total_platforms = session.query(Platform).filter(Platform.is_active == True).count()
            
            # Get recent price records
            recent_prices = session.query(PriceRecord)\
                .join(PhoneModel)\
                .join(Platform)\
                .order_by(PriceRecord.scrape_timestamp.desc())\
                .limit(20).all()
        
        return render_template_string(DASHBOARD_TEMPLATE, 
            total_records=total_records,
            recent_records=recent_records,
            total_models=total_models,
            total_platforms=total_platforms,
            recent_prices=recent_prices,
            now=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return f"Error loading dashboard: {e}", 500


@app.route('/api/status')
def api_status():
    """API endpoint for system status"""
    try:
        with db_manager.get_session() as session:
            stats = {
                'total_records': session.query(PriceRecord).count(),
                'recent_records': session.query(PriceRecord).filter(
                    PriceRecord.scrape_timestamp >= datetime.utcnow() - timedelta(days=7)
                ).count(),
                'active_models': session.query(PhoneModel).filter(PhoneModel.is_active == True).count(),
                'active_platforms': session.query(Platform).filter(Platform.is_active == True).count(),
                'last_updated': datetime.utcnow().isoformat()
            }
        
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"API status error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/insights')
def api_insights():
    """API endpoint for market insights"""
    try:
        with db_manager.get_session() as session:
            analyzer = PriceAnalyzer(session)
            
            # Get insights
            insights = []
            insights.extend(analyzer.find_arbitrage_opportunities(min_profit_percent=5.0))
            insights.extend(analyzer.find_significant_price_changes(min_change_percent=5.0))
            insights.extend(analyzer.find_best_deals(top_n=5))
            
            # Convert to JSON serializable format
            insights_data = [{
                'type': insight.insight_type,
                'title': insight.title,
                'description': insight.description,
                'phone_model': insight.phone_model,
                'platform': insight.platform,
                'region': insight.region,
                'value': insight.value,
                'confidence': insight.confidence
            } for insight in insights[:20]]  # Limit to 20 insights
            
            return jsonify({
                'insights': insights_data,
                'count': len(insights_data),
                'generated_at': datetime.utcnow().isoformat()
            })
    
    except Exception as e:
        logger.error(f"API insights error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trigger-scrape', methods=['POST'])
def trigger_scrape():
    """API endpoint to trigger manual scraping"""
    try:
        # This would typically be protected with authentication
        # For demo purposes, we'll allow it but log the request
        
        region = request.json.get('region') if request.json else None
        platform = request.json.get('platform') if request.json else None
        
        logger.info(f"Manual scrape triggered - Region: {region}, Platform: {platform}")
        
        # In a real implementation, this would queue a background task
        # For now, just return a success message
        
        return jsonify({
            'message': 'Scraping task queued',
            'region': region,
            'platform': platform,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Trigger scrape error: {e}")
        return jsonify({'error': str(e)}), 500


# HTML template for dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📱 Smartphone Price Tracker</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
        }
        .recent-activity {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .activity-item {
            padding: 15px 0;
            border-bottom: 1px solid #eee;
        }
        .activity-item:last-child {
            border-bottom: none;
        }
        .price {
            color: #28a745;
            font-weight: bold;
        }
        .timestamp {
            color: #999;
            font-size: 0.8em;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #666;
        }
        .api-links {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .api-link {
            display: inline-block;
            margin: 5px 10px;
            padding: 8px 15px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.9em;
        }
        .api-link:hover {
            background: #5a6fd8;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Smartphone Price Tracker</h1>
            <p>Monitoring refurbished phone prices globally</p>
            <p><small>Last updated: {{ now.strftime('%Y-%m-%d %H:%M UTC') }}</small></p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ "{:,}".format(total_records) }}</div>
                <div class="stat-label">Total Price Records</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ "{:,}".format(recent_records) }}</div>
                <div class="stat-label">Records This Week</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_models }}</div>
                <div class="stat-label">Phone Models Tracked</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_platforms }}</div>
                <div class="stat-label">Platforms Monitored</div>
            </div>
        </div>
        
        <div class="api-links">
            <h3>📡 API Endpoints</h3>
            <a href="/api/status" class="api-link">System Status</a>
            <a href="/api/insights" class="api-link">Market Insights</a>
            <a href="/health" class="api-link">Health Check</a>
        </div>
        
        <div class="recent-activity">
            <h3>🕐 Recent Price Records</h3>
            {% for price in recent_prices %}
            <div class="activity-item">
                <strong>{{ price.phone_model.brand }} {{ price.phone_model.model_name }}</strong>
                ({{ price.phone_model.storage_capacity }}, {{ price.condition }})
                on <strong>{{ price.platform.name }}</strong>
                - <span class="price">${{ "%.2f"|format(price.price) }} {{ price.currency }}</span>
                <div class="timestamp">{{ price.scrape_timestamp.strftime('%Y-%m-%d %H:%M UTC') }}</div>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>🚀 Deployed on <a href="https://render.com">Render.com</a> | 
               📊 <a href="https://github.com/yourusername/smartphone-price-tracker">View on GitHub</a></p>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => {
            location.reload();
        }, 5 * 60 * 1000);
    </script>
</body>
</html>
"""


if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
else:
    # For Render deployment
    # Render will use Gunicorn to serve this app
    pass