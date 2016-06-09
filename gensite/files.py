import markdown
import os
import os.path
import json
import io
import time
import shutil
from markdown_extensions import tufte_aside

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
        print("scanning " + p)
        if (os.path.isfile(p)):
            results.append(current)
        if (os.path.isdir(p)):
            for de in os.scandir(p):
                if de.name.startswith("."):
                    continue
                print(de.name)
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
            os.path.join(destDir, self.relative_path)
        os.makedirs(dest_file, exist_ok=True)
        dest_file = os.path.join(dest_file, os.path.split(self.file_name)[-1])
        dest_time = 0
        if (os.path.exists(dest_file)):
            dest_time = os.path.getmtime(dest_file)
        if (self.mod_time < dest_time):
            shutil.copy2(self.file_name, dest_file)
        

class SourceFileDef(FileDef):
    def __init__(self, file_name, cache=False):
        super().__init__(file_name, cache)
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
    
    
class GenSiteTemplate:
    """ Contains the template handling functionality """
    
    def __init__(self, template_path):
        self.template_path = template_path
        config = {}
        with open(os.path.join(self.template_path, "config.js"), encoding='utf-8') as f:
            config = json.load(f)

        # load the prefixes and sufixes into memory
        article = config["article"]
        self.article_template = FileDef(os.path.join(self.template_path, article["page_template"]), cache=True)
 
        self.static_files = []
        for f in config["static_files"]:
            path = os.path.join(template_path, f)
            if os.path.isfile(path):
                self.static_files.append(FileDef(path, cache=False, relative_path=os.path.split(f)[0]))
            else:
                dir_files = get_files_in_dir(path)
                for d in dir_files:
                    self.static_files.append(FileDef(os.path.join(path, d), cache=False, relative_path=os.path.split(d)[0]))
        print("Template loaded with " + str(len(self.static_files)) + " static files")


    def process_source_file(self, sourceFileDef, destDir):
        """ process a source file and output the files required """
        header = sourceFileDef.metadata
        title = header["title"]
        author = header["author"]
        template_type = header["template_type"]

        outputFileDef = FileDef(os.path.join(destDir, make_filename_safe_title(title) + ".html"))
        if (sourceFileDef.older(outputFileDef)):
            return

        if (template_type != "article"):
            raise CompileError("Unknown template type: " + template_type, sourceFileDef.file_name)

        article_text = markdown.markdown(sourceFileDef.contents, extensions=["codehilite", "fenced_code", tufte_aside.TufteAsideExtension()])
        html_source = self.article_template.contents
        html_source = html_source.replace("{{article_content}}", article_text)
        html_source = html_source.replace("{{title}}", title)
        html_source = html_source.replace("{{author}}", author)

        with open(outputFileDef.file_name, "w", encoding="utf-8") as f:
            f.write(html_source)

    def copy_template_files(self, destDir):
        print("Copying template files:")
        for f in self.static_files:
            print("  " + f.file_name)
            f.copy_if_required(destDir)

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

def create_file(baseDir, title, author):
    """ creates a file from the template """

    t = time.gmtime();
    metadata = { "title" : title,
                 "author" : author,
                 "template_type" : "article",
                 "original_date" : time.strftime("%a, %d %b %Y %H:%M:%SZ", t)
                 }

    p = os.path.join(os.path.abspath(baseDir), str(t.tm_year), str(t.tm_mon))
    
    os.makedirs(p, exist_ok = True)
    p = os.path.join(p, make_filename_safe_title(title) + ".md")

    with open(p, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent="  ")

    print(p, "created")

    

def gensite(rootdir):
    """ reads the site config, loads the template, and processes each file it finds """
    site_config = {}
    with open(os.path.join(rootdir, "config.js"), encoding="utf-8") as config_file:
        site_config = json.load(config_file)

    template = GenSiteTemplate(os.path.join(rootdir, site_config["template"]))
    destdir = os.path.join(rootdir, site_config["destination_dir"])
    sourcedir = os.path.join(rootdir, site_config["source_dir"])

    files = gather_source_files(sourcedir, [".md"])
    files.sort(key=lambda s: s.original_date)

    files_to_be_regenerated = []
    for f in files:
        output_file = os.path.join(destdir, f.output_filename)
        mod_time = 0
        if (os.path.exists(output_file)):
            mod_time = os.path.getmtime(output_file)

        if (mod_time < f.mod_time):
            files_to_be_regenerated.append(f)

    print("Will generate ", str(len(files_to_be_regenerated)), "files")

    for f in files_to_be_regenerated:
        print("   processing", f.metadata["title"])
        template.process_source_file(f, destdir)
    
    template.copy_template_files(destdir)
        




    

                               
