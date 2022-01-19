# _config.py 로 복사해서 사용하세요.

# ==============================================================================
# 필수 설정
# ------------------------------------------------------------------------------
# 이벤트를 게시할 채널 (CXXXXXXXX)
FEED_CHANNEL = ''
# 봇 이름
BOT_USERNAME = ''
# 봇 프로필 이미지
BOT_ICON_URL = ''

# ==============================================================================
# 공통 설정
# ------------------------------------------------------------------------------
# 사우론이 보여줄 최근 스레드 글 개수
RECENT_REPLY_NUM = 3
# 이벤트 쿨다운
EVENT_COOLDOWN = 1 * 60 * 60

# ==============================================================================
# 오래된 스레드에 새 글이 올라옴
# ------------------------------------------------------------------------------
# 이 시간 이상 지났으면 오래된 스레드
CONTINUE_COOLDOWN = 6 * 60 * 60
# 오래된 스레드에 이 글 개수 만큼 글이 올라오면 이벤트 발생
CONTINUE_COUNTER = 3

# ==============================================================================
# 핫한 스레드: 일정 시간 내에 일정 개수 이상의 글이 올라옴
# ------------------------------------------------------------------------------
# 이 시간 내에
BURNING_COOLDOWN = 10 * 60
# 이 개수 만큼 글이 올라오면 이벤트 발생
BURNING_COUNTER = 30