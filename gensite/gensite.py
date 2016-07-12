# main interface for using gensite
# gensite init - writes .gensite file
# gensite build
# gensite clean
# gensite new
# gensite list

import argparse
import files
import os.path

import json
import io
import time
import files

class CommandError(Exception):
    def __init__(self, message):
        self.message = message

def init():
  if len(os.listdir(path='.')) != 0:
    raise CommandError("Current directory not empty")
    
  blog_dir = os.getcwd()
  user_config = os.path.join(os.path.expanduser("~"), ".gensite")
  
  if (os.path.exists(user_config)):
    raise CommandError("User already has a site in the " + user_config + " file, delete first")
  
  user_site_data = { "source_dir" : blog_dir,
                     "deploy_command" : "run deploy script here" }
                     
  with open(user_config, "w", encoding="utf-8") as f:
    json.dump(user_site_data, f)
  
    
  site_metadata = {
    "source_dir" : ".",
    "destination_dir" : "/Users/andrew/Source/gensite/webbuild",
    "template" : "/Users/andrew/Source/gensite/template/default",
    "blog_name" : "Andrew's Blog",
    "blog_description" : "A blog about stuff",
    "blog_author" : "Andrew Stephens",
    "root_url" : "http://sheep.horse/",
    "relative_index" : "/"
  }
  
  with open("config.js", "w", encoding="utf-8") as f:
    json.dump(site_metadata, f)
  
  print("OK - edit config.js file")
  
def read_user_config():
  user_config_file = os.path.join(os.path.expanduser("~"), ".gensite")
  
  if not os.path.exists(user_config_file):
    raise CommandError("No user file exists, use gensite init first : " + user_config_file)
  
  user_config = {}
  with open(user_config_file, "r", encoding="utf-8") as f:
    user_config = json.load(f)
  return user_config
  
def read_site_config(site_dir):
  site_config = {}
  
  site_config_file = os.path.join(site_dir, "config.js")
  if not os.path.exists(site_config_file):
    raise CommandError("Not site config file exists : " + site_config_file)
    
  with open(site_config_file, "r", encoding="utf-8") as f:
    site_config = json.load(f)
  return site_config
  
def new():
  """ creates a file from the template """
  user_config = read_user_config()
  base_dir = user_config["source_dir"]
  site_config = read_site_config(base_dir)
  title = input("Enter the title: ")
  
  t = time.gmtime();
  metadata = { "title" : title,
               "author" : site_config["blog_author"],
               "template_type" : "article",
               "original_date" : time.strftime("%a, %d %b %Y %H:%M:%SZ", t)
               }

  p = os.path.join(os.path.abspath(base_dir), str(t.tm_year), str(t.tm_mon))

  os.makedirs(p, exist_ok = True)
  p = os.path.join(p, files.make_filename_safe_title(title) + ".md")

  with open(p, "w", encoding="utf-8") as f:
      json.dump(metadata, f, indent="  ")

  print(p, "created")
  

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("command", choices=["init", "build", "clean", "new", "list"])
  args = parser.parse_args()
  
  {'init' : init ,
   'new' : new }[args.command]()
   