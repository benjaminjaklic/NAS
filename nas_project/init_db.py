import os
from app import create_app, db
from app.models import User
from datetime import datetime

app = create_app()

with app.app_context():
    # Drop all tables and recreate them
    print("Recreating database schema...")
    db.drop_all()
    db.create_all()
    
    # Create admin user
    admin = User(
        username='YOUR ADMIN USERNAME', 
        email='EMAIL FOR THE MAIN ADMIN', 
        is_admin=True, 
        is_approved=True,
        created_at=datetime.utcnow(),
        storage_limit=1024 * 1024 * 1024 * 100,  # 100GB for admin
        storage_used=0
    )
    admin.set_password('PASSWORD FOR YOUR ADMIN ACCOUNT')  # Change this password!
    db.session.add(admin)
    db.session.commit()
    print("Admin user created!")
    
    print("Database initialized!")