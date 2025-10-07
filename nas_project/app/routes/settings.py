from flask import Blueprint, request, redirect, url_for, make_response
from flask_login import login_required

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/toggle_theme', methods=['POST'])
@login_required
def toggle_theme():
    current = request.cookies.get('theme', 'light')
    new_theme = 'dark' if current == 'light' else 'light'

    resp = make_response(redirect(request.referrer or url_for('files.dashboard')))
    resp.set_cookie('theme', new_theme, max_age=60*60*24*365)  # 1 year

    return resp
