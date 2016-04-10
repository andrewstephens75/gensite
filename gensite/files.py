import markdown
import os
import os.path
import json
import io

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


class FileDef:
    """ Stores file name and modification date """
    def __init__(self, file_name, cache=False):
        self.file_name = file_name
        self.mod_time = 0
        self.contents = None
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

class SourceFileDef(FileDef):
    def __init__(self, file_name, cache=False):
        super().__init__(file_name, cache)
        self.metadata, self.contents = self.split_header_contents()

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
            self.static_files.append(FileDef(os.path.join(self.template_path, f), cache=False))

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

        article_text = markdown.markdown(sourceFileDef.contents, extensions=["codehilite", "fenced_code"])
        html_source = self.article_template.contents
        html_source = html_source.replace("{{article_content}}", article_text)
        html_source = html_source.replace("{{title}}", title)
        html_source = html_source.replace("{{author}}", author)

        with open(outputFileDef.file_name, "w", encoding="utf-8") as f:
            f.write(html_source)        
        
    

def gather_source_files(topdir, extensions):
    """ returns a list of files that will be processed """
    lowExt = [t.lower() for t in extensions]
    results = []
    for root, dirs, files in os.walk(topdir):
        for filename in files:
            ext = os.path.splitext(filename)[1]
            if (ext in lowExt):
                results.append(FileDef(os.path.join(root, filename)))
    return results

