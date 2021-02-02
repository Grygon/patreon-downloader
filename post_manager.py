import json
import os


class PostManager():

    posts: dict
    post_file: str
    data: dict

    def __init__(self, post_file='posts.json'):
        self.post_file = post_file
        self.load_data()

    def load_data(self):
        if os.path.exists(self.post_file):
            with open(self.post_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save_data(self):
        with open(self.post_file, 'w') as f:
            json.dump(self.data, f)

    def register_post(self, post: str, date: str):
        self.data[post] = date

    def should_update(self, post: str, date: str):
        if post in self.data:
            return self.data[post]['date'] < date
        return True
