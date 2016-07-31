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
import subprocess

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
    raise CommandError("No site config file exists : " + site_config_file)
    
  with open(site_config_file, "r", encoding="utf-8") as f:
    site_config = json.load(f)
  return site_config
  
def new():
  """ creates a file from the template """
  user_config = read_user_config()
  base_dir = user_config["source_dir"]
  site_config = read_site_config(base_dir)
  author = site_config["blog_author"]
  title = input("Enter the title: ")
  
  p = files.create_new_article(base_dir, title, author, time.gmtime()) 

  print(p, "created")
  
def build():
  user_config = read_user_config()
  base_dir = user_config["source_dir"]
  site_config = read_site_config(base_dir)
  
  files.gensite(base_dir)
  
def deploy():
  user_config = read_user_config()
  base_dir = user_config["source_dir"]
  site_config = read_site_config(base_dir)
  build_dir = site_config["destination_dir"]
  command = user_config["deploy_command"]
  
  subs_command = []
  for a in command:
    if a == "{{build_dir}}":
      t = build_dir
      if (t[-1:] != "/"):
        t = t + "/"
      subs_command.append(t)
    else:
      subs_command.append(a)
    
  print("Running: " + str(subs_command))
  
  subprocess.run(subs_command)
  
  
  

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("command", choices=["init", "build", "deploy", "clean", "new", "list"])
  args = parser.parse_args()
  
  {'init' : init ,
   'new' : new,
    'build' : build,
    'deploy' : deploy}[args.command]()
   