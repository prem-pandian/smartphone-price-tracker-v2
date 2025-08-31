import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import tempfile
import os

from src.database import DatabaseManager, PhoneModel, Platform, PriceRecord, init_database


class TestDatabaseModels:
    """Test database model definitions"""
    
    def test_phone_model_creation(self):
        """Test PhoneModel creation"""
        phone = PhoneModel(
            brand='Apple',
            model_name='iPhone 16',
            storage_capacity='128GB'
        )
        
        assert phone.brand == 'Apple'
        assert phone.model_name == 'iPhone 16' 
        assert phone.storage_capacity == '128GB'
        assert phone.is_active is True
        assert isinstance(phone.created_at, type(datetime.utcnow()))
    
    def test_platform_creation(self):
        """Test Platform creation"""
        platform = Platform(
            name='Swappa',
            region='US',
            base_url='https://swappa.com',
            scraper_type='html',
            rate_limit=1.0
        )
        
        assert platform.name == 'Swappa'
        assert platform.region == 'US'
        assert platform.base_url == 'https://swappa.com'
        assert platform.scraper_type == 'html'
        assert platform.rate_limit == 1.0
        assert platform.is_active is True
    
    def test_price_record_creation(self):
        """Test PriceRecord creation"""
        price = PriceRecord(
            phone_model_id=1,
            platform_id=1,
            condition='Excellent',
            price=799.99,
            currency='USD',
            price_usd=799.99,
            availability=True
        )
        
        assert price.phone_model_id == 1
        assert price.platform_id == 1
        assert price.condition == 'Excellent'
        assert price.price == 799.99
        assert price.currency == 'USD'
        assert price.price_usd == 799.99
        assert price.availability is True
        assert isinstance(price.scrape_timestamp, type(datetime.utcnow()))


