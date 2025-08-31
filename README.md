# 📱 Smartphone Price Tracker

A comprehensive Python-based tool for monitoring refurbished smartphone prices across multiple secondary market platforms and regions. Track flagship models from Google Pixel, Apple iPhone, and Samsung Galaxy series with automated weekly reports and trend analysis.

## 🌟 Features

### Core Functionality
- **Multi-Platform Monitoring**: Track prices across 12+ platforms including Swappa, Back Market, Gazelle, eBay Refurbished, and regional marketplaces
- **Global Coverage**: Monitor prices in US, Europe, Japan, and India with automatic currency conversion
- **Flagship Phone Tracking**: Focus on latest models from Apple, Google, and Samsung
- **Condition-Based Analysis**: Track prices for Excellent, Good, and Fair condition devices

### Data Analysis & Insights
- **Trend Analysis**: Calculate week-over-week price changes and identify market trends
- **Arbitrage Detection**: Find price differences across platforms and regions
- **Volatility Tracking**: Monitor price stability and market fluctuations
- **Best Deal Identification**: Automatically identify the best value propositions

### Automation & Reporting
- **Weekly HTML Reports**: Comprehensive email reports with charts and insights
- **Automated Scheduling**: Configurable scraping and reporting schedules
- **Interactive Charts**: Price trends, platform comparisons, and brand analysis
- **Export Capabilities**: CSV/Excel export for further analysis

### Technical Features
- **Robust Web Scraping**: Rate limiting, proxy support, and respectful scraping practices
- **Database Management**: PostgreSQL/SQLite support with automated cleanup
- **CLI Interface**: Full command-line interface for all operations
- **Docker Support**: Easy deployment with Docker Compose
- **Comprehensive Testing**: Unit tests with >80% code coverage

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/smartphone-price-tracker.git
   cd smartphone-price-tracker
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your email settings and API keys
   ```

3. **Start with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database:**
   ```bash
   docker-compose exec price-tracker python cli.py init
   ```

5. **Run your first scrape:**
   ```bash
   docker-compose exec price-tracker python cli.py scrape
   ```

### Local Installation

1. **Prerequisites:**
   - Python 3.11+
   - PostgreSQL (optional, SQLite used by default)
   - Redis (optional, for advanced features)

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure settings:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database:**
   ```bash
   python cli.py init
   ```

5. **Start tracking:**
   ```bash
   python cli.py scrape --region US
   ```

## 📊 Usage Examples

### Command Line Interface

```bash
# Initialize database
python cli.py init

# Run full scraping cycle
python cli.py scrape

# Scrape specific region
python cli.py scrape --region US

# Scrape specific platform
python cli.py scrape --platform Swappa

# Analyze trends
python cli.py analyze --days 30

# Generate and send report
python cli.py report --recipient user@example.com --include-charts

# Start scheduler daemon
python cli.py schedule --start

# Check system status
python cli.py status

# Generate demo data
python cli.py demo --sample-size 1000
```

### Python API

```python
from main import SmartphonePriceTracker
import asyncio

async def main():
    tracker = SmartphonePriceTracker()
    
    # Run single scraping cycle
    result = await tracker.run_full_scraping_cycle()
    print(f"Scraped {result['total_saved']} records")
    
    # Generate weekly report
    await tracker.generate_weekly_report()

asyncio.run(main())
```

### Docker Operations

```bash
# Start all services
docker-compose up -d

# Run CLI commands
docker-compose exec price-tracker python cli.py status

# View logs
docker-compose logs -f price-tracker

# Start with admin tools
docker-compose --profile admin up -d

# Access pgAdmin at http://localhost:8080
# Access Grafana at http://localhost:3000 (with monitoring profile)
```

## 🛠️ Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/price_tracker
# or for SQLite: sqlite:///./price_tracker.db

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com

# API Keys (optional)
EBAY_CLIENT_ID=your_ebay_client_id
BACK_MARKET_API_KEY=your_back_market_api_key

# Scraping Settings
SCRAPING_DELAY=2
MAX_RETRIES=3
USE_PROXY=false
PROXY_LIST=proxy1:port,proxy2:port
```

### Phone Models Configuration

Edit `config/settings.py` to customize tracked models:

