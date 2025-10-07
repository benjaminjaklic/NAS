from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, User, Group, File, UserGroups
from datetime import datetime
from flask import request, redirect, url_for, flash
from flask_login import login_required
from app.models import Group, UserGroups, db
from app.routes.admin import admin_required



groups_bp = Blueprint('groups', __name__, url_prefix='/groups')

@groups_bp.route('/')
@login_required
def index():
    user_groups = current_user.groups
    return render_template('groups/index.html', groups=user_groups)

@groups_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if Group.query.filter_by(name=name).first():
            flash('Group name already exists', 'error')
            return redirect(url_for('groups.create'))
        
        group = Group(
            name=name,
            description=description,
            creator_id=current_user.id
        )
        
        # Make creator an admin of the group
        user_group = UserGroups(
            user_id=current_user.id,
            is_admin=True
        )
        
        group.users.append(user_group)
        
        db.session.add(group)
        db.session.commit()
        
        flash('Group created successfully', 'success')
        return redirect(url_for('groups.index'))
    
    return render_template('groups/create.html')

@groups_bp.route('/<int:group_id>')
@login_required
def detail(group_id):
    group = Group.query.get_or_404(group_id)
    
    if current_user not in [ug.user for ug in group.users]:
        flash('Access denied', 'error')
        return redirect(url_for('groups.index'))
    
    # Query files NOT linked to this group yet, so users can pick only unlinked files
    available_files = File.query.filter(
        (File.group_id != group_id) | (File.group_id.is_(None))
    ).all()
    
    return render_template('groups/detail.html', group=group, available_files=available_files)

@groups_bp.route('/<int:group_id>/invite', methods=['POST'])
@login_required
def invite_user(group_id):
    group = Group.query.get_or_404(group_id)
    
    # Check if user is admin of group
    if not any(ug.user_id == current_user.id and ug.is_admin for ug in group.users):
        flash('Permission denied', 'error')
        return redirect(url_for('groups.detail', group_id=group_id))
    
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('groups.detail', group_id=group_id))
    
    if user in [ug.user for ug in group.users]:
        flash('User already in group', 'error')
        return redirect(url_for('groups.detail', group_id=group_id))
    
    user_group = UserGroups(
        user_id=user.id,
        is_admin=False
    )
    
    group.users.append(user_group)
    db.session.commit()
    
    flash(f'User {username} added to group', 'success')
    return redirect(url_for('groups.detail', group_id=group_id))

@groups_bp.route('/<int:group_id>/remove/<int:user_id>', methods=['POST'])
@login_required
def remove_user(group_id, user_id):
    group = Group.query.get_or_404(group_id)
    
    # Check if current user is group admin
    if not any(ug.user_id == current_user.id and ug.is_admin for ug in group.users):
        flash('Permission denied', 'error')
        return redirect(url_for('groups.detail', group_id=group_id))
    
    user_group = UserGroups.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first()
    
    if user_group:
        db.session.delete(user_group)
        db.session.commit()
        flash('User removed from group', 'success')
    
    return redirect(url_for('groups.detail', group_id=group_id))

@groups_bp.route('/<int:group_id>/files')
@login_required
def files(group_id):
    group = Group.query.get_or_404(group_id)
    
    if current_user not in [ug.user for ug in group.users]:
        flash('Access denied', 'error')
        return redirect(url_for('groups.index'))
    
    files = File.query.filter_by(group_id=group_id).all()
    return render_template('groups/files.html', group=group, files=files)

@groups_bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    
    # Only creator can delete group
    if group.creator_id != current_user.id:
        flash('Permission denied', 'error')
        return redirect(url_for('groups.index'))
    
    db.session.delete(group)
    db.session.commit()
    
    flash('Group deleted successfully', 'success')
    return redirect(url_for('groups.index'))


@groups_bp.route('/groups/<int:group_id>/remove_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def remove_user_from_group(group_id, user_id):
    # Prevent admin from removing themselves
    if user_id == current_user.id:
        flash('You cannot remove yourself from the group.', 'error')
        return redirect(url_for('groups.detail', group_id=group_id))
    
    link = UserGroups.query.filter_by(group_id=group_id, user_id=user_id).first()
    if link:
        db.session.delete(link)
        db.session.commit()
        flash('User removed from group.', 'success')
    else:
        flash('User not found in group.', 'danger')
    
    return redirect(url_for('groups.detail', group_id=group_id))


@groups_bp.route('/groups/<int:group_id>/link_file', methods=['POST'])
@login_required
@admin_required
def link_file_to_group(group_id):
    file_id = request.form.get('file_id')
    if not file_id:
        flash('No file selected.', 'danger')
        return redirect(url_for('groups.detail', group_id=group_id))
    
    # Check if file exists
    file = File.query.filter_by(id=file_id).first()
    if not file:
        flash('File not found.', 'danger')
        return redirect(url_for('groups.detail', group_id=group_id))
    
    # Link file to group by setting group_id or another association
    
    # If your File model has group_id foreign key:
    if file.group_id == group_id:
        flash('File is already linked to this group.', 'warning')
        return redirect(url_for('groups.detail', group_id=group_id))
    
    file.group_id = group_id
    db.session.commit()
    
    flash('File linked to group.', 'success')
    return redirect(url_for('groups.detail', group_id=group_id))
