from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from .models.database import db
import os
from dotenv import load_dotenv

ALLOWED_ORIGINS = "*"

socketio = SocketIO(cors_allowed_origins=ALLOWED_ORIGINS)

def create_app():
    load_dotenv()
    app = Flask(__name__)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 300, 
    }

    CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True)
    
    db.init_app(app)
    JWTManager(app)
    socketio.init_app(app)

    from .routes.public import public_bp
    from .routes.admin import admin_bp
    from .routes.auth import auth_bp
    
    app.register_blueprint(public_bp, url_prefix='/api/public')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from .sockets import events

    return app