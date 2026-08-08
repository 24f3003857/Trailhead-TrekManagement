from functools import wraps
from flask import abort
from flask_login import current_user
from models import STATUS_ACTIVE

def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if current_user.role != role or current_user.account_status != STATUS_ACTIVE:
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator
