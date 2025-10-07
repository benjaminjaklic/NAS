from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, User, ActivityLog, StorageRequest, File
from datetime import datetime
from functools import wraps
import os
import shutil

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need administrative privileges to access this page.', 'error')
            return redirect(url_for('files.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    if current_user.is_demo:
        return render_template('admin/dashboard.html',
                               total_users=1,
                               pending_users=0,
                               pending_requests=0,
                               recent_activities=[])

    total_users = User.query.count()
    pending_users = User.query.filter_by(is_approved=False).count()
    pending_requests = StorageRequest.query.filter_by(status='pending').count()
    recent_activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           pending_users=pending_users,
                           pending_requests=pending_requests,
                           recent_activities=recent_activities)

@admin_bp.route('/manage_users')
@admin_required
def manage_users():
    if current_user.is_demo:
        now = datetime.utcnow()
        return render_template('admin/users.html', users=[current_user], now=now, default_admin_id=current_user.id)

    users_list = User.query.all()
    now = datetime.utcnow()
    return render_template('admin/users.html', users=users_list, now=now, default_admin_id=1)

@admin_bp.route('/user/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    if current_user.is_demo:
        flash("Demo user can't approve users.", 'warning')
        return redirect(url_for('admin.manage_users'))

    user = User.query.get_or_404(user_id)
    action = request.args.get('action', 'approve')
    if action == 'revoke':
        user.is_approved = False
        details = f'Revoked approval for user: {user.username}'
        flash_message = f'Approval for {user.username} has been revoked.'
        log_action = 'user_approval_revoked'
    else:
        if user.is_approved:
            flash('User is already approved.', 'info')
            return redirect(url_for('admin.manage_users'))
        user.is_approved = True
        details = f'Approved user: {user.username}'
        flash_message = f'User {user.username} has been approved.'
        log_action = 'user_approval'

    log = ActivityLog(user_id=current_user.id, action=log_action, details=details,
                      ip_address=get_client_ip(), timestamp=datetime.utcnow())
    db.session.add(log)
    db.session.commit()
    flash(flash_message, 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/user/<int:user_id>/make_admin', methods=['POST'])
@admin_required
def make_admin(user_id):
    if current_user.is_demo:
        flash("Demo user can't grant admin rights.", 'warning')
        return redirect(url_for('admin.manage_users'))

    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash(f'{user.username} is already an admin.', 'info')
        return redirect(url_for('admin.manage_users'))
    user.is_admin = True
    log = ActivityLog(user_id=current_user.id, action='admin_status_granted',
                      details=f'Admin status granted to user: {user.username}',
                      ip_address=get_client_ip(), timestamp=datetime.utcnow())
    db.session.add(log)
    db.session.commit()
    flash(f'Admin privileges granted to {user.username}.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/user/<int:user_id>/revoke_admin', methods=['POST'])
@admin_required
def revoke_admin(user_id):
    if current_user.is_demo:
        flash("Demo user can't revoke admin rights.", 'warning')
        return redirect(url_for('admin.manage_users'))

    if user_id == 1 or user_id == current_user.id:
        flash('Cannot revoke this admin account.', 'error')
        return redirect(url_for('admin.manage_users'))
    user = User.query.get_or_404(user_id)
    if not user.is_admin:
        flash(f'{user.username} is not an admin.', 'info')
        return redirect(url_for('admin.manage_users'))
    user.is_admin = False
    log = ActivityLog(user_id=current_user.id, action='admin_status_revoked',
                      details=f'Admin status revoked from user: {user.username}',
                      ip_address=get_client_ip(), timestamp=datetime.utcnow())
    db.session.add(log)
    db.session.commit()
    flash(f'Admin privileges revoked from {user.username}.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if current_user.is_demo:
        flash("Demo user can't delete users.", 'warning')
        return redirect(url_for('admin.manage_users'))

    if user_id == 1 or user_id == current_user.id:
        flash('Cannot delete this account.', 'error')
        return redirect(url_for('admin.manage_users'))

    user = User.query.get_or_404(user_id)
    if user.is_admin and current_user.id != 1:
        flash('Only the default admin can delete other admins.', 'error')
        return redirect(url_for('admin.manage_users'))

    try:
        user_storage_path = os.path.join('storage', 'users', str(user.id))
        if os.path.exists(user_storage_path):
            shutil.rmtree(user_storage_path)
        ActivityLog.query.filter_by(user_id=user.id).delete()
        StorageRequest.query.filter_by(user_id=user.id).delete()
        StorageRequest.query.filter_by(responded_by=user.id).delete()
        File.query.filter_by(user_id=user.id).delete()
        user.groups = []
        log = ActivityLog(user_id=current_user.id, action='user_deletion',
                          details=f'Deleted user: {user.username}',
                          ip_address=get_client_ip(), timestamp=datetime.utcnow())
        db.session.add(log)
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted successfully.', 'success')
        return redirect(url_for('admin.manage_users'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('admin.manage_users'))

@admin_bp.route('/storage_requests')
@admin_required
def view_storage_requests():
    if current_user.is_demo:
        flash("Demo user can't process storage requests.", 'warning')
        return render_template('admin/storage_requests.html', requests=[])

    requests = StorageRequest.query.order_by(StorageRequest.created_at.desc()).all()
    return render_template('admin/storage_requests.html', requests=requests)

@admin_bp.route('/storage_request/<int:request_id>/process', methods=['POST'])
@admin_required
def handle_storage_request(request_id):
    if current_user.is_demo:
        flash("Demo user can't process storage requests.", 'warning')
        return redirect(url_for('admin.view_storage_requests'))

    storage_request = StorageRequest.query.get_or_404(request_id)
    action = request.form.get('action')
    if action not in ['approve', 'deny']:
        flash('Invalid action.', 'error')
        return redirect(url_for('admin.view_storage_requests'))
    if storage_request.status != 'pending':
        flash('This request has already been processed.', 'error')
        return redirect(url_for('admin.view_storage_requests'))
    user = User.query.get(storage_request.user_id)
    if action == 'approve':
        user.storage_limit = storage_request.requested_size
        storage_request.status = 'approved'
        flash(f'Storage request for {user.username} has been approved.', 'success')
    else:
        storage_request.status = 'denied'
        flash(f'Storage request for {user.username} has been denied.', 'info')
    storage_request.responded_at = datetime.utcnow()
    storage_request.responded_by = current_user.id
    log = ActivityLog(user_id=current_user.id, action=f'storage_request_{action}',
                      details=f'Storage request {action}d for user: {user.username}',
                      ip_address=get_client_ip(), timestamp=datetime.utcnow())
    db.session.add(log)
    db.session.delete(storage_request)
    db.session.commit()
    return redirect(url_for('admin.view_storage_requests'))

@admin_bp.route('/user/<int:user_id>', methods=['GET'])
@admin_required
def user_detail(user_id):
    if current_user.is_demo:
        flash("Demo user can't view user details.", 'warning')
        return redirect(url_for('admin.manage_users'))

    user = User.query.get_or_404(user_id)
    return render_template('admin/user_detail.html', user=user)
