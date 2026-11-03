import os.path
import json

def read_user_config():
  user_config_file = os.path.join(os.path.expanduser("~"), ".gensite")

  if not os.path.exists(user_config_file):
    raise CommandError("No user file exists, use gensite init first : " + user_config_file)

  user_config = {}
  with open(user_config_file, "r", encoding="utf-8") as f:
    user_config = json.load(f)
  return user_config
