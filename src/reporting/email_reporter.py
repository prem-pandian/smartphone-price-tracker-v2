import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
import logging
from jinja2 import Environment, FileSystemLoader, Template
from datetime import datetime
import os
import io
import base64
from ..analysis import PriceAnalysis, MarketInsight

logger = logging.getLogger(__name__)


class EmailReporter:
    """Handles email report generation and sending"""
    
    def __init__(self, smtp_config: dict, template_dir: str = "templates"):
        self.smtp_server = smtp_config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = smtp_config.get('smtp_port', 587)
        self.smtp_username = smtp_config.get('smtp_username', '')
        self.smtp_password = smtp_config.get('smtp_password', '')
        self.email_from = smtp_config.get('email_from', '')
        
        self.template_dir = template_dir
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir) if os.path.exists(template_dir) else None
        )
        
        # Add custom filters
        self.jinja_env.filters['currency'] = self._format_currency
        self.jinja_env.filters['percent'] = self._format_percent
        self.jinja_env.filters['datetime'] = self._format_datetime
    
    def generate_weekly_report(self, 
                             price_analyses: List[PriceAnalysis],
                             market_insights: List[MarketInsight],
                             market_summary: Dict[str, Any],
                             charts: Dict[str, Any] = None) -> str:
        """Generate weekly HTML report"""
        
        # Organize data for template
        report_data = {
            'generated_at': datetime.utcnow(),
            'summary': market_summary,
            'price_analyses': price_analyses,
            'market_insights': market_insights,
            'charts': charts or {},
            'stats': self._calculate_report_stats(price_analyses, market_insights)
        }
        
        # Try to use custom template first
        template = self._get_template('weekly_report.html')
        if not template:
            # Use built-in template
            template = Template(self._get_builtin_template())
        
        return template.render(**report_data)
    
    def send_email_report(self, 
                         recipients: List[str],
                         subject: str,
                         html_content: str,
                         attachments: List[str] = None) -> bool:
        """Send email report to recipients"""
        
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = self.email_from
            message['To'] = ', '.join(recipients)
            message['Subject'] = subject
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            # Add attachments if any
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        self._add_attachment(message, attachment_path)
            
            # Send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Email report sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email report: {e}")
            return False
    
    def _get_template(self, template_name: str) -> Optional[Template]:
        """Get Jinja2 template"""
        try:
            return self.jinja_env.get_template(template_name)
        except Exception as e:
            logger.warning(f"Could not load template {template_name}: {e}")
            return None
    
    def _get_builtin_template(self) -> str:
        """Get built-in HTML template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Smartphone Price Tracker - Weekly Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 40px;
        }
        .section h2 {
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .insights-list {
            list-style: none;
            padding: 0;
        }
        .insight-item {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #28a745;
        }
        .insight-item.arbitrage {
            border-left-color: #ffc107;
        }
        .insight-item.price_drop {
            border-left-color: #28a745;
        }
        .insight-item.price_increase {
            border-left-color: #dc3545;
        }
        .insight-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
        }
        .insight-description {
            color: #666;
            line-height: 1.4;
        }
        .price-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .price-table th,
        .price-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .price-table th {
            background-color: #f8f9fa;
            font-weight: 600;
        }
        .price-change.positive {
            color: #28a745;
        }
        .price-change.negative {
            color: #dc3545;
        }
        .trend-up::before {
            content: "↗ ";
            color: #28a745;
        }
        .trend-down::before {
            content: "↘ ";
            color: #dc3545;
        }
        .trend-stable::before {
            content: "→ ";
            color: #6c757d;
        }
        .footer {
            background-color: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
        .chart-container {
            margin: 20px 0;
            text-align: center;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Smartphone Price Tracker</h1>
            <p>Weekly Market Report - {{ generated_at | datetime }}</p>
        </div>
        
        <div class="content">
            <!-- Executive Summary -->
            <div class="section">
                <h2>📊 Executive Summary</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{{ stats.total_models }}</div>
                        <div class="stat-label">Models Tracked</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ stats.total_platforms }}</div>
                        <div class="stat-label">Platforms Monitored</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ stats.significant_changes }}</div>
                        <div class="stat-label">Significant Changes</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ stats.arbitrage_opportunities }}</div>
                        <div class="stat-label">Arbitrage Opportunities</div>
                    </div>
                </div>
            </div>
            
            <!-- Key Market Insights -->
            <div class="section">
                <h2>🔍 Key Market Insights</h2>
                <ul class="insights-list">
                    {% for insight in market_insights[:10] %}
                    <li class="insight-item {{ insight.insight_type }}">
                        <div class="insight-title">{{ insight.title }}</div>
                        <div class="insight-description">{{ insight.description }}</div>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            
            <!-- Price Analysis -->
            <div class="section">
                <h2>💰 Price Analysis</h2>
                <table class="price-table">
                    <thead>
                        <tr>
                            <th>Phone Model</th>
                            <th>Platform</th>
                            <th>Condition</th>
                            <th>Current Price</th>
                            <th>Change</th>
                            <th>Trend</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for analysis in price_analyses[:20] %}
                        <tr>
                            <td>{{ analysis.brand }} {{ analysis.phone_model }}</td>
                            <td>{{ analysis.platform }} ({{ analysis.region }})</td>
                            <td>{{ analysis.condition }}</td>
                            <td>${{ analysis.current_price | currency }}</td>
                            <td class="price-change {% if analysis.price_change_percent > 0 %}positive{% elif analysis.price_change_percent < 0 %}negative{% endif %}">
                                {% if analysis.price_change_percent %}
                                    {{ analysis.price_change_percent | percent }}%
                                {% else %}
                                    -
                                {% endif %}
                            </td>
                            <td class="trend-{{ analysis.trend_direction }}">{{ analysis.trend_direction | title }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <!-- Brand Comparison -->
            {% if summary.brand_avg_prices %}
            <div class="section">
                <h2>🏷️ Brand Comparison</h2>
                <div class="stats-grid">
                    {% for brand, avg_price in summary.brand_avg_prices.items() %}
                    <div class="stat-card">
                        <div class="stat-number">${{ avg_price | currency }}</div>
                        <div class="stat-label">{{ brand }} Average</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
            
            <!-- Charts -->
            {% if charts %}
            <div class="section">
                <h2>📈 Market Trends</h2>
                {% for chart_name, chart_data in charts.items() %}
                <div class="chart-container">
                    <h3>{{ chart_name | title }}</h3>
                    {% if chart_data %}
                    <img src="data:image/png;base64,{{ chart_data }}" alt="{{ chart_name }}">
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <!-- Platform Activity -->
            {% if summary.platform_activity %}
            <div class="section">
                <h2>🌐 Platform Activity</h2>
                <table class="price-table">
                    <thead>
                        <tr>
                            <th>Platform</th>
                            <th>Records This Week</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for platform, count in summary.platform_activity %}
                        <tr>
                            <td>{{ platform }}</td>
                            <td>{{ count }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
        </div>
        
        <div class="footer">
            <p>Generated automatically by Smartphone Price Tracker</p>
            <p>Report generated on {{ generated_at | datetime }}</p>
        </div>
    </div>
</body>
</html>
        """
    
    def _calculate_report_stats(self, 
                               price_analyses: List[PriceAnalysis], 
                               market_insights: List[MarketInsight]) -> Dict[str, int]:
        """Calculate summary statistics for the report"""
        
        unique_models = set()
        unique_platforms = set()
        significant_changes = 0
        arbitrage_opportunities = 0
        
        for analysis in price_analyses:
            unique_models.add(f"{analysis.brand} {analysis.phone_model}")
            unique_platforms.add(analysis.platform)
            
            if abs(analysis.price_change_percent) >= 10:
                significant_changes += 1
        
        for insight in market_insights:
            if insight.insight_type == 'arbitrage':
                arbitrage_opportunities += 1
        
        return {
            'total_models': len(unique_models),
            'total_platforms': len(unique_platforms),
            'significant_changes': significant_changes,
            'arbitrage_opportunities': arbitrage_opportunities
        }
    
    def _add_attachment(self, message: MIMEMultipart, file_path: str):
        """Add file attachment to email message"""
        try:
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(file_path)}'
            )
            
            message.attach(part)
            logger.debug(f"Added attachment: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {e}")
    
    def _format_currency(self, value: float) -> str:
        """Format currency value"""
        if value is None:
            return "N/A"
        return f"{value:,.2f}"
    
    def _format_percent(self, value: float) -> str:
        """Format percentage value"""
        if value is None:
            return "N/A"
        return f"{value:+.1f}"
    
    def _format_datetime(self, value: datetime) -> str:
        """Format datetime value"""
        return value.strftime("%B %d, %Y at %I:%M %p UTC")
    
    def test_email_connection(self) -> bool:
        """Test email server connection"""
        try:
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
            
            logger.info("Email connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False
    
    def save_report_to_file(self, html_content: str, file_path: str) -> bool:
        """Save HTML report to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Report saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save report to {file_path}: {e}")
            return False