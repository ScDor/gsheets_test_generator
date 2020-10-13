import os


def make_list(l: list):
    return {i: x for i, x in enumerate(l)}


def file_to_list(path):
    with open(path, 'rt', encoding="utf8") as openf:
        return [l.strip() for l in openf.readlines()]


root = "web_gui"
for f in os.listdir(root):
    if ".py" not in f:
        print(make_list(file_to_list(os.path.join(root, f))))
