# Export files from a wordpress database to a directory structure with
# formatted gensite-style files

import os
import pymysql
import files
import argparse
import datetime

def export(host, port, user, password, database, output_dir, author):
  results = []
  connection = pymysql.connect(host=host, port=port, user=user, password=password, db=database)
  try:    
    with connection.cursor() as c:
      c.execute("select post_title, post_content, post_modified_gmt from wp_posts where post_type='post'")
      while True:
        result = c.fetchone()
        if result == None:
          break
        if (result[2] == None):
          continue
        title = result[0]
        content = result[1].replace("\r\n", "\n")
        note = " ->[This post was automatically imported from my old sandfly.net.nz blog. It may look a little weird since it was not originally written for this format.]"
        pos = content.find(".")
        content = content[:pos] + note + content[pos:]
        t = result[2].timetuple()
        p = files.create_new_article(output_dir, title, author, t, initial_contents=content)
        print(p, " created")
  finally:
    connection.close()

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("host", help="DB Server Host")
  parser.add_argument("port", type=int, help="DB Service Port")
  parser.add_argument("user", help="User name")
  parser.add_argument("password", help="Password")
  parser.add_argument("database", help="Database")
  parser.add_argument("dest", help="Destination directory")
  parser.add_argument("author", help="Post author")
  
  args = parser.parse_args()
  
  export(args.host, args.port, args.user, args.password, args.database, args.dest, args.author)

        
      
      