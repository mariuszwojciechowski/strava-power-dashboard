import json
import os

from config import BASE_DIR

DATA_FILE = os.path.join(BASE_DIR, "lab_tests.json")

DEFAULT_TESTS = [
    {"date": "2024-01-01", "value": 100, "label": "Przykładowy test (podmień w lab_tests.json)"},
]


def get_tests():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_TESTS
    with open(DATA_FILE) as f:
        return json.load(f)


def save_tests(tests):
    with open(DATA_FILE, "w") as f:
        json.dump(tests, f, indent=2, ensure_ascii=False)
