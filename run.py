import os

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Iniciando servidor MVP en puerto {port}")
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)