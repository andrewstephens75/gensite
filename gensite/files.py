import markdown
import os
import os.path
import json
import io
import time
import shutil
from markdown_extensions import tufte_aside
from feedgen.feed import FeedGenerator
import lxml
import lxml.html
import lxml.etree



class CompileError(Exception):
    def __init__(self, message, file_name):
        self.message = message
        self.file_name = file_name

def make_filename_safe_title(s):
    """ removes illegal path characters from title """
    illegal = {" " : "_",
               "/" : "-slash-",
               "\\" : "-slash-",
               "?" : "",
               "#": "",
               ">" : "",
               "<" : "",
               ":": "-"}
    for k, v in illegal.items():
        s = s.replace(k, v)
    s = s.lower()
    return s[0:50]

def get_files_in_dir(startPath):
    """ gets a recursive list of relative paths inside this directory """
    working = [""]
    results = []
    while len(working) > 0:
        current = working.pop(0)
        p = os.path.join(startPath, current)
        if (os.path.isfile(p)):
            results.append(current)
        if (os.path.isdir(p)):
            for de in os.scandir(p):
                if de.name.startswith("."):
                    continue
                working.append(os.path.join(current, de.name))
    return results


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
    def __init__(self, file_name, cache=False, relative_path = ""):
        super().__init__(file_name, cache, relative_path)
        self.metadata, self.contents = self.split_header_contents()
        self.original_date = time.strptime( self.metadata["original_date"], "%a, %d %b %Y %H:%M:%SZ")
        self.output_filename = make_filename_safe_title(self.metadata["title"])

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
        else:
            raise CompileError("Unknown template type " + t, self.file_name)

    def template_type(self):
        return self.metadata["template_type"]

    def title(self):
        return self.metadata["title"]
        
    
    
class GenSiteTemplate:
    """ Contains the template handling functionality """
    
    def __init__(self, template_path):
        self.template_path = template_path
        config = {}
        with open(os.path.join(self.template_path, "config.js"), encoding='utf-8') as f:
            config = json.load(f)

        # load the templates into memory

        self.templates = {}
        for t in ["article", "index"]:
            page_template = config["templates"][t]["page_template"]
            self.templates[t] = FileDef(os.path.join(self.template_path, page_template), cache=True)
         
        self.static_files = []
        for f in config["static_files"]:
            path = os.path.join(template_path, f)
            if os.path.isfile(path):
                self.static_files.append(FileDef(path, cache=False, relative_path=os.path.split(f)[0]))
            else:
                dir_files = get_files_in_dir(path)
                for d in dir_files:
                    self.static_files.append(FileDef(os.path.join(path, d), cache=False, relative_path=os.path.join(f, os.path.split(d)[0])))
        print("Template loaded with " + str(len(self.static_files)) + " static files")


    def process_source_file(self, sourceFileDef, destDir, additional_tags = {}, force_write = False):
        """ process a source file and output the files required """
        header = sourceFileDef.metadata
        title = header["title"]
        author = header["author"]
        template_type = sourceFileDef.template_type()

        dest_file_path = os.path.join(destDir, sourceFileDef.dest_file_name())
        dest_file_dir = os.path.split(dest_file_path)[0]
        os.makedirs(dest_file_dir, exist_ok = True)
        number_of_subdirs = 0
        t = sourceFileDef.dest_file_name().split(os.path.sep)
        number_of_subdirs = len(t) - 1
        relative_path_to_top = "/".join([".."] * number_of_subdirs)
        if (len(relative_path_to_top) > 0):
            relative_path_to_top += '/'

        outputFileDef = FileDef(dest_file_path)
        if (sourceFileDef.older(outputFileDef) and not force_write):
            return

        if (template_type not in self.templates):
            raise CompileError("Unknown template type: " + template_type, sourceFileDef.file_name)

        
        html_source = self.templates[template_type].contents
        for t,v in additional_tags.items():
            html_source = html_source.replace("{{" + t + "}}", v)
        

        html_source = html_source.replace("{{title}}", title)
        html_source = html_source.replace("{{author}}", author)
        html_source = html_source.replace("{{css_relative_path}}", relative_path_to_top)
        
        article_text = markdown.markdown(sourceFileDef.contents, extensions=["codehilite", "fenced_code", tufte_aside.TufteAsideExtension()])
        html_source = html_source.replace("{{article_content}}", article_text)


        with open(outputFileDef.file_name, "w", encoding="utf-8") as f:
            f.write(html_source)

    def copy_template_files(self, destDir):
        num_copied = 0
        for f in self.static_files:
            if f.copy_if_required(destDir):
                num_copied += 1
        print("Copied " + str(num_copied) + " modified template files")

    def generate_index(self, all_files):
        all_files.sort(key=lambda s: s.original_date)
        all_files.reverse()

        index_element = lxml.html.Element("div", {"class": "index"})
        
        group_element = lxml.html.Element("div", {"class" : "group"})
        list_element = lxml.html.Element("ul")
        current_group_date = None
        current_group_len = 0
        
        def same_month_and_year(t1, t2):
          return ((t1.tm_year == t2.tm_year) and (t1.tm_mon == t2.tm_mon))
          
        def emit_grouped_list(list_element):
              group_element = lxml.html.Element("div", {"class" : "group"})
              header_element = lxml.html.Element("div", {"class" : "groupheading"})
              header_element.text = time.strftime("%B %Y", current_group_date)
              group_element.append(header_element)
              group_element.append(list_element)
              index_element.append(group_element)
     
        for f in all_files:
            date = f.original_date
            if (current_group_date == None):
              current_group_date = date
            if (not same_month_and_year(date, current_group_date) and (current_group_len != 0)):
              # emmit the old group
              emit_grouped_list(list_element)
              # start a new group
              list_element = lxml.html.Element("ul")
              current_group_date = date
              current_group_len = 0
                            
            title = f.title()
            template_type = f.template_type()
            item = lxml.html.Element("li")
            link = lxml.html.Element("a", {"href" : f.dest_file_name()})
            link.text = f.title()
            item.append(link)
            list_element.append(item)
            current_group_len += 1
        emit_grouped_list(list_element)
        return index_element

