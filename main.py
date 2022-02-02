from app import create_app
from app.sauron import Sauron

sauron = Sauron()
app = create_app(sauron)


if __name__ == '__main__':
    app.run()

