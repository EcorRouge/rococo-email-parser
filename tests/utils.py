import os


def list_files(relative_path, ext):
    path = os.path.join(os.path.dirname(__file__), relative_path)
    return [f for f in os.listdir(path) if f.endswith(ext)]


def read_local_file(relative_path, mode="rb"):
    file_path = os.path.join(os.path.dirname(__file__), relative_path)
    with open(file_path, mode) as f:
        content = f.read()
    return content
