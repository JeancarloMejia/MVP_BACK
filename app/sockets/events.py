from flask import request
from flask_socketio import emit, join_room, leave_room
from app import socketio

@socketio.on('connect')
def handle_connect():
    print(f"Nuevo dispositivo conectado: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Dispositivo desconectado: {request.sid}")

@socketio.on('unirse_tracking')
def on_join_tracking(data):
    order_id = data.get('order_id')
    if order_id:
        join_room(order_id)
        print(f"Cliente {request.sid} escuchando el pedido: {order_id}")
        emit('conexion_establecida', {'status': 'ok', 'room': order_id})

@socketio.on('unirse_admin')
def on_join_admin():
    join_room('admin_room')
    print(f"Administrador {request.sid} conectado a la sala principal")