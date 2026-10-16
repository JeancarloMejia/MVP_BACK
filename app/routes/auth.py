from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token
from app.models.database import Admin
import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/ping', methods=['GET', 'OPTIONS'])
@cross_origin()
def ping():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({
        'status': 'success',
        'message': 'Servidor activo y funcionando',
        'data': None
    }), 200

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
@auth_bp.route('/login/', methods=['POST', 'OPTIONS'])
@cross_origin()
def login():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json(silent=True)

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({
            'status': 'error',
            'message': 'Faltan credenciales (username y password son requeridos)'
        }), 400

    username = data.get('username')
    password = data.get('password')

    admin = Admin.query.filter_by(username=username).first()

    if admin and check_password_hash(admin.password_hash, password):
        expires = datetime.timedelta(hours=12)
        access_token = create_access_token(identity=admin.username, expires_delta=expires)
        
        return jsonify({
            'status': 'success',
            'message': 'Login exitoso',
            'data': {
                'access_token': access_token
            }
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'message': 'Usuario o contraseña incorrectos'
        }), 401