```python
PHONE_MODELS = {
    "pixel": {
        "Pixel 9": ["128GB", "256GB"],
        "Pixel 9 Pro": ["128GB", "256GB", "512GB", "1TB"],
        # Add more models...
    },
    "iphone": {
        "iPhone 16": ["128GB", "256GB", "512GB"],
        # Add more models...
    }
}
```

### Platform Configuration

Add new platforms in `config/settings.py`:

```python
PLATFORMS = {
    "US": {
        "Your Platform": {
            "base_url": "https://yourplatform.com",
            "scraper_type": "html",
            "rate_limit": 1.0
        }
    }
}
```

## 📈 Reports and Analytics

### Weekly Email Reports Include:
- **Executive Summary**: Key metrics and statistics
- **Market Insights**: Arbitrage opportunities, price changes, best deals
- **Price Analysis Table**: Detailed breakdown by model and platform
- **Interactive Charts**: Trend analysis and platform comparisons
- **Brand Comparison**: Average prices across manufacturers

### Available Charts:
- Price trends over time
- Platform price comparisons
- Brand analysis and market share
- Price volatility analysis
- Regional price differences

## 🔧 Development

### Project Structure
```
smartphone-price-tracker/
├── src/
│   ├── database/          # Database models and management
│   ├── scrapers/          # Web scraping modules
│   ├── analysis/          # Price analysis and insights
│   ├── reporting/         # Email reports and charts
│   ├── scheduler/         # Task scheduling
│   └── utils/            # Logging and utilities
├── tests/                # Unit tests
├── config/               # Configuration files
├── docker/               # Docker configuration
├── cli.py               # Command line interface
├── main.py              # Main application entry
└── requirements.txt     # Python dependencies
```

### Running Tests
```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest

# Run specific test files
pytest tests/test_scrapers.py -v

# Run tests with specific markers
pytest -m "not slow" -v
```

### Adding New Platforms

1. **Create scraper class:**
   ```python
   class YourPlatformScraper(BaseScraper):
       async def scrape_phone_prices(self, phone_models):
           # Implementation here
           pass
       
       def build_search_url(self, brand, model, storage):
           # URL building logic
           pass
   ```

2. **Register in factory:**
   ```python
   ScraperFactory.register_scraper('Your Platform', YourPlatformScraper)
   ```

3. **Add to configuration:**
   ```python
   # In config/settings.py
   PLATFORMS["Region"]["Your Platform"] = {
       "base_url": "https://yourplatform.com",
       "scraper_type": "html",
       "rate_limit": 1.0
   }
   ```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🚨 Important Notes

### Ethical Scraping
- **Rate Limiting**: Respects platform rate limits and robots.txt
- **User Agent Rotation**: Uses realistic user agents
- **Proxy Support**: Optional proxy rotation for distributed requests
- **Error Handling**: Graceful failure handling without overwhelming servers

### Legal Compliance
- This tool is for educational and personal use only
- Users are responsible for compliance with platform Terms of Service
- Respect copyright and intellectual property rights
- Consider reaching out to platforms for API access

### Privacy & Security
- Never commit API keys or passwords to version control
- Use environment variables for sensitive configuration
- Rotate API keys and passwords regularly
- Monitor for unauthorized access

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation for new features
- Use type hints where appropriate

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Troubleshooting

### Common Issues

**Database Connection Errors:**
```bash
# Check database status
python cli.py status

# Reinitialize database
python cli.py init --drop-existing
```

**Email Not Sending:**
- Verify SMTP credentials in `.env`
- Check firewall settings
- For Gmail, use App Passwords instead of account password

**Scraping Issues:**
- Check internet connection
- Verify platform accessibility
- Review rate limiting settings
- Enable proxy if needed

### Getting Help
- Check the [Issues](https://github.com/yourusername/smartphone-price-tracker/issues) page
- Join our [Discord](https://discord.gg/yourserver) community
- Email support: support@yourproject.com

## 🎯 Roadmap

- [ ] Machine learning price predictions
- [ ] Mobile app for price alerts
- [ ] API endpoint for external integrations
- [ ] Real-time price monitoring
- [ ] Advanced filtering and search
- [ ] Price history visualization
- [ ] Multi-language support
- [ ] Additional regional markets

---

**⚠️ Disclaimer**: This tool is provided for educational purposes. Users are responsible for complying with platform Terms of Service and applicable laws. The developers are not responsible for any misuse or legal issues arising from the use of this tool.