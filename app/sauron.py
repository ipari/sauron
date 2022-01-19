import os

from collections import namedtuple
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import *
from app.enums import SauronEvent


Message = namedtuple('Message', ['ts', 'dt', 'user', 'text', 'blocks'])
User = namedtuple('User', ['email_id', 'first_name', 'last_name', 'image'])


def dt_from_ts(ts):
    return datetime.fromtimestamp(float(ts))


def dt_diff(dt_after, dt_before):
    diff = dt_after - dt_before
    return min(diff.days, 7) * 24 * 3600 + diff.seconds


class Thread:

    ts = None
    channel = None
    replies = None
    length = None

    continued = None
    continue_counter = None

    def __init__(self, ts, channel, user, text, blocks):
        self.ts = ts
        self.dt = dt_from_ts(ts)
        self.channel = channel
        self.replies = []
        self.length = 0

        self.continued = False
        self.continue_counter = 0
        self.last_event_dt = datetime.min

        self.add_reply(ts, user, text, blocks, skip_event=True)

    @property
    def text(self):
        return self.replies[0].text

    def add_reply(self, ts, user, text, blocks, skip_event=False):
        if self.replies and ts == self.replies[-1].ts:
            return False

        message = Message(ts, dt_from_ts(ts), user, text, blocks)
        self.replies.append(message)
        self.length += 1
        if not skip_event:
            return self.check_event()

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
                self.length -= 1
                return True
        return False

    def check_event(self):
        now = datetime.now()

        # 이벤트 반복 트리거 방지
        if dt_diff(now, self.last_event_dt) < EVENT_COOLDOWN:
            return

        event = None
        # 스레드가 재개됨
        if not self.continued:
            if self.length >= 2 and dt_diff(self.replies[-1].dt, self.replies[-2].dt) > CONTINUE_COOLDOWN:
                self.continued = True
        if self.continued:
            self.continue_counter += 1
            if self.continue_counter >= CONTINUE_COUNTER:
                self.continued = False
                self.continue_counter = 0
                event = SauronEvent.THREAD_CONTINUED

        # 스레드가 활활 불타오름
        if self.length >= BURNING_COUNTER \
                and dt_diff(self.replies[-1].dt, self.replies[-BURNING_COUNTER].dt) < BURNING_COOLDOWN:
            event = SauronEvent.THREAD_BURNING

        if event:
            self.last_event_dt = now
            return event


class Block:

    def __init__(self):
        self.blocks = []

    def add_section(self, text):
        self.blocks.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': text,
            }
        })

    def add_divider(self):
        self.blocks.append({
            'type': 'divider',
        })

    def add_message(self, text, name=None, image_url=None, img_alt=None):
        elements = []
        if image_url:
            elements.append({
                'type': 'image',
                'image_url': image_url,
                'alt_text': img_alt or '',
            })
        if name:
            text = f'{name}: {text}'
        elements.append({
            'type': 'plain_text',
            'emoji': True,
            'text': text,
        })
        self.blocks.append({
            'type': 'context',
            'elements': elements,
        })


class Sauron:

    client = None
    users = None
    threads = None

    def __init__(self):
        self.threads = {}
        self.users = {}
        self.client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

    def handle_message(self, event_data):
        # 봇 필터링
        if 'bot_id' in event_data:
            return

        # 작성/수정/삭제에 따른 info 처리
        channel = event_data['channel']
        subtype = event_data.get('subtype')

        # 필요한 메시지 타입만 남김
        if subtype and subtype not in ('message_changed', 'message_deleted', 'file_share'):
            return

        try:
            if subtype is None or subtype == 'file_share':
                ts = event_data['ts']
                thread_ts = event_data.get('thread_ts', ts)
                user = event_data['user']
            else:
                ts = event_data['previous_message']['ts']
                thread_ts = event_data['previous_message'].get('thread_ts', ts)
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
        except KeyError as e:
            print(f'ERROR: {e} \n {event_data}')
            return

        if ts == thread_ts:
            return

        # 스레드에 속한 메시지인데, 소속 스레드가 사우론에 없으면 스레드 정보를 받아온다.
        if thread_ts not in self.threads:
            replies = self.get_replies(thread_ts, channel)
            num_replies = len(replies)
            message = replies[0]
            self.threads[thread_ts] = Thread(message[0], channel, message[2], message[3], message[4])
            for i in range(1, num_replies):
                reply = replies[i]
                # 기존 메시지 불러올 때는 이벤트 트리거 하지 않음
                self.threads[thread_ts].add_reply(reply[0], reply[2], reply[3], reply[4], skip_event=True)

        # 작성/수정/삭제 처리
        thread = self.threads[thread_ts]
        if subtype is None:
            print(f'[Message Posted]: {ts}, {user}, {text}, {blocks}')
            event = thread.add_reply(ts, user, text, blocks)
            self.handle_event(thread, event)
        elif subtype == 'message_changed':
            print(f'[Message Changed]: {ts}, {user}, {text}, {blocks}')
            thread.change_reply(ts, user, text, blocks)
        elif subtype == 'message_deleted':
            print(f'[Message Deleted]: {ts}, {user}, {text}, {blocks}')
            thread.delete_reply(ts)

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

    def handle_event(self, thread, event):
        if not event:
            return None

        print('=' * 80)
        print(f'>>>>>>>> {event}, {thread.text}')
        print('=' * 80)

        texts = []
        channel = ''
        if event == SauronEvent.THREAD_CONTINUED:
            texts = [
                ':arrow_forward: 잠자던 스레드에 새로운 대화가 있습니다.',
                f'<#{thread.channel}> *{thread.text}*',
            ]
            channel = thread.channel
        elif event == SauronEvent.THREAD_BURNING:
            texts = [
                ':fire: 스레드가 활활 불타고 있습니다.',
                f'<#{thread.channel}> *{thread.text}*',
            ]
            channel = FEED_CHANNEL

        self.client.chat_postMessage(
            channel=channel,
            text=texts[0],
            blocks=self.get_blocks(thread, texts),
            username=BOT_USERNAME,
            icon_url=BOT_ICON_URL,
        )

    def get_user_info(self, user_id):
        if user_id not in self.users:
            profile = self.client.users_profile_get(user=user_id)['profile']
            user = User(
                profile['email'].split('@')[0],
                profile['first_name'],
                profile['last_name'].replace('(', '').replace(')', ''),
                profile['image_original'],
            )
            self.users[user_id] = user

        return self.users[user_id]

    def get_permalink(self, channel, ts):
        result = self.client.chat_getPermalink(
            channel=channel,
            message_ts=ts
        )
        return result['permalink']

    def get_blocks(self, thread, texts):
        if not isinstance(texts, list):
            texts = [texts]

        block = Block()
        for text in texts:
            block.add_section(text)
        block.add_divider()
        for i in range(-RECENT_REPLY_NUM, 0):
            reply = thread.replies[i]
            user = self.get_user_info(reply.user)
            email_id = user.email_id
            name = user.last_name
            image = user.image
            reply_text = reply.text
            block.add_message(reply_text, name=name, image_url=image, img_alt=email_id)
        permalink = self.get_permalink(thread.channel, thread.ts)
        block.add_section(permalink)
        return block.blocks
