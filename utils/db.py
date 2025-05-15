import os
import json

class Database:
    def __init__(self, data_path):
        self.data_path = data_path
        self.users = {}
        self.teams = {}
        self.tickets = {}
        self.persistent_views = {}
        self.load_data()

    def load_data(self):
        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)
                self.users = data.get('users', {})
                self.teams = data.get('teams', {})
                self.tickets = data.get('tickets', {})
                self.persistent_views = data.get('persistent_views', {})
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"データ読み込みエラー: {e}")

    def save_data(self):
        data = {
            'users': self.users,
            'teams': self.teams,
            'tickets': self.tickets,
            'persistent_views': self.persistent_views
        }
        try:
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            with open(self.data_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"データ保存エラー: {e}") 