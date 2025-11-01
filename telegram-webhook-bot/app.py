from flask import Flask, request, jsonify
import os
from bot import application

app = Flask(__name__)

@app.route('/<token>', methods=['POST'])
def webhook(token):
    if token != os.getenv('TELEGRAM_BOT_TOKEN'):
        return jsonify({'error': 'Invalid token'}), 403

    update = request.get_json()
    if update is None:
        return jsonify({'error': 'Invalid update'}), 400

    # Process the incoming update
    application.process_update(update)

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)