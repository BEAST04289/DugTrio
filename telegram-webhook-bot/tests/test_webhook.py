import unittest
from flask import json
from app import app

class WebhookTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_valid_webhook(self):
        token = 'your_bot_token_here'  # Replace with your actual bot token for testing
        response = self.app.post(f'/{token}', data=json.dumps({
            'update_id': 123456,
            'message': {
                'message_id': 1,
                'from': {
                    'id': 123456789,
                    'is_bot': False,
                    'first_name': 'Test',
                    'username': 'testuser',
                },
                'chat': {
                    'id': 123456789,
                    'first_name': 'Test',
                    'username': 'testuser',
                    'type': 'private',
                },
                'date': 1610000000,
                'text': 'Hello, world!',
            }
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)

    def test_invalid_webhook_token(self):
        invalid_token = 'invalid_token'
        response = self.app.post(f'/{invalid_token}', data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 403)

if __name__ == '__main__':
    unittest.main()