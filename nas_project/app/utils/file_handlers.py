import os
import shutil
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image
import mimetypes

def get_file_type(filename):
    """Determine file type based on extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    type_map = {
        # Documents
        'pdf': 'document',
        'doc': 'document',
        'docx': 'document',
        'txt': 'document',
        'rtf': 'document',
        
        # Images
        'jpg': 'image',
        'jpeg': 'image',
        'png': 'image',
        'gif': 'image',
        'bmp': 'image',
        
        # Videos
        'mp4': 'video',
        'avi': 'video',
        'mkv': 'video',
        'mov': 'video',
        
        # Audio
        'mp3': 'audio',
        'wav': 'audio',
        'ogg': 'audio',
        
        # Archives
        'zip': 'archive',
        'rar': 'archive',
        '7z': 'archive'
    }
    
    return type_map.get(ext, 'other')

def save_file(file, user, category=None, custom_category=None):
    """Save uploaded file to appropriate directory"""
    filename = secure_filename(file.filename)
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'users', str(user.id))
    
    os.makedirs(user_dir, exist_ok=True)
    
    if category:
        user_dir = os.path.join(user_dir, category)
        os.makedirs(user_dir, exist_ok=True)
    elif custom_category:
        user_dir = os.path.join(user_dir, 'custom', custom_category)
        os.makedirs(user_dir, exist_ok=True)
    
    file_path = os.path.join(user_dir, filename)
    file.save(file_path)
    return file_path

def create_thumbnail(file_path, size=(200, 200)):
    """Create thumbnail for image files"""
    try:
        img = Image.open(file_path)
        img.thumbnail(size)
        thumb_path = f"{os.path.splitext(file_path)[0]}_thumb.jpg"
        img.save(thumb_path, "JPEG")
        return thumb_path
    except Exception as e:
        current_app.logger.error(f"Error creating thumbnail: {str(e)}")
        return None

def get_video_metadata(file_path):
    """Get basic video file information"""
    try:
        file_size = os.path.getsize(file_path)
        return {
            'size': file_size,
            'path': file_path,
            'filename': os.path.basename(file_path)
        }
    except Exception as e:
        current_app.logger.error(f"Error getting video metadata: {str(e)}")
        return None

def stream_video(file_path, start_byte=0):
    """Generator to stream video files"""
    chunk_size = current_app.config.get('CHUNK_SIZE', 1024 * 1024)
    
    with open(file_path, 'rb') as video:
        video.seek(start_byte)
        while True:
            chunk = video.read(chunk_size)
            if not chunk:
                break
            yield chunk

def delete_file(file_path):
    """Safely delete file and its thumbnails"""
    try:
        if os.path.exists(file_path):
            # Delete thumbnail if it exists
            thumb_path = f"{os.path.splitext(file_path)[0]}_thumb.jpg"
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            
            os.remove(file_path)
            
            # Remove empty directories
            dir_path = os.path.dirname(file_path)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
                
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting file: {str(e)}")
        return False