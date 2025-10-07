import os
from datetime import timedelta

class Config:
    # Base directory - this is your project root
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///nas.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'YOUR EMAIL ADDRESS HERE'
    MAIL_PASSWORD = 'YOUR PASSWORD/LOGIN KEY HERE'
    MAIL_DEFAULT_SENDER = ('NAME OF SERVICE', 'YOUR EMAIL ADDRESS')
    SECURITY_PASSWORD_SALT ='I hope this works'
    
    # File Storage Configuration
    UPLOAD_FOLDER = 'PATH TO YOUR STORAGE' 
    MAX_CONTENT_LENGTH = 21474836480  # 20GB for maximum single file size
    
    # Upload Optimization
    UPLOAD_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB upload chunks
    REQUEST_TIMEOUT = 3600  # 1 hour timeout for large uploads
    SERVER_TIMEOUT = 3600   # Server-side timeout

    # Blocked file extensions (potentially dangerous files)
    BLOCKED_EXTENSIONS = {
        'bat', 'exe', 'cmd', 'sh', 'ps1', 'vbs', 'js', 'reg', 'msi', 'com', 
        'scr', 'gadget', 'application', 'msc', 'jar', 'vb', 'vbe', 'jse', 'ws', 
        'wsf', 'wsc', 'wsh', 'ps1xml', 'ps2', 'ps2xml', 'psc1', 'psc2', 'msh', 
        'msh1', 'msh2', 'mshxml', 'msh1xml', 'msh2xml', 'scf', 'lnk', 'inf', 'sys'
    }

    # Categories for file type icons (for UI purposes)
    FILE_CATEGORIES = {
        'document': {'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'pages', 'epub', 'odf', 
                    'ods', 'xls', 'xlsx', 'csv', 'ppt', 'pptx', 'odp'},
        'image': {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff', 
                 'psd', 'ai', 'raw', 'heic', 'jfif', 'tif'},
        'video': {'mp4', 'avi', 'mkv', 'mov', 'webm', 'flv', 'wmv', 'm4v', 'mpg', 
                 'mpeg', '3gp', 'h264', 'h265', 'rm', 'swf', 'vob'},
        'audio': {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'wma', 'aac', 'mid', 'midi', 
                 'aif', 'aifc', 'aiff', 'au', 'pcm'},
        'archive': {'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'iso', 'dmg', 'pkg', 
                   'deb', 'rpm', 'xz', 'tgz', 'z'},
        'code': {'py', 'java', 'c', 'cpp', 'h', 'hpp', 'html', 'css', 'scss', 'json', 
                'xml', 'yaml', 'yml', 'sql', 'php', 'rb', 'go', 'rs', 'ts', 'jsx', 'tsx'},
        'font': {'ttf', 'otf', 'woff', 'woff2', 'eot'},
        'model': {'obj', 'fbx', '3ds', 'blend', 'stl', 'dae', 'max'},
        'other': {'*'}  # Catch-all for other file types
    }
    
    # Storage Structure
    FOLDER_STRUCTURE = {
        'users': os.path.join(UPLOAD_FOLDER, 'users'),        # User-specific files
        'shared': os.path.join(UPLOAD_FOLDER, 'shared'),      # Shared files
        'system': os.path.join(UPLOAD_FOLDER, 'system'),      # System files
        'tmp': os.path.join(UPLOAD_FOLDER, 'tmp')             # Temporary upload files
    }
    
    # User Storage Settings
    DEFAULT_STORAGE_LIMIT = 50 * 1024 * 1024 * 1024  # 50GB in bytes
    WARNING_THRESHOLD = 0.75  # 75% - Show warning
    CRITICAL_THRESHOLD = 0.90  # 90% - Show critical warning
    
    # Security Headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block'
    }
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'csrf-secret-key'

    # Logging Configuration
    LOG_FOLDER = os.path.join(BASE_DIR, 'logs')
    LOG_FILENAME = 'nas.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # Video Streaming
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for video streaming
    
    # Preview Settings
    MAX_PREVIEW_SIZE = 10 * 1024 * 1024  # 10MB max for preview
    THUMBNAIL_SIZE = (200, 200)  # Thumbnail dimensions
    
    # Performance Settings for Raspberry Pi
    MAX_WORKERS = 2  # Limit number of worker processes
    THREAD_POOL_SIZE = 8  # Thread pool size for async operations
    
    # Print storage path on startup for verification
    print(f"Storage path is set to: {UPLOAD_FOLDER}")
    
    @staticmethod
    def init_directories():
        """Initialize base directory structure"""
        # Create main storage directories
        for folder in Config.FOLDER_STRUCTURE.values():
            os.makedirs(folder, exist_ok=True)
            print(f"Created/verified directory at: {folder}")
        
        # Create logs directory
        os.makedirs(Config.LOG_FOLDER, exist_ok=True)
        print(f"Created/verified logs directory at: {Config.LOG_FOLDER}")
        
        # Create temp directory with appropriate permissions
        temp_dir = os.path.join(Config.UPLOAD_FOLDER, 'tmp')
        os.makedirs(temp_dir, exist_ok=True)
        os.chmod(temp_dir, 0o777)  # Full permissions for temporary storage
        print(f"Created/verified temp directory at: {temp_dir}")

    @staticmethod
    def get_user_storage_path(user_id):
        """Get the storage path for a specific user"""
        user_path = os.path.join(Config.FOLDER_STRUCTURE['users'], str(user_id))
        os.makedirs(user_path, exist_ok=True)
        return user_path

    @staticmethod
    def get_file_category(filename):
        """Determine file category based on extension"""
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        for category, extensions in Config.FILE_CATEGORIES.items():
            if ext in extensions:
                return category
        return 'other'

    @staticmethod
    def format_size(size_in_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} PB"