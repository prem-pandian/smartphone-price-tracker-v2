# 🚀 Setup Guide

This guide will help you get the Smartphone Price Tracker up and running quickly.

## 📋 Prerequisites

### Required
- Python 3.9+ (Python 3.11 recommended)
- Git

### Optional (for advanced features)
- Docker & Docker Compose (recommended for production)
- PostgreSQL 12+ (SQLite used by default)
- Redis 6+ (for caching and background tasks)

## 🐳 Quick Start with Docker (Recommended)

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/yourusername/smartphone-price-tracker.git
cd smartphone-price-tracker

# Copy and configure environment file
cp .env.example .env
```

### 2. Edit Configuration

Edit `.env` file with your settings:

```bash
# Required: Email configuration for reports
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password  # Use App Password for Gmail
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com

# Optional: API keys for better data access
EBAY_CLIENT_ID=your_ebay_client_id
EBAY_CLIENT_SECRET=your_ebay_client_secret
BACK_MARKET_API_KEY=your_back_market_api_key

# Database will be auto-configured with Docker
DATABASE_URL=postgresql://pricetracker:secretpass@postgres:5432/smartphone_prices
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f price-tracker
```

### 4. Initialize Database

```bash
# Initialize database with phone models and platforms
docker-compose exec price-tracker python cli.py init

# Verify setup
docker-compose exec price-tracker python cli.py status
```

### 5. Run Your First Scrape

```bash
# Generate demo data for testing
docker-compose exec price-tracker python cli.py demo --sample-size 100

# Or run actual scraping (use demo first to test)
docker-compose exec price-tracker python cli.py scrape --region US --dry-run

# Generate test report
docker-compose exec price-tracker python cli.py report --recipient your@email.com
```

## 💻 Local Development Setup

### 1. Python Environment

```bash
# Clone repository
git clone https://github.com/yourusername/smartphone-price-tracker.git
cd smartphone-price-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env  # or your preferred editor
```

**Minimal .env configuration:**
```bash
# Use SQLite for local development
DATABASE_URL=sqlite:///./price_tracker.db

# Email configuration (required for reports)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=your@email.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/price_tracker.log
```

### 3. Initialize and Test

```bash
# Initialize database
python cli.py init

# Check system status
python cli.py status

# Generate demo data
python cli.py demo --sample-size 50

# Run analysis
python cli.py analyze --days 30

# Generate test report
python cli.py report --recipient your@email.com --include-charts
```

## 📧 Email Configuration

### Gmail Setup (Recommended)

1. **Enable 2-Factor Authentication** in your Google Account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Select "Mail" and your device
   - Use the generated 16-character password in `.env`

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com,another@example.com
```

### Other Email Providers

**Outlook/Hotmail:**
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

**Yahoo:**
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

**Custom SMTP:**
```bash
SMTP_SERVER=mail.yourprovider.com
SMTP_PORT=587  # or 465 for SSL
```

## 🛠️ Advanced Configuration

### Database Setup (Optional)

#### PostgreSQL (Production)

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian
brew install postgresql  # macOS

# Create database
sudo -u postgres createuser pricetracker
sudo -u postgres createdb smartphone_prices -O pricetracker
sudo -u postgres psql -c "ALTER USER pricetracker PASSWORD 'yourpassword';"

# Update .env
DATABASE_URL=postgresql://pricetracker:yourpassword@localhost:5432/smartphone_prices
```

#### Redis (Optional)

```bash
# Install Redis
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis  # macOS

# Start Redis
sudo systemctl start redis-server  # Linux
brew services start redis  # macOS

# Update .env
REDIS_URL=redis://localhost:6379/0
```

### Proxy Configuration (Optional)

For large-scale scraping or geo-restricted content:

```bash
# Add to .env
USE_PROXY=true
PROXY_LIST=proxy1.com:8080,proxy2.com:8080,proxy3.com:8080
```

### API Keys (Optional)

Obtain API keys for better data access:

#### eBay Developer Account
1. Visit [eBay Developers](https://developer.ebay.com/)
2. Create account and app
3. Get Client ID and Client Secret

#### Back Market API
1. Contact Back Market for API access
2. Add API key to configuration

```bash
# Add to .env
EBAY_CLIENT_ID=your_ebay_client_id
EBAY_CLIENT_SECRET=your_ebay_client_secret
BACK_MARKET_API_KEY=your_back_market_api_key
```

## 🔧 Customization

### Adding Phone Models

Edit `config/settings.py`:

```python
PHONE_MODELS = {
    "pixel": {
        "Pixel 9": ["128GB", "256GB"],
        "Pixel 8a": ["128GB", "256GB"],  # Add new model
    },
    "iphone": {
        "iPhone 16": ["128GB", "256GB", "512GB"],
        "iPhone 15": ["128GB", "256GB"],  # Add older model
    }
}
```

### Adding Platforms

1. **Add platform configuration:**

```python
# In config/settings.py
PLATFORMS = {
    "US": {
        "Your Platform": {
            "base_url": "https://yourplatform.com",
            "scraper_type": "html",
            "rate_limit": 2.0
        }
    }
}
```

2. **Create scraper (optional):**

```python
# In src/scrapers/your_platform_scraper.py
from .base_scraper import BaseScraper, PriceData

