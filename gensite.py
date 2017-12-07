# main interface for using gensite
# gensite init - writes .gensite file
# gensite build
# gensite clean
# gensite new
# gensite list

import argparse
import os.path

import json
import io
import time
import subprocess

from gensite import files
from gensite import siteconfig
from gensite import userconfig

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
    "relative_index" : "/",
    "allowed_tags" : []
  }

  with open("config.js", "w", encoding="utf-8") as f:
    json.dump(site_metadata, f)

  print("OK - edit config.js file")



def new():
  """ creates a file from the template """
  user_config = userconfig.read_user_config()
  base_dir = user_config["source_dir"]
  site_config = siteconfig.SiteConfig(base_dir)
  author = site_config.blog_author
  title = input("Enter the title: ")

  p = files.create_new_article(base_dir, title, author, time.gmtime())

  print(p, "created")

def build():
  user_config = userconfig.read_user_config()
  base_dir = user_config["source_dir"]
  site_config = siteconfig.SiteConfig(base_dir)

  files.gensite(base_dir)

def deploy():
  user_config = userconfig.read_user_config()
  base_dir = user_config["source_dir"]
  site_config = siteconfig.SiteConfig(base_dir)
  build_dir = site_config.destination_dir
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

def print_valid_tags():
  user_config = userconfig.read_user_config()
  base_dir = user_config["source_dir"]
  site_config = siteconfig.SiteConfig(base_dir)

  print("Valid tags:")
  for t in site_config.allowed_tags:
    print("   ", t)

def print_untagged():
   user_config = userconfig.read_user_config()
   base_dir = user_config["source_dir"]
   site_config = siteconfig.SiteConfig(base_dir)

   sourcedir = os.path.join(base_dir, site_config.source_dir)
   all_source_files = files.gather_source_files(sourcedir, [".md"])
   articles, unpublished_articles = files.get_articles(all_source_files)

   tags_for_articles, untagged = files.get_tags_for_articles(articles)

   for i in untagged:
       print(i.file_name)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("command", choices=["init", "build", "deploy", "clean", "new", "untagged", "tags"])
  args = parser.parse_args()

  {'init' : init ,
   'new' : new,
    'build' : build,
    'deploy' : deploy,
    'tags' : print_valid_tags,
    'untagged' : print_untagged}[args.command]()
