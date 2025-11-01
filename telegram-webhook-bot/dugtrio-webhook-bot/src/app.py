from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from bot import handle_update

load_dotenv()

app = Flask(__name__)

@app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    bot_token = os.getenv('BOT_TOKEN')
    
    if token != bot_token:
        return jsonify({'error': 'Invalid token'}), 403

    update = request.get_json()
    handle_update(update)
    
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)