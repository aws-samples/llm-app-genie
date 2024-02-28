import os

import toml

with open("./.streamlit/secrets.toml", "w", encoding="utf8") as file:
    data = {"passwords": {os.environ["USERNAME"]: os.environ["PASSWORD"]}}
    toml.dump(data, file)
