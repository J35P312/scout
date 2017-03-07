# -*- coding: utf-8 -*-
from flask import Flask, redirect, request, url_for
from flask_login import current_user

from . import extensions
from .blueprints import public, genes, cases, login


def create_app(config_file=None, config=None):
    """Flask app factory function."""
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    if config_file:
        app.config.from_pyfile(config_file)
    if config:
        app.config.update(config)

    configure_extensions(app)
    register_blueprints(app)

    @app.before_request
    def check_user():
        if request.endpoint:
            # check if the endpoint requires authentication
            static_endpoint = 'static' in request.endpoint
            public_endpoint = getattr(app.view_functions[request.endpoint],
                                      'is_public', False)
            relevant_endpoint = not (static_endpoint or public_endpoint)
            # if endpoint requires auth, check if user is authenticated
            if relevant_endpoint and not current_user.is_authenticated:
                login_url = url_for('login.login', next=url_for(request.endpoint))
                return redirect(login_url)

    return app


def configure_extensions(app):
    """Configure Flask extensions."""
    extensions.toolbar.init_app(app)
    extensions.bootstrap.init_app(app)
    extensions.mongo.init_app(app)
    extensions.store.init_app(app)
    extensions.login_manager.init_app(app)
    extensions.oauth.init_app(app)


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(public.public_bp)
    app.register_blueprint(genes.genes_bp)
    app.register_blueprint(cases.cases_bp)
    app.register_blueprint(login.login_bp)
