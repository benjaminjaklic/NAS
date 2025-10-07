from flask import Blueprint, render_template, request, jsonify, current_app, send_file, abort, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, File, ActivityLog, StorageRequest, Tag
import os
import mimetypes
from datetime import datetime
import requests
from PyPDF2 import PdfReader

files_bp = Blueprint('files', __name__, url_prefix='/files')

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    # Only block potentially dangerous files
    return ext not in current_app.config['BLOCKED_EXTENSIONS']

@files_bp.route('/dashboard')
@login_required
def dashboard():
    # Get filter parameters
    print("DEBUG >> Current user:", current_user.username, current_user.id)
    print("DEBUG >> Total files:", File.query.count())
    print("DEBUG >> My files:", File.query.filter_by(user_id=current_user.id).all())

    tag_id = request.args.get('tag')
    
    # Base query - only get files belonging to the current user
    query = File.query.filter_by(user_id=current_user.id)
    
    # Apply tag filter if specified
    if tag_id:
        try:
            tag_id = int(tag_id)
            query = query.join(File.tags).filter(Tag.id == tag_id)
        except ValueError:
            pass
    
    # Get files ordered by upload date
    files = query.order_by(File.uploaded_at.desc()).all()
    
    # Get all tags for tag selection
    tags = Tag.query.filter((Tag.user_id == current_user.id) | (Tag.is_system == True)).all()
    
    return render_template('files/dashboard.html', files=files, tags=tags)

