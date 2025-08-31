# 🚀 Deploying to Render.com

This guide walks you through deploying the Smartphone Price Tracker to [Render.com](https://render.com), which provides excellent support for Python applications, PostgreSQL databases, and background workers.

## 🌟 Why Render.com?

- **Free Tier**: PostgreSQL database, Redis, and web services with generous limits
- **Automatic Scaling**: Services scale automatically based on demand  
- **Background Workers**: Built-in support for long-running tasks
- **Cron Jobs**: Native support for scheduled tasks
- **Easy Deployment**: Git-based deployment with automatic builds
- **SSL**: Free SSL certificates for all services
- **Environment Management**: Secure environment variable management

## 📋 Prerequisites

1. **GitHub Repository**: Push your code to GitHub
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **Email Configuration**: Gmail account with App Password (for reports)

## 🚀 Quick Deploy with Render Blueprint

### Option 1: One-Click Deploy (Easiest)

1. **Click Deploy Button** (add this to your README):
   ```markdown
   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/yourusername/smartphone-price-tracker)
   ```

2. **Configure Environment Variables** in the Render dashboard:
   - `SMTP_USERNAME`: Your Gmail address
   - `SMTP_PASSWORD`: Your Gmail App Password
   - `EMAIL_FROM`: Your Gmail address  
   - `EMAIL_TO`: Recipient email(s)

### Option 2: Manual Setup

## 📖 Step-by-Step Manual Deployment

### Step 1: Create Render Services

#### 1.1 Create PostgreSQL Database

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `smartphone-price-tracker-db`
   - **Database Name**: `smartphone_prices` 
   - **User**: `pricetracker`
   - **Region**: Choose closest to your users
   - **Plan**: Free (sufficient for testing)

#### 1.2 Create Redis Instance

1. Click **"New +"** → **"Redis"**
2. Configure:
   - **Name**: `smartphone-price-tracker-redis`
   - **Plan**: Free
   - **Region**: Same as database

#### 1.3 Create Web Service (Dashboard)

1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `smartphone-price-tracker-web`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements-render.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app`
   - **Plan**: Free (upgrade for production)

#### 1.4 Create Background Worker

1. Click **"New +"** → **"Background Worker"**
2. Connect the same GitHub repository
3. Configure:
   - **Name**: `smartphone-price-tracker-worker`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements-render.txt`
   - **Start Command**: `python worker.py`
   - **Plan**: Free

#### 1.5 Create Cron Job

1. Click **"New +"** → **"Cron Job"**
2. Connect the same GitHub repository  
3. Configure:
   - **Name**: `smartphone-price-tracker-scheduler`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements-render.txt`
   - **Command**: `python cli.py scrape && python cli.py report`
   - **Schedule**: `0 6 * * 1` (Every Monday at 6 AM UTC)
   - **Plan**: Free

### Step 2: Configure Environment Variables

For **each service** (web, worker, cron), add these environment variables:

#### Database Configuration (Auto-generated)
```bash
# These are automatically set by Render when you link services
DATABASE_URL=postgresql://username:password@hostname:5432/database
REDIS_URL=redis://username:password@hostname:6379
```

#### Required Email Configuration
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

#### Optional API Keys
```bash
EBAY_CLIENT_ID=your_ebay_client_id
EBAY_CLIENT_SECRET=your_ebay_client_secret
BACK_MARKET_API_KEY=your_back_market_api_key
```

#### Application Settings
```bash
LOG_LEVEL=INFO
SCRAPING_DELAY=2
MAX_RETRIES=3
TIMEOUT=30
USE_PROXY=false
DEFAULT_CURRENCY=USD
PRICE_CHANGE_THRESHOLD=5.0
```

### Step 3: Link Services

1. **For Web Service**:
   - Go to Environment tab
   - Add DATABASE_URL: Select your PostgreSQL database
   - Add REDIS_URL: Select your Redis instance

2. **For Background Worker** (same as web service)
3. **For Cron Job** (same as web service)

### Step 4: Deploy and Initialize

1. **Deploy Services**: All services should auto-deploy after configuration
2. **Initialize Database**: Using Render Shell or Logs:
   ```bash
   # In the web service shell or check worker logs
   python cli.py init
   ```
3. **Test the Setup**:
   ```bash
   python cli.py status
   python cli.py demo --sample-size 50
   ```

## 🎯 Service Architecture on Render

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Service   │    │Background Worker│    │   Cron Job      │
│  (Dashboard)    │    │   (Scraping)    │    │  (Scheduled)    │
│                 │    │                 │    │                 │
│ • Flask app     │    │ • Continuous    │    │ • Weekly runs   │
│ • Health checks │    │ • Price scraping│    │ • Email reports │
│ • API endpoints │    │ • Data analysis │    │ • Maintenance   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   Database      │
                    │                 │
                    │ • Price data    │
                    │ • Phone models  │
                    │ • Platforms     │
                    └─────────────────┘
```

## 🔧 Configuration Files for Render

### requirements-render.txt (Optimized)
```txt
# Lighter requirements for Render deployment
requests>=2.31.0
beautifulsoup4>=4.12.2
sqlalchemy>=2.0.23
psycopg2-binary>=2.9.9
pandas>=2.1.4
matplotlib>=3.8.2
flask>=3.0.0
gunicorn>=21.2.0
# ... (see full file)
```

### render.yaml (Blueprint)
```yaml
# Complete service definition
services:
  - type: pserv
    name: smartphone-price-tracker-db
  - type: redis  
    name: smartphone-price-tracker-redis
  - type: web
    name: smartphone-price-tracker-web
    startCommand: gunicorn --bind 0.0.0.0:$PORT app:app
  # ... (see full file)
```

## 📊 Monitoring and Management

### Access Your Services

- **Dashboard**: `https://your-web-service.onrender.com`
- **API Status**: `https://your-web-service.onrender.com/api/status`
- **Health Check**: `https://your-web-service.onrender.com/health`
- **Render Dashboard**: Monitor all services at dashboard.render.com

### View Logs

1. Go to your service in Render Dashboard
2. Click on **"Logs"** tab
3. Monitor real-time logs for debugging

### Scale Services

1. Go to service settings
2. Upgrade plan for more resources:
   - **Starter**: $7/month per service
   - **Standard**: $25/month per service
   - **Pro**: $85/month per service

## 🛠️ Development and Testing

### Test Locally Before Deploy

```bash
# Set environment variables for local testing
export DATABASE_URL=postgresql://user:pass@localhost:5432/test_db
export REDIS_URL=redis://localhost:6379/0

# Test web service
python app.py

# Test worker
python worker.py

# Test CLI
python cli.py status
```

### Deploy New Changes

1. **Push to GitHub**: Changes auto-deploy on git push
2. **Manual Deploy**: Use "Manual Deploy" button in dashboard
3. **Rollback**: Use "Rollback" if issues occur

## 💰 Cost Optimization

### Free Tier Limits
- **PostgreSQL**: 1GB storage, 1 million rows
- **Redis**: 25MB memory
- **Web Service**: 750 hours/month
- **Background Worker**: 750 hours/month  
- **Cron Jobs**: Unlimited runs

### Optimization Tips

1. **Efficient Scraping**: Use longer delays, respect rate limits
2. **Database Cleanup**: Regular cleanup of old records
3. **Image Optimization**: Minimize Docker image size
4. **Monitoring**: Use Render metrics to monitor usage

### Upgrade Path

When you outgrow free tier:
- **Database**: Upgrade to Starter ($7/month) for 4GB
- **Web Service**: Upgrade to Starter for always-on service
- **Worker**: Keep on free tier unless needed 24/7

## 🚨 Troubleshooting

### Common Issues

**Database Connection Errors**:
```bash
# Check environment variables in service settings
# Verify DATABASE_URL format
# Check database service status
```

**Worker Not Running**:
```bash
# Check worker logs in Render dashboard
# Verify all environment variables are set
# Check build command succeeded
```

**Email Not Sending**:
```bash
# Verify Gmail App Password (not account password)
# Check SMTP settings
# Test with curl or Python script
```

**Build Failures**:
```bash
# Check requirements-render.txt syntax
# Verify Python version compatibility
# Check build logs for specific errors
```

### Getting Help

1. **Render Docs**: [render.com/docs](https://render.com/docs)
2. **Community**: [Render Community Discord](https://discord.gg/render)
3. **Support**: Email support@render.com for paid plans

## 🎉 Success Checklist

- [ ] All services deployed and running
- [ ] Database initialized with phone models
- [ ] Environment variables configured
- [ ] Web dashboard accessible
- [ ] Background worker processing data
- [ ] Cron job scheduled for weekly runs
- [ ] Email reports working
- [ ] Health checks passing
- [ ] Monitoring and logs reviewed

## 📈 Next Steps

1. **Custom Domain**: Add your own domain to web service
2. **SSL Certificate**: Automatically provided by Render
3. **Monitoring**: Set up alerts for service health
4. **Backup**: Regular database backups (paid plans)
5. **Analytics**: Add Google Analytics to dashboard
6. **API Keys**: Obtain platform API keys for better access
7. **Scaling**: Monitor usage and upgrade plans as needed

## 🔒 Security Best Practices

- Use environment variables for all secrets
- Enable 2FA on Render account
- Regularly rotate API keys and passwords
- Monitor access logs
- Keep dependencies updated
- Use strong passwords for database

---

**🎯 Pro Tip**: Start with the free tier to test everything, then upgrade specific services as needed. Render's pay-as-you-scale model makes it perfect for growing applications!

**⚡ Quick Deploy**: Once configured, deploying updates is as simple as `git push` - Render handles the rest automatically!