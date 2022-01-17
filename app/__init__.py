import json
import os

from flask import Flask, request


def create_app(sauron):
    app = Flask(__name__)

    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    @app.route('/sauron', methods=['POST'])
    def watch():
        if not request.method == 'POST':
            return

        json_data = request.get_json()

        # API 인증
        if 'challenge' in json_data:
            return json.dumps({'challenge': json_data['challenge']}), 200, {'ContentType': 'application/json'}

        # 필요한 이벤트만 선택한다.
        if 'event' not in json_data:
            return json.dumps({'success': False}), 200, {'ContentType': 'application/json'}

        event_data = json_data['event']
        if event_data.get('type') == 'message':
            sauron.handle_message(event_data)
            return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

    return app
