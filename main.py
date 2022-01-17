import threading

from app import create_app
from app.sauron import Sauron

app = create_app()
sauron = Sauron()

thread = threading.Thread(target=sauron.watch, args=())
thread.daemon = True
thread.start()

if __name__ == '__main__':
    app.run(threaded=True)
