from app import create_app
from app.config import Config

app = create_app()

def cleanup_orphaned_files():
    """Remove files and folders for users that no longer exist in the database"""
    print("Checking for orphaned files...")
    from app.models import User
    import os
    import shutil
    
    # Get all valid user IDs from the database
    with app.app_context():
        valid_user_ids = [str(user.id) for user in User.query.all()]
    
    # Check user directories
    user_storage_path = os.path.join(Config.UPLOAD_FOLDER, 'users')
    if os.path.exists(user_storage_path):
        for folder_name in os.listdir(user_storage_path):
            if folder_name not in valid_user_ids:
                folder_path = os.path.join(user_storage_path, folder_name)
                if os.path.isdir(folder_path):
                    print(f"Removing orphaned user directory: {folder_path}")
                    shutil.rmtree(folder_path)

if __name__ == '__main__':
    # Initialize storage directories
    Config.init_directories()
    print(f"Storage path is set to: {Config.UPLOAD_FOLDER}")
    
    # Cleanup orphaned files
    cleanup_orphaned_files()
    
    app.run(
        host='0.0.0.0',  # Only listen on localhost since Nginx handles external connections
        port=5000,
        debug=False 
    )