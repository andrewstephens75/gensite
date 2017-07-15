import markdown
import os
import os.path
import json
import io
import time
import shutil
from .markdown_extensions import tufte_aside
from .markdown_extensions import tufte_figure
import lxml
import lxml.html
import lxml.etree
import datetime
import html

from . import siteconfig
from . import errors


def make_filename_safe_title(s):
    """ removes illegal path characters from title """
    illegal = {" " : "_",
               "/" : "-slash-",
               "\\" : "-slash-",
               "?" : "",
               "#": "",
               ">" : "",
               "<" : "",
               ":": "-",
               "&" : ""}
    for k, v in illegal.items():
        s = s.replace(k, v)
    s = s.lower()
    return s[0:50]

def pretty_date(d):
  """ returns a html formatted pretty date """
  special_suffixs = {1 : "st", 2 : "nd" , 3 : "rd", 21 : "st", 22 : "nd", 23 : "rd", 31 : "st"}
  suffix = "th"

  if d.tm_mday in special_suffixs:
    suffix = special_suffixs[d.tm_mday]

  suffix = "<sup>" + suffix + "</sup>"

  day = time.strftime("%A", d)
  month = time.strftime("%B", d)

  return day + " the " + str(d.tm_mday) + suffix + " of " + month + ", " + str(d.tm_year)

class FileDef:
    """ Stores file name and modification date """
    def __init__(self, file_name, cache=False, relative_path = ""):
        self.file_name = file_name
        self.mod_time = 0
        self.contents = None
        self.relative_path = relative_path
        if (os.path.exists(self.file_name)):
            self.mod_time = os.path.getmtime(self.file_name)
            if (cache == True):
               self.contents = self.contentsFromUtf8()

    def contentsFromUtf8(self):
        if (self.contents is not None):
            return self.contents
        contents = ""
        with open(self.file_name, encoding="utf-8") as f:
            contents = f.read()
        return contents

    def older(self, other):
        if (other.mod_time == 0):
            return False
        if (self.mod_time == 0):
            return False
        return (self.mod_time < other.mod_time)

    def copy_if_required(self, destDir):
        """ Copies the file to the destDir (maybe a subdirectory if relative paths are used) """
        """ But only if the modification date is earlier than the existing file """
        dest_file = destDir
        if self.relative_path != "":
            dest_file = os.path.join(destDir, self.relative_path)
        os.makedirs(dest_file, exist_ok=True)
        dest_file = os.path.join(dest_file, os.path.split(self.file_name)[-1])
        dest_time = 0
        if (os.path.exists(dest_file)):
            dest_time = os.path.getmtime(dest_file)
        if (dest_time == 0 or self.mod_time > dest_time):
            shutil.copy2(self.file_name, dest_file)
            return True
        return False

class SourceFileDef(FileDef):
    def __init__(self, file_name, cache=False, relative_path = "", site_config = None):
        super().__init__(file_name, cache, relative_path)
        self.summary = ""
        self.images = []
        self.processed_text = ""
        self.site_config = site_config
        try:
            self.metadata, self.contents = self.split_header_contents()
            self.original_date = time.strptime( self.metadata["original_date"], "%a, %d %b %Y %H:%M:%SZ")
            self.output_filename = make_filename_safe_title(self.metadata["title"])
            self.processed_text = markdown.markdown(self.contents, extensions=["codehilite", "fenced_code", tufte_aside.TufteAsideExtension(), tufte_figure.TufteFigureExtension()])
            self.summarize_markup();
        except Exception as err:
            raise CompileError(str(err), file_name)

    def split_header_contents(self):
        """ Gets the json header from the file and leaves the file pointer at the first
            character of the article """
        with open(self.file_name, encoding="utf-8") as file:
            inquotes = False
            parenthesis = 0
            pos = 0
            json_string = ""
            while True:
                c = file.read(1)
                json_string = json_string + c
                if (c == '{' and inquotes ==False):
                        parenthesis = parenthesis + 1
                if (c == '}' and inquotes ==False):
                        parenthesis = parenthesis - 1
                        if (parenthesis == 0):
                                break;
                if (c == '"'):
                        inquotes = not inquotes

            c = file.read(1)
            pos = file.tell()
            while (c.isspace()):
               pos = file.tell()
               c = file.read(1)
            file.seek(pos)
            contents = file.read()
            return (json.loads(json_string), contents)


    def dest_files(self):
        """ return a list of filenames that this file requires """
        return [self.file_name]

    def dest_file_name(self):
        t = self.template_type()
        if t == "article":
            t = self.original_date
            p = os.path.join(str(t.tm_year), str(t.tm_mon))
            p = os.path.join(p, self.output_filename + ".html")
            return p
        elif t == "index":
            return "index.html"
        elif t == "tag_cloud":
            return "tagcloud.html"
        elif t == "static_page":
            return os.path.join(self.relative_path, self.output_filename + ".html")
        else:
            raise CompileError("Unknown template type " + t, self.file_name)

    def template_type(self):
        return self.metadata["template_type"]

    def title(self):
        return self.metadata["title"]

    def publish(self):
      if "publish" not in self.metadata:
        return True
      else:
        return self.metadata["publish"]

    def tags(self):
        if "tags" not in self.metadata:
            return []
        else:
            return self.metadata["tags"]

    def summary(self):
        return self.summary

    def images(self):
        return self.images

    def summarize_markup(self):
        """ parse some markup and try to extract some meaningful text """
        try:
            elements = lxml.html.fragments_fromstring(self.processed_text);
        except lxml.etree.XMLSyntaxError:
            print("XMLSyntaxError when parsing markup")
            return

        summary = ""

        for e in elements:
            for i in e.findall(".//img"):
                folder = os.path.split(self.dest_file_name())[0]
                image_url = self.site_config.root_url + folder + "/" + i.get("src");
                self.images.append(image_url);

            if (e.tag != "p"):
                continue

            for t in e.findall(".//span"):
                c = t.get("class");
                if c:
                    if ((c.find("sidenote") != -1) or
                       (c.find("importantmarginnote") != -1)):
                       t.drop_tree();

            summary += e.text_content();

        """ grab the first 30 words """
        summary = " ".join(summary.split(maxsplit=30)[:30]) + "...";
        self.summary = summary;