class YourPlatformScraper(BaseScraper):
    async def scrape_phone_prices(self, phone_models):
        # Implementation here
        pass
    
    def build_search_url(self, brand, model, storage):
        # URL building logic
        pass
```

3. **Register scraper:**

```python
# In src/scrapers/scraper_factory.py
from .your_platform_scraper import YourPlatformScraper

ScraperFactory.register_scraper('Your Platform', YourPlatformScraper)
```

## 📊 Production Deployment

### Docker Compose with Monitoring

```bash
# Start with all services including monitoring
docker-compose --profile admin --profile monitoring up -d

# Access services
# Main app: Check logs with docker-compose logs -f price-tracker  
# pgAdmin: http://localhost:8080
# Grafana: http://localhost:3000
```

### Environment Variables for Production

```bash
# .env for production
DATABASE_URL=postgresql://pricetracker:strong_password@postgres:5432/smartphone_prices
REDIS_URL=redis://redis:6379/0

# Strong passwords
POSTGRES_PASSWORD=your_strong_db_password
REDIS_PASSWORD=your_strong_redis_password
PGADMIN_PASSWORD=your_strong_admin_password
GRAFANA_PASSWORD=your_strong_grafana_password

# Email settings
SMTP_USERNAME=your_production_email@company.com
SMTP_PASSWORD=your_production_app_password
EMAIL_TO=team@company.com,alerts@company.com

# Performance tuning
SCRAPING_DELAY=3  # Be more conservative in production
MAX_RETRIES=5
TIMEOUT=60
```

### Backup and Maintenance

```bash
# Backup database
docker-compose exec postgres pg_dump -U pricetracker smartphone_prices > backup_$(date +%Y%m%d).sql

# Database maintenance
docker-compose exec price-tracker python cli.py analyze --days 90

# Log rotation (add to crontab)
# 0 0 * * * find /path/to/logs -name "*.log" -mtime +30 -delete
```

## 🧪 Testing Your Setup

### Verification Checklist

```bash
# 1. Check system status
python cli.py status
# Should show: ✅ Database: Connected, ✅ Email: Configuration valid

# 2. Test database operations
python cli.py init
# Should create tables and populate default data

# 3. Test scraping (with demo data)
python cli.py demo --sample-size 10
# Should create sample price records

# 4. Test analysis
python cli.py analyze --days 30
# Should show market insights and trends

# 5. Test reporting
python cli.py report --recipient your@email.com --save-html report.html
# Should generate and send HTML report

# 6. Check logs
tail -f logs/price_tracker.log
# Should show recent activity without errors
```

### Common Issues and Solutions

**Database Connection Failed:**
```bash
# Check database status
docker-compose logs postgres  # Docker
sudo systemctl status postgresql  # Linux local

# Reinitialize if needed
python cli.py init --drop-existing
```

**Email Not Sending:**
```bash
# Test email configuration
python -c "from src.reporting import EmailReporter; from config.settings import settings; reporter = EmailReporter({'smtp_server': settings.smtp_server, 'smtp_port': settings.smtp_port, 'smtp_username': settings.smtp_username, 'smtp_password': settings.smtp_password, 'email_from': settings.email_from}); print('Success!' if reporter.test_email_connection() else 'Failed!')"
```

**Scraping Issues:**
```bash
# Test with single platform
python cli.py scrape --platform Swappa --dry-run

# Check rate limits
# Edit config/settings.py and increase rate_limit values
```

**Permission Issues (Linux):**
```bash
# Fix log directory permissions
sudo chown -R $USER:$USER logs/
chmod 755 logs/
```

## 🚀 Next Steps

Once your setup is working:

1. **Schedule Regular Runs:**
   ```bash
   # Add to crontab for weekly scraping
   0 6 * * 1 cd /path/to/project && python cli.py scrape
   0 8 * * 1 cd /path/to/project && python cli.py report
   ```

2. **Monitor Performance:**
   - Check logs regularly
   - Monitor database size
   - Review email reports

3. **Customize for Your Needs:**
   - Add specific phone models
   - Include regional platforms
   - Adjust scraping frequency
   - Customize report content

4. **Scale Up:**
   - Add more regions
   - Implement real-time monitoring
   - Set up alerting for good deals
   - Create custom analysis scripts

## 💡 Tips for Success

- **Start Small**: Begin with demo data and one region
- **Monitor Respectfully**: Use appropriate delays and respect robots.txt
- **Keep Updated**: Regularly update dependencies and configurations
- **Backup Data**: Regularly backup your price history database
- **Stay Legal**: Always respect platform Terms of Service

For additional help, check the main [README.md](README.md) or create an issue on GitHub.