class TestDatabaseManager:
    """Test DatabaseManager functionality"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_url = f"sqlite:///{temp_file.name}"
        temp_file.close()
        
        yield db_url
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    def test_database_manager_initialization(self, temp_db):
        """Test DatabaseManager initialization"""
        db_manager = DatabaseManager(temp_db)
        
        assert db_manager.database_url == temp_db
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None
    
    def test_create_tables(self, temp_db):
        """Test table creation"""
        db_manager = DatabaseManager(temp_db)
        
        # Should not raise exception
        db_manager.create_tables()
        
        # Test that we can connect
        assert db_manager.test_connection() is True
    
    def test_get_session_context_manager(self, temp_db):
        """Test session context manager"""
        db_manager = DatabaseManager(temp_db)
        db_manager.create_tables()
        
        with db_manager.get_session() as session:
            assert session is not None
            
            # Add a test record
            phone = PhoneModel(
                brand='Test',
                model_name='Test Model',
                storage_capacity='128GB'
            )
            session.add(phone)
            # Session should auto-commit on exit
        
        # Verify record was saved
        with db_manager.get_session() as session:
            saved_phone = session.query(PhoneModel).filter_by(brand='Test').first()
            assert saved_phone is not None
            assert saved_phone.model_name == 'Test Model'
    
    def test_get_session_error_handling(self, temp_db):
        """Test session error handling and rollback"""
        db_manager = DatabaseManager(temp_db)
        db_manager.create_tables()
        
        with pytest.raises(Exception):
            with db_manager.get_session() as session:
                phone = PhoneModel(
                    brand='Test',
                    model_name='Test Model',
                    storage_capacity='128GB'
                )
                session.add(phone)
                session.flush()  # Force write to check constraints
                
                # Cause an error
                raise Exception("Test error")
        
        # Verify no record was saved due to rollback
        with db_manager.get_session() as session:
            saved_phone = session.query(PhoneModel).filter_by(brand='Test').first()
            assert saved_phone is None
    
    def test_init_default_data(self, temp_db):
        """Test initialization of default data"""
        db_manager = DatabaseManager(temp_db)
        db_manager.create_tables()
        
        with patch('src.database.database.PHONE_MODELS', {
            'apple': {
                'iPhone 16': ['128GB', '256GB']
            }
        }), patch('src.database.database.PLATFORMS', {
            'US': {
                'Swappa': {
                    'base_url': 'https://swappa.com',
                    'scraper_type': 'html',
                    'rate_limit': 1.0
                }
            }
        }):
            db_manager.init_default_data()
        
        with db_manager.get_session() as session:
            # Check phone models were created
            phones = session.query(PhoneModel).all()
            assert len(phones) >= 2  # 2 storage options
            
            # Check platforms were created
            platforms = session.query(Platform).all()
            assert len(platforms) >= 1
            
            swappa = session.query(Platform).filter_by(name='Swappa').first()
            assert swappa is not None
            assert swappa.region == 'US'
    
    def test_save_price_records(self, temp_db):
        """Test saving price records"""
        db_manager = DatabaseManager(temp_db)
        db_manager.create_tables()
        
        with db_manager.get_session() as session:
            # Create test phone model and platform
            phone = PhoneModel(brand='Apple', model_name='iPhone 16', storage_capacity='128GB')
            session.add(phone)
            session.flush()
            
            platform = Platform(
                name='Swappa',
                region='US', 
                base_url='https://swappa.com',
                scraper_type='html'
            )
            session.add(platform)
            session.flush()
            
            # Test data
            price_records = [
                {
                    'phone_model_id': phone.id,
                    'platform_id': platform.id,
                    'condition': 'Excellent',
                    'price': 799.99,
                    'currency': 'USD',
                    'price_usd': 799.99,
                    'availability': True
                },
                {
                    'phone_model_id': phone.id,
                    'platform_id': platform.id,
                    'condition': 'Good',
                    'price': 749.99,
                    'currency': 'USD',
                    'price_usd': 749.99,
                    'availability': True
                }
            ]
            
            success = db_manager.save_price_records(session, price_records, 'test_session')
            assert success is True
            
            # Verify records were saved
            saved_records = session.query(PriceRecord).all()
            assert len(saved_records) == 2
            
            for record in saved_records:
                assert record.scrape_session_id == 'test_session'
    
    def test_get_phone_models(self, temp_db):
        """Test getting phone models"""
        db_manager = DatabaseManager(temp_db)
        db_manager.create_tables()
        
        with db_manager.get_session() as session:
            # Add test data
            active_phone = PhoneModel(
                brand='Apple',
                model_name='iPhone 16',
                storage_capacity='128GB',
                is_active=True
            )
            inactive_phone = PhoneModel(
                brand='Apple',
                model_name='iPhone 15',
                storage_capacity='128GB',
                is_active=False
            )
            session.add(active_phone)
            session.add(inactive_phone)
            session.commit()
            
            # Test getting active only
            active_models = db_manager.get_phone_models(session, active_only=True)
            assert len(active_models) == 1
            assert active_models[0].model_name == 'iPhone 16'
            
            # Test getting all
            all_models = db_manager.get_phone_models(session, active_only=False)
            assert len(all_models) == 2
    
    def test_cleanup_old_records(self, temp_db):
        """Test cleanup of old price records"""
        db_manager = DatabaseManager(temp_db)
        db_manager.create_tables()
        
        with db_manager.get_session() as session:
            # Create test phone and platform
            phone = PhoneModel(brand='Apple', model_name='iPhone 16', storage_capacity='128GB')
            platform = Platform(name='Swappa', region='US', base_url='https://swappa.com', scraper_type='html')
            session.add(phone)
            session.add(platform)
            session.flush()
            
            # Create old and new price records
            old_record = PriceRecord(
                phone_model_id=phone.id,
                platform_id=platform.id,
                condition='Excellent',
                price=799.99,
                currency='USD',
                scrape_timestamp=datetime.utcnow() - timedelta(days=120)
            )
            
            new_record = PriceRecord(
                phone_model_id=phone.id,
                platform_id=platform.id,
                condition='Excellent',
                price=799.99,
                currency='USD',
                scrape_timestamp=datetime.utcnow() - timedelta(days=30)
            )
            
            session.add(old_record)
            session.add(new_record)
            session.commit()
            
            # Cleanup records older than 90 days
            deleted_count = db_manager.cleanup_old_records(session, keep_days=90)
            
            assert deleted_count == 1
            
            # Verify only new record remains
            remaining_records = session.query(PriceRecord).all()
            assert len(remaining_records) == 1
            assert remaining_records[0].scrape_timestamp > (datetime.utcnow() - timedelta(days=90))


class TestInitDatabase:
    """Test database initialization function"""
    
    @patch('src.database.database.db_manager')
    def test_init_database(self, mock_db_manager):
        """Test init_database function"""
        init_database()
        
        mock_db_manager.create_tables.assert_called_once()
        mock_db_manager.init_default_data.assert_called_once()