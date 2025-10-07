from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import db
import logging
import sqlite3
from flask import current_app

# File Tags association table (many-to-many)
file_tags = db.Table('file_tags',
    db.Column('file_id', db.Integer, db.ForeignKey('file.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
    # Storage
    storage_limit = db.Column(db.BigInteger)
    storage_used = db.Column(db.BigInteger)
    
    # Status
    is_admin = db.Column(db.Boolean)
    is_approved = db.Column(db.Boolean)
    is_demo = db.Column(db.Boolean, default=False)  # NEW FIELD
    
    # Timestamps
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime)
    
    # Relationships
    files = db.relationship('File', backref='user', lazy='dynamic')
    created_groups = db.relationship('Group', backref='creator', lazy='dynamic', foreign_keys='Group.creator_id')
    
    groups = db.relationship('Group', secondary='user_groups', 
                            backref=db.backref('members', lazy='dynamic'),
                            overlaps="users,user_groups")
    
    user_groups = db.relationship('UserGroups', back_populates='user', 
                                lazy='dynamic', overlaps="groups,members")
    
    tags = db.relationship('Tag', backref='creator', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_storage_percentage(self):
        if not self.storage_limit or self.storage_limit == 0:
            return 100
        return (self.storage_used / self.storage_limit) * 100
    
    def get_storage_usage(self):
        return self.storage_used or 0
    
    def can_upload(self, file_size):
        if not self.storage_limit:
            return True
        return self.storage_used + file_size <= self.storage_limit



class UserGroups(db.Model):
    __tablename__ = 'user_groups'
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete="CASCADE"), primary_key=True)
    is_admin = db.Column(db.Boolean)

    user = db.relationship('User', backref=db.backref('user_groups_assoc', lazy='dynamic', cascade="all, delete"),
                           overlaps="groups,members,user_groups")
    
    group = db.relationship('Group', backref=db.backref('users', lazy='dynamic', cascade="all, delete"),
                            overlaps="groups,members")

    def __repr__(self):
        return f'<UserGroups {self.user_id} in {self.group_id}>'


class Tag(db.Model):
    __tablename__ = 'tag'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20), default='#6c757d')  # Default gray
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_system = db.Column(db.Boolean, default=False)  # System tags can't be deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Tag {self.name}>'


class File(db.Model):
    __tablename__ = 'file'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.BigInteger)
    category = db.Column(db.String(50))
    path = db.Column(db.String(512), nullable=False, unique=True)
    is_public = db.Column(db.Boolean)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime)
    last_accessed = db.Column(db.DateTime)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete='SET NULL'))
    
    # Tags relationship
    tags = db.relationship('Tag', secondary=file_tags, backref=db.backref('files', lazy='dynamic'))
    
    # Compatibility properties
    @property
    def filepath(self):
        return self.path
    
    @filepath.setter
    def filepath(self, value):
        self.path = value
        
    @property
    def filetype(self):
        return self.file_type
    
    @filetype.setter
    def filetype(self, value):
        self.file_type = value
        
    @property
    def filesize(self):
        return self.file_size
    
    @filesize.setter
    def filesize(self, value):
        self.file_size = value
    
    def __repr__(self):
        return f'<File {self.filename}>'
    
    def update_last_accessed(self):
        """Update the last accessed timestamp"""
        self.last_accessed = datetime.utcnow()
        db.session.commit()
    
    def is_archive(self):
        """Check if the file is an archive file (zip, rar, etc.)"""
        return self.filename.lower().endswith(('.zip', '.rar', '.7z', '.tar.gz', '.tar'))


class Group(db.Model):
    __tablename__ = 'group'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Files in the group
    files = db.relationship('File', backref='group', lazy='dynamic')
    
    def __repr__(self):
        return f'<Group {self.name}>'
    
    def is_member(self, user_id):
        """Check if a user is a member of this group"""
        return UserGroups.query.filter_by(group_id=self.id, user_id=user_id).first() is not None
    
    def is_admin(self, user_id):
        """Check if a user is an admin of this group"""
        user_group = UserGroups.query.filter_by(group_id=self.id, user_id=user_id).first()
        return user_group is not None and user_group.is_admin


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime)
    
    # Relationship
    user = db.relationship('User', backref='activities')
    
    def __repr__(self):
        return f'<ActivityLog {self.action} by {self.user_id}>'


class StorageRequest(db.Model):
    __tablename__ = 'storage_request'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_size = db.Column(db.BigInteger, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20))
    created_at = db.Column(db.DateTime)
    responded_at = db.Column(db.DateTime)
    responded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='storage_requests')
    responder = db.relationship('User', foreign_keys=[responded_by], backref='handled_requests')
    
    def __repr__(self):
        return f'<StorageRequest by {self.user_id} for {self.requested_size} bytes>'


class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50))
    read = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime)
    
    # Relationship
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification for {self.user_id}>'


def check_and_update_tables():
    """Check and update database tables if needed
    This function is called during app initialization to ensure all tables exist and
    have the required columns.
    """
    import logging
    import sqlite3
    
    try:
        # Get database path from current app context
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Log tables found
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logging.info(f"Database tables: {[table[0] for table in tables]}")
        
        conn.close()
        logging.info("Database structure check completed")
        
    except Exception as e:
        logging.error(f"Error checking database structure: {str(e)}")


def initialize_system_tags():
    """Create system tags if they don't exist"""
    try:
        # Check for FOLDER tag
        folder_tag = Tag.query.filter_by(name='FOLDER', is_system=True).first()
        if not folder_tag:
            folder_tag = Tag(name='FOLDER', color='#ffc107', is_system=True)
            db.session.add(folder_tag)
            print("Created system tag: FOLDER")
        
        # Create other system tags as needed
        system_tags = [
            {'name': 'IMPORTANT', 'color': '#dc3545'},
            {'name': 'WORK', 'color': '#0d6efd'},
            {'name': 'PERSONAL', 'color': '#198754'}
        ]
        
        for tag_info in system_tags:
            tag = Tag.query.filter_by(name=tag_info['name'], is_system=True).first()
            if not tag:
                tag = Tag(name=tag_info['name'], color=tag_info['color'], is_system=True)
                db.session.add(tag)
                print(f"Created system tag: {tag_info['name']}")
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing system tags: {str(e)}")