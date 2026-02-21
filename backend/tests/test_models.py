import pytest
from datetime import datetime, date
from app.models.collection import Collection
from app.models.user import User


def test_create_user(db_session):
    """Test user creation"""
    user = User(
        id="test-user-123",
        username="testuser",
        email="test@example.com",
        full_name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.id == "test-user-123"
    assert user.username == "testuser"
    assert user.email == "test@example.com"


def test_create_collection(db_session):
    """Test collection creation"""
    # Create user first
    user = User(
        id="test-user-123",
        username="testuser",
        email="test@example.com"
    )
    db_session.add(user)
    db_session.commit()
    
    # Create collection
    collection = Collection(
        name="Test Collection",
        location="Test Location",
        date=date(2024, 1, 1),
        owner_id=user.id
    )
    db_session.add(collection)
    db_session.commit()
    
    assert collection.name == "Test Collection"
    assert collection.location == "Test Location"
    assert collection.owner_id == user.id
    assert collection.owner.username == "testuser"


def test_collection_cascade_delete(db_session):
    """Test that deleting a user cascades to collections"""
    user = User(
        id="test-user-123",
        username="testuser",
        email="test@example.com"
    )
    db_session.add(user)
    db_session.commit()
    
    collection = Collection(
        name="Test Collection",
        owner_id=user.id
    )
    db_session.add(collection)
    db_session.commit()
    
    collection_id = collection.id
    
    # Delete user
    db_session.delete(user)
    db_session.commit()
    
    # Collection should be deleted
    deleted_collection = db_session.query(Collection).filter(Collection.id == collection_id).first()
    assert deleted_collection is None
