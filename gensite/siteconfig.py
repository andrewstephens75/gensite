import os.path
import json

class Tag:
  def __init__(self, tag, title, icon):
    self.tag = tag
    self.title = title
    self.icon = icon

class SiteConfig:
  
  def __init__(self, site_dir):
    self.site_dir = site_dir
    
    config_file_name = os.path.join(self.site_dir, "config.js")
    
    if not os.path.exists(config_file_name):
      raise CommandError("No site config file exists : " + site_config_file)
    
    site_config = {}
    with open(config_file_name, "r", encoding="utf-8") as f:
      site_config = json.load(f)
    
    self.source_dir       = site_config["source_dir"]
    self.destination_dir  = site_config["destination_dir"]
    self.template         = site_config["template"]
    self.blog_name        = site_config["blog_name"]
    self.blog_description = site_config["blog_description"]
    self.blog_author      = site_config["blog_author"]
    self.root_url         = site_config["root_url"]
    self.relative_index   = site_config["relative_index"]
    self.navigation_menu  = site_config["navigation_menu"]
    
    self.allowed_tags = {}
    tags = site_config["allowed_tags"]
    for t in tags:
      self.allowed_tags[t["tag"]] = Tag(t["tag"], t["title"], t["icon"])

  def is_tag_allowed(self, tag):
    return tag in self.allowed_tags
    

