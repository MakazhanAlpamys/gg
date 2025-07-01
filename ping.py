from flask import Flask
import os
import threading
import time

app = Flask(__name__)

@app.route('/')
def ping():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Запустите сервер Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Бесконечный цикл для поддержания процесса активным
    while True:
        time.sleep(60)