from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    print("Iniciando servidor MVP")
    socketio.run(app, host='0.0.0.0', port=24571, allow_unsafe_werkzeug=True)