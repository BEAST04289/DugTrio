from flask import Flask, request, jsonify
import os
from bot import application, handle_update

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PORT = int(os.getenv('PORT', 5000))

@app.route('/<token>', methods=['POST'])
def webhook(token):
    if token != TELEGRAM_BOT_TOKEN:
        return jsonify({'error': 'Invalid token'}), 403

    update = request.get_json()
    handle_update(update)
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)