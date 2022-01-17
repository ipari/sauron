import os

from collections import namedtuple
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


Message = namedtuple('Message', ['ts', 'dt', 'user', 'text', 'blocks'])
User = namedtuple('User', ['email_id', 'first_name', 'last_name', 'image'])


def dt_from_ts(ts):
    return datetime.fromtimestamp(float(ts))


class Thread:

    ts = None
    channel = None
    reopened = None
    replies = None

    def __init__(self, ts, channel, user, text, blocks):
        self.ts = ts
        self.dt = dt_from_ts(ts)
        self.channel = channel
        self.replies = []
        self.reopened = False

        self.add_reply(ts, user, text, blocks)

    def add_reply(self, ts, user, text, blocks):
        if self.replies and ts == self.replies[-1].ts:
            return False
        self.replies.append(Message(ts, dt_from_ts(ts), user, text, blocks))
        return True

    def change_reply(self, ts, user, text, blocks):
        for i in range(len(self.replies)):
            if ts == self.replies[i].ts:
                self.replies[i] = Message(ts, dt_from_ts(ts), user, text, blocks)
                return True
        return False

    def delete_reply(self, ts):
        for i in range(len(self.replies)):
            if self.replies[i].ts == ts:
                self.replies = self.replies[:i] + self.replies[i+1:]
                return True
        return False


class Sauron:

    client = None
    users = None
    threads = None

    def __init__(self):
        self.threads = {}
        self.client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

    def handle_message(self, event_data):

        # 작성/수정/삭제에 따른 info 처리
        channel = event_data['channel']
        subtype = event_data.get('subtype')

        if subtype is None:
            ts = event_data['ts']
            thread_ts = event_data['thread_ts']
            user = event_data['user']
        else:
            ts = event_data['previous_message']['ts']
            thread_ts = event_data['previous_message']['thread_ts']
            user = event_data['previous_message']['user']

        if subtype is None:
            text = event_data['text']
            blocks = event_data['blocks']
        elif subtype == 'message_changed':
            text = event_data['message']['text']
            blocks = event_data['message']['blocks']
        else:
            text = ''
            blocks = []

        if ts == thread_ts:
            return

        # 스레드에 속한 메시지인데, 소속 스레드가 사우론에 없으면 스레드 정보를 받아온다.
        if thread_ts not in self.threads:
            replies = self.get_replies(thread_ts, channel)
            message = replies[0]
            self.threads[thread_ts] = Thread(message[0], channel, message[2], message[3], message[4])
            for i in range(1, len(replies)):
                reply = replies[i]
                self.threads[thread_ts].add_reply(reply[0], reply[2], reply[3], reply[4])

        # 작성/수정/삭제 처리
        if subtype is None:
            print(f'[Message Posted]: {ts}, {user}, {text}, {blocks}')
            event = self.threads[thread_ts].add_reply(ts, user, text, blocks)
            # event 에 따라 POST
        elif subtype == 'message_changed':
            print(f'[Message Changed]: {ts}, {user}, {text}, {blocks}')
            self.threads[thread_ts].change_reply(ts, user, text, blocks)
        elif subtype == 'message_deleted':
            print(f'[Message Deleted]: {ts}, {user}, {text}, {blocks}')
            self.threads[thread_ts].delete_reply(ts)

    def get_message(self, ts, channel):
        try:
            result = self.client.conversations_history(
                channel=channel,
                inclusive=True,
                oldest=ts,
                limit=1
            )
            return self.get_info_from_message(result['messages'][0])
        except SlackApiError as e:
            print(f'Error: {e}')

    def get_replies(self, thread_ts, channel):
        try:
            result = self.client.conversations_replies(
                channel=channel,
                inclusive=True,
                ts=thread_ts,
                oldest=thread_ts,
            )
            return [self.get_info_from_message(m) for m in result['messages']]
        except SlackApiError as e:
            print(f'Error: {e}')

    @staticmethod
    def get_info_from_message(result):
        return result['ts'], result['thread_ts'], result.get('user'), result['text'], result.get('blocks', [])