def gather_source_files(topdir, extensions):
    """ returns a list of files that will be processed """
    lowExt = [t.lower() for t in extensions]
    results = []
    for root, dirs, files in os.walk(topdir):
        for filename in files:
            ext = os.path.splitext(filename)[1]
            if (ext in lowExt):
                results.append(SourceFileDef(os.path.join(root, filename)))
    return results


def gensite(rootdir):
    """ reads the site config, loads the template, and processes each file it finds """
    site_config = {}
    with open(os.path.join(rootdir, "config.js"), encoding="utf-8") as config_file:
        site_config = json.load(config_file)

    template = GenSiteTemplate(os.path.join(rootdir, site_config["template"]))
    destdir = os.path.join(rootdir, site_config["destination_dir"])
    sourcedir = os.path.join(rootdir, site_config["source_dir"])

    files = gather_source_files(sourcedir, [".md"])

    articles = [e for e in files if e.template_type() == "article"]
    articles.sort(key=lambda s: s.original_date)
    articles.reverse()
    
    files_to_be_regenerated = []
    for f in articles:
        output_file = os.path.join(destdir, f.dest_file_name())
        mod_time = 0
        if (os.path.exists(output_file)):
            mod_time = os.path.getmtime(output_file)

        if (mod_time < f.mod_time):
            files_to_be_regenerated.append(f)

    print("Will generate ", str(len(files_to_be_regenerated)), "files")

    for f in files_to_be_regenerated:
        extra_article_tags = { "article_menu" : "<a href=\"" + site_config["relative_index"] + "\">Index</a>" }
        template.process_source_file(f, destdir, additional_tags = extra_article_tags)
    
    template.copy_template_files(destdir)

    """ generate feed """
    fg = FeedGenerator()
    fg.id(site_config["blog_name"])
    fg.language("en")
    fg.title(site_config["blog_name"])
    fg.link(href= site_config["root_url"], rel='alternate')
    fg.description(site_config["blog_description"])

    for entry in articles:
        dest_file_name = entry.dest_file_name();
        fe = fg.add_entry()
        fe.id(site_config["root_url"] + dest_file_name)
        fe.title(entry.title())
        fe.content(src=site_config["root_url"] + dest_file_name)

    fg.rss_file(os.path.join(destdir, 'rss.xml'), pretty=True)
    fg.atom_file(os.path.join(destdir, 'atom.xml'), pretty=True)
    
    index_element = template.generate_index(articles)
    index = [e for e in files if e.template_type() == "index"][0]
    i = str(lxml.etree.tostring(index_element, pretty_print=True), "utf-8")    
    template.process_source_file(index, destdir, additional_tags = {"index_content" : i}, force_write=True)

    """ copy static files """
    static_files = get_files_in_dir(sourcedir)
    num_static_files = 0
    for s in static_files:
      t = os.path.join(sourcedir, s)
      if (os.path.splitext(s)[1] == ".md"):
        continue
      if (s == "config.js"):
        continue
      f = FileDef(os.path.join(sourcedir, s), cache=False, relative_path=os.path.split(s)[0])
      if f.copy_if_required(destdir):
        num_static_files += 1
    print("Copied " + str(num_static_files) + " static files")
    
def create_new_article(base_dir, title, author, date, template_type = "article", initial_contents=""):
  metadata = { "title" : title,
               "author" : author,
               "template_type" : "article",
               "original_date" : time.strftime("%a, %d %b %Y %H:%M:%SZ", date),
               "tags" : []
               }

  p = os.path.join(os.path.abspath(base_dir), str(date.tm_year), str(date.tm_mon))

  os.makedirs(p, exist_ok = True)
  p = os.path.join(p, make_filename_safe_title(title) + ".md")

  with open(p, "w", encoding="utf-8") as f:
      json.dump(metadata, f, indent="  ")
      f.write("\n\n")
      f.write(initial_contents)
  return p
                               
