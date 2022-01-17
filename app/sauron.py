

class Sauron:

    def __init__(self):
        self.num_message = 0

    def handle_message(self, json_data):
        self.num_message += 1
        print(self.num_message)

    def watch(self):
        # while True:
        return
