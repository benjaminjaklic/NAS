from flask import render_template

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/error.html',
                             error_code=404,
                             error_message="Page Not Found",
                             error_description="The requested page could not be found."), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/error.html',
                             error_code=403,
                             error_message="Forbidden",
                             error_description="You don't have permission to access this resource."), 403

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/error.html',
                             error_code=500,
                             error_message="Internal Server Error",
                             error_description="Something went wrong on our end."), 500

    @app.errorhandler(413)
    def file_too_large(error):
        return render_template('errors/error.html',
                             error_code=413,
                             error_message="File Too Large",
                             error_description="The file you're trying to upload exceeds the maximum allowed size."), 413