@files_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    # Log the request details
    print(f"===== UPLOAD REQUEST =====")
    print(f"User: {current_user.username} (ID: {current_user.id})")
    print(f"Content-Type: {request.content_type}")
    print(f"Form keys: {list(request.form.keys())}")
    print(f"Files keys: {list(request.files.keys())}")
    print(f"Headers: {request.headers}")
    
    if 'file' not in request.files:
        print("Error: No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        print("Error: No selected file - empty filename")
        return jsonify({'error': 'No selected file'}), 400

    print(f"File being uploaded: {file.filename}")
    print(f"File content type: {file.content_type}")
    
    # Check if file type is allowed
    if not allowed_file(file.filename):
        print(f"Error: File type not allowed: {file.filename}")
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        return jsonify({'error': f'File type not allowed: {ext}'}), 400
    
    try:
        filename = secure_filename(file.filename)
        category = request.form.get('category', 'other')
        
        # Get tags if any were selected
        tag_ids = request.form.getlist('tags')
        selected_tags = []
        if tag_ids:
            try:
                selected_tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
                print(f"Selected tags: {[tag.name for tag in selected_tags]}")
            except Exception as e:
                print(f"Error retrieving tags: {str(e)}")
        
        # Log more details
        print(f"Attempting to upload file: {filename}, category: {category}")
        print(f"User storage: used={current_user.storage_used}, limit={current_user.storage_limit}")
        
        # Create user directory if it doesn't exist
        user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id))
        print(f"User directory path: {user_dir}")
        
        # Check if directory exists and is writable
        if not os.path.exists(user_dir):
            print(f"Creating user directory: {user_dir}")
            try:
                os.makedirs(user_dir, exist_ok=True)
                print(f"User directory created successfully")
            except Exception as e:
                print(f"Error creating user directory: {str(e)}")
                return jsonify({'error': f'Could not create storage directory: {str(e)}'}), 500
        
        # Generate unique filename if file already exists
        base_name, extension = os.path.splitext(filename)
        counter = 1
        final_filename = filename
        while os.path.exists(os.path.join(user_dir, final_filename)):
            final_filename = f"{base_name}_{counter}{extension}"
            counter += 1
        
        # Log the final filename
        print(f"Final filename: {final_filename}")
        
        # Create the full file path
        file_path = os.path.join(user_dir, final_filename)
        print(f"Full file path: {file_path}")
        
        # Save file temporarily to check size
        temp_path = os.path.join(user_dir, f"temp_{final_filename}")
        print(f"Saving to temporary path: {temp_path}")
        file.save(temp_path)
        
        # Get file size
        file_size = os.path.getsize(temp_path)
        print(f"File size: {file_size} bytes")
        
        # Check storage limit
        if current_user.storage_used + file_size > current_user.storage_limit:
            print(f"Storage limit exceeded. Needed: {file_size}, Available: {current_user.storage_limit - current_user.storage_used}")
            os.remove(temp_path)  # Remove the temporary file
            return jsonify({'error': 'Storage limit exceeded'}), 400
        
        # Move from temp file to final location
        try:
            os.rename(temp_path, file_path)
            print(f"File moved from temporary location to final path")
        except Exception as e:
            print(f"Error moving file from temp location: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({'error': f'Error saving file: {str(e)}'}), 500
        
        # Update user's storage usage
        current_user.storage_used += file_size
        print(f"Updated user storage: {current_user.storage_used}")
        
        # Get file type
        file_type = category
        if not file_type:
            mime_type = mimetypes.guess_type(filename)[0]
            if mime_type:
                file_type = mime_type.split('/')[0]
            else:
                file_type = 'other'
        
        print(f"File type determined as: {file_type}")
        
        # Create file record
        new_file = File(
            filename=final_filename,
            original_filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            category=category,
            path=file_path,
            user_id=current_user.id,
            uploaded_at=datetime.utcnow(),
            is_public=False
        )
        
        print(f"File record created")
        
        # Add selected tags to the file
        for tag in selected_tags:
            new_file.tags.append(tag)
            print(f"Added tag '{tag.name}' to file")
        
        # Automatically add FOLDER tag to archive files
        if final_filename.lower().endswith(('.zip', '.rar', '.7z', '.tar.gz', '.tar')):
            folder_tag = Tag.query.filter_by(name='FOLDER', is_system=True).first()
            if folder_tag and folder_tag not in new_file.tags:
                new_file.tags.append(folder_tag)
                print(f"Added FOLDER tag automatically to archive file")
        
        # Log activity
        activity = ActivityLog(
            user_id=current_user.id,
            action='file_upload',
            details=f'Uploaded file: {final_filename}',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        
        print(f"Activity log created")
        
        # Add records to database
        db.session.add(new_file)
        db.session.add(activity)
        
        # Commit transaction
        try:
            db.session.commit()
            print(f"Database transaction committed successfully")
        except Exception as e:
            print(f"Error committing to database: {str(e)}")
            db.session.rollback()
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify({
                'message': 'File uploaded successfully',
                'file_id': new_file.id,
                'filename': new_file.original_filename
            }), 200
        else:
            # For non-AJAX requests, redirect to the dashboard
            flash('File uploaded successfully', 'success')
            return redirect(url_for('files.dashboard'))
        
    except Exception as e:
        # Log the full error
        print(f"Unhandled error in upload: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Clean up any temporary files
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        # Roll back any database changes
        db.session.rollback()
        
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500
        else:
            flash(f'Upload failed: {str(e)}', 'danger')
            return redirect(url_for('files.dashboard'))

@files_bp.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    
    # Check if user has access to file
    if file.user_id != current_user.id:
        abort(403)
    
    # Log download
    activity = ActivityLog(
        user_id=current_user.id,
        action='file_download',
        details=f'Downloaded file: {file.filename}',
        ip_address=request.remote_addr,
        timestamp=datetime.utcnow()
    )
    db.session.add(activity)
    
    # Update last accessed
    file.last_accessed = datetime.utcnow()
    db.session.commit()
    
    return send_file(
        file.path,
        as_attachment=True,
        download_name=file.original_filename
    )

@files_bp.route('/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    print(f"===== DELETE REQUEST =====")
    print(f"User: {current_user.username} (ID: {current_user.id})")
    print(f"File ID: {file_id}")
    print(f"Headers: {request.headers}")
    
    file = File.query.get_or_404(file_id)
    
    # Check if user owns the file
    if file.user_id != current_user.id:
        print(f"Permission denied for user {current_user.id} on file {file_id}")
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        # Delete physical file
        if os.path.exists(file.path):
            os.remove(file.path)
            print(f"Deleted physical file: {file.path}")
        else:
            print(f"Physical file not found: {file.path}")
        
        # Update user's storage usage
        current_user.storage_used = max(0, current_user.storage_used - file.file_size)
        print(f"Updated user storage: {current_user.storage_used}")
        
        # Log deletion
        activity = ActivityLog(
            user_id=current_user.id,
            action='file_delete',
            details=f'Deleted file: {file.filename}',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(activity)
        
        # Delete database record
        db.session.delete(file)
        db.session.commit()
        print(f"File {file_id} deleted successfully")
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify({'message': 'File deleted successfully'}), 200
        else:
            flash('File deleted successfully', 'success')
            return redirect(url_for('files.dashboard'))
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
        import traceback
        traceback.print_exc()
        
        db.session.rollback()
        
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify({'error': str(e)}), 500
        else:
            flash(f'Error deleting file: {str(e)}', 'danger')
            return redirect(url_for('files.dashboard'))

@files_bp.route('/tag/<int:file_id>', methods=['POST'])
@login_required
def tag_file(file_id):
    """Add or remove tags from a file"""
    file = File.query.get_or_404(file_id)
    
    # Check if user owns the file
    if file.user_id != current_user.id:
        abort(403)
    
    try:
        # Get tags from form
        tag_ids = request.form.getlist('tags')
        
        # Clear existing tags (except system tags like FOLDER for archives)
        current_tags = list(file.tags)
        for tag in current_tags:
            if tag.is_system and file.is_archive() and tag.name == 'FOLDER':
                continue  # Don't remove FOLDER tag from archives
            file.tags.remove(tag)
        
        # Add selected tags
        if tag_ids:
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
            for tag in tags:
                file.tags.append(tag)
        
        db.session.commit()
        
        # Log tag update
        activity = ActivityLog(
            user_id=current_user.id,
            action='file_tag',
            details=f'Updated tags for file: {file.filename}',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({'message': 'Tags updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@files_bp.route('/get-tags/<int:file_id>')
@login_required
def get_file_tags(file_id):
    """Get tags for a file"""
    file = File.query.get_or_404(file_id)
    
    # Check if user owns the file
    if file.user_id != current_user.id:
        abort(403)
    
    # Return tag IDs
    tag_ids = [tag.id for tag in file.tags]
    return jsonify({'tags': tag_ids})

@files_bp.route('/tags', methods=['GET', 'POST'])
@login_required
def manage_tags():
    """Manage user's tags"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name')
            color = request.form.get('color', '#6c757d')
            
            if not name:
                flash('Tag name is required', 'danger')
                return redirect(url_for('files.manage_tags'))
            
            # Check if tag already exists
            existing_tag = Tag.query.filter(
                (Tag.name == name) & 
                ((Tag.user_id == current_user.id) | (Tag.is_system == True))
            ).first()
            
            if existing_tag:
                flash('Tag already exists', 'danger')
            else:
                new_tag = Tag(
                    name=name,
                    color=color,
                    user_id=current_user.id,
                    created_at=datetime.utcnow()
                )
                db.session.add(new_tag)
                db.session.commit()
                flash('Tag created successfully', 'success')
        
        elif action == 'delete':
            tag_id = request.form.get('tag_id')
            tag = Tag.query.get_or_404(tag_id)
            
            # Check if user owns the tag
            if tag.user_id != current_user.id:
                abort(403)
            
            # Don't allow deleting system tags
            if tag.is_system:
                flash('Cannot delete system tags', 'danger')
            else:
                db.session.delete(tag)
                db.session.commit()
                flash('Tag deleted successfully', 'success')
        
        return redirect(url_for('files.manage_tags'))
    
    # Get user's tags and system tags
    tags = Tag.query.filter((Tag.user_id == current_user.id) | (Tag.is_system == True)).all()
    return render_template('files/tags.html', tags=tags)

@files_bp.route('/request_storage', methods=['POST'])
@login_required
def request_storage():
    """Request a storage increase"""
    requested_size = request.form.get('requested_size')
    reason = request.form.get('reason')
    
    if not requested_size or not reason:
        flash('Please provide both size and reason', 'danger')
        return redirect(url_for('auth.profile'))
    
    try:
        requested_size = int(requested_size)
        if requested_size <= current_user.storage_limit:
            flash('Requested size must be greater than current limit', 'danger')
            return redirect(url_for('auth.profile'))
        
        # Create storage request
        storage_request = StorageRequest(
            user_id=current_user.id,
            requested_size=requested_size,
            reason=reason,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        # Log request
        activity = ActivityLog(
            user_id=current_user.id,
            action='storage_request',
            details=f'Storage increase request: {requested_size} bytes',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(storage_request)
        db.session.add(activity)
        db.session.commit()
        
        flash('Storage request submitted successfully', 'success')
        
    except ValueError:
        flash('Invalid storage size', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('auth.profile'))

@files_bp.route('/list')
@login_required
def file_list():
    """Return a partial HTML with just the file list"""
    # Get filter parameters
    tag_filter = request.args.get('tag')
    
    # Base query - only get files belonging to the current user
    query = File.query.filter_by(user_id=current_user.id)
    
    # Apply tag filter if specified
    if tag_filter:
        try:
            tag_id = int(tag_filter)
            query = query.join(File.tags).filter(Tag.id == tag_id)
        except ValueError:
            pass
    
    # Get files ordered by upload date
    files = query.order_by(File.uploaded_at.desc()).all()
    tags = Tag.query.filter((Tag.user_id == current_user.id) | (Tag.is_system == True)).all()
    
    return render_template('files/partials/file_list.html', files=files, tags=tags)



AI_SUMMARIZE_API = "http://192.168.1.23:8000/summarize"  # <- zamenjaj z IP tvojega PC-ja

@files_bp.route('/summarize/<int:file_id>')
@login_required
def summarize_file(file_id):
    file = File.query.get_or_404(file_id)
    
    if file.user_id != current_user.id:
        abort(403)

    if not os.path.exists(file.path):
        flash("File doesn't exist.", "danger")
        return redirect(url_for("files.dashboard"))

    ext = os.path.splitext(file.filename)[1].lower()
    
    try:
        # 🔹 Preberi besedilo glede na končnico
        if ext == ".txt":
            with open(file.path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        elif ext == ".pdf":
            reader = PdfReader(file.path)
            content = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            flash("Summary is only possible for .txt and .pdf files", "warning")
            return redirect(url_for("files.dashboard"))

        # 🔹 Pošlji AI strežniku
        res = requests.post(AI_SUMMARIZE_API, json={"text": content}, timeout=60)
        res.raise_for_status()
        summary = res.json().get("summary", "[Ni bilo povzetka]")
    except Exception as e:
        summary = f"Error at geneerating a summary: {e}"

    return render_template("files/summary.html", filename=file.original_filename, summary=summary)
