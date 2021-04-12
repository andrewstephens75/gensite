import markdown
import os
import os.path
import json
import io
import time
import shutil
from .markdown_extensions import tufte_aside
from .markdown_extensions import tufte_figure
from feedgen.feed import FeedGenerator
import lxml
import lxml.html
import lxml.etree
import datetime
import html

from . import siteconfig
from . import errors
from .sourcefile import FileDef
from .sourcefile import SourceFileDef
from .sourcefile import make_filename_safe_title
from .sourcefile import pretty_date


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


class GenSiteTemplate:
    """ Contains the template handling functionality """

    def __init__(self, template_path):
        self.template_path = template_path
        config = {}
        with open(os.path.join(self.template_path, "config.js"), encoding='utf-8') as f:
            config = json.load(f)

        # load the templates into memory

        self.templates = {}
        config_templates = config["templates"].keys()

        for t in config_templates:
            page_template = config["templates"][t]["page_template"]
            self.templates[t] = FileDef(os.path.join(
                self.template_path, page_template), cache=True)

        self.static_files = []
        for f in config["static_files"]:
            path = os.path.join(template_path, f)
            if os.path.isfile(path):
                self.static_files.append(
                    FileDef(path, cache=False, relative_path=os.path.split(f)[0]))
            else:
                dir_files = get_files_in_dir(path)
                for d in dir_files:
                    self.static_files.append(FileDef(os.path.join(
                        path, d), cache=False, relative_path=os.path.join(f, os.path.split(d)[0])))
        print("Template loaded with " +
              str(len(self.static_files)) + " static files")

    def replace_mustache_tag(self, html_source, tag, replacement_text, encode=False):
        """ Replaces the tag in the text with (optionally) html escaped replacement """
        if encode:
            return html_source.replace(tag, html.escape(replacement_text, quote=True))
        else:
            return html_source.replace(tag, replacement_text)

    def process_source_file(self, sourceFileDef, destDir, site_config, additional_mustache_tags={}, force_write=False):
        """ process a source file and output the files required """
        header = sourceFileDef.metadata
        title = header["title"]
        author = header["author"]
        template_type = sourceFileDef.template_type()
        full_url = site_config.root_url + sourceFileDef.dest_relative_url()

        dest_file_path = os.path.join(destDir, sourceFileDef.dest_file_name())
        dest_file_dir = os.path.split(dest_file_path)[0]
        os.makedirs(dest_file_dir, exist_ok=True)
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
            raise errors.CompileError(
                "Unknown template type: " + template_type, sourceFileDef.file_name)

        """ Calculate the list of tags for this article"""
        article_tags = []
        for tag_name in sourceFileDef.tags():
            if not site_config.is_tag_allowed(tag_name):
                raise errors.CompileError(
                    "Unknown tag: " + tag_name + ". Add to site config file to use.", sourceFileDef.file_name)
            article_tags.append(site_config.allowed_tags[tag_name])

        article_tags.sort(key=lambda s: s.title)
        all_tag_ids = []
        all_tag_titles = []
        for tag in article_tags:
            all_tag_titles.append(html.escape(tag.title, quote=True))
            all_tag_ids.append(tag.tag)

        tag_link_text = "<a href=\"/tagcloud.html#" + \
            "+".join(all_tag_ids) + "\">" + ", ".join(all_tag_titles) + "</a>"

        article_text = sourceFileDef.processed_text
        summary = sourceFileDef.summary
        image_url = "/favicon.ico"
        if (len(sourceFileDef.images) > 0):
            image_url = sourceFileDef.images[0]

        html_source = self.templates[template_type].contents
        for t, v in additional_mustache_tags.items():
            html_source = self.replace_mustache_tag(
                html_source, "{{" + t + "}}", v)

        html_source = self.replace_mustache_tag(
            html_source, "{{title}}", title, encode=True)
        html_source = self.replace_mustache_tag(
            html_source, "{{author}}", author, encode=True)
        html_source = self.replace_mustache_tag(
            html_source, "{{pretty_date}}", pretty_date(sourceFileDef.original_date))

        iso_date = datetime.datetime.fromtimestamp(time.mktime(
            sourceFileDef.original_date), datetime.timezone.utc)
        html_source = self.replace_mustache_tag(
            html_source, "{{iso_date}}", iso_date.strftime('%Y-%m-%dT%H:%M:%SZ'))
        html_source = self.replace_mustache_tag(
            html_source, "{{full_url}}", full_url)
        html_source = self.replace_mustache_tag(
            html_source, "{{tag_links}}", tag_link_text)
        html_source = self.replace_mustache_tag(
            html_source, "{{twitter_handle}}", site_config.twitter_handle, encode=True)
        html_source = self.replace_mustache_tag(
            html_source, "{{first_words}}", summary, encode=True)
        html_source = self.replace_mustache_tag(
            html_source, "{{first_image}}", image_url)

        html_source = html_source.replace(
            "{{css_relative_path}}", relative_path_to_top)

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

        group_element = lxml.html.Element("div", {"class": "group"})
        list_element = lxml.html.Element("ul")
        current_group_date = None
        current_group_len = 0

        def same_month_and_year(t1, t2):
            return ((t1.tm_year == t2.tm_year) and (t1.tm_mon == t2.tm_mon))

        def emit_grouped_list(list_element):
            group_element = lxml.html.Element("div", {"class": "group"})
            header_element = lxml.html.Element(
                "div", {"class": "groupheading"})
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
            link = lxml.html.Element("a", {"href": f.dest_relative_url()})
            link.text = f.title()
            item.append(link)
            list_element.append(item)
            current_group_len += 1
        emit_grouped_list(list_element)
        return index_element


def gather_source_files(topdir, extensions, site_config):
    """ returns a list of files that will be processed """
    lowExt = [t.lower() for t in extensions]
    results = []
    for root, dirs, files in os.walk(topdir):
        for filename in files:
            ext = os.path.splitext(filename)[1]
            if (ext in lowExt):
                rel_path = root[len(topdir) + 1:]
                results.append(SourceFileDef(os.path.join(
                    root, filename),  relative_path=rel_path, site_config=site_config))
    return results


class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)


def generate_navigation_header(site_config):
    """ generates the navigation header """

    menu_items = site_config.navigation_menu
    nav_tag = lxml.etree.Element("nav")

    for i in menu_items:
        name = i["title"]
        href = i["href"]
        span_tag = lxml.etree.Element("div")
        span_tag.set("class", "menu")
        link_tag = lxml.etree.Element("a")
        link_tag.set("href", href)
        link_tag.text = name
        span_tag.append(link_tag)
        nav_tag.append(span_tag)

    return lxml.etree.tostring(nav_tag).decode("utf-8")


def needs_to_be_regenerated(destdir, file):
    output_file = os.path.join(destdir, file.dest_file_name())
    mod_time = 0
    if (os.path.exists(output_file)):
        mod_time = os.path.getmtime(output_file)

    if (mod_time < file.mod_time):
        return True
    return False


def get_articles(files):
    articles = [e for e in files if (
        e.template_type() == "article" and e.publish() == True)]
    unpublished_articles = [e for e in files if (
        e.template_type() == "article" and e.publish() == False)]
    articles.sort(key=lambda s: s.original_date)
    articles.reverse()

    return articles, unpublished_articles


def get_tags_for_articles(articles):
    tagged_articles = {}
    untagged_articles = []
    for a in articles:
        if len(a.tags()) == 0:
            untagged_articles.append(a)
        else:
            for t in a.tags():
                if t in tagged_articles:
                    tagged_articles[t].append(a)
                else:
                    tagged_articles[t] = [a]
    return tagged_articles, untagged_articles


def build_tagging_data(site_config, articles):
    """ Returns all articles by tag, suitable for constructing a JSON idex """
    tagged_articles, untagged_articles = get_tags_for_articles(articles)

    allowed_tags = site_config.allowed_tags

    all_tags = []
    for tagname, taginfo in allowed_tags.items():
        tagdata = {'tag': tagname,
                   'title': taginfo.title,
                   'articles': []}
        articles_for_tag = tagged_articles[tagname]
        for a in articles_for_tag:
            t = {'title': a.title(),
                 'url': a.dest_relative_url(),
                 'date': time.mktime(a.original_date)}
            tagdata['articles'].append(t)

        all_tags.append(tagdata)

    return all_tags


def gensite(rootdir):
    """ reads the site config, loads the template, and processes each file it finds """
    site_config = siteconfig.SiteConfig(rootdir)

    template = GenSiteTemplate(os.path.join(rootdir, site_config.template))
    destdir = os.path.join(rootdir, site_config.destination_dir)
    sourcedir = os.path.join(rootdir, site_config.source_dir)

    files = gather_source_files(sourcedir, [".md"], site_config)

    articles, unpublished_articles = get_articles(files)

    files_to_be_regenerated = [
        x for x in articles if needs_to_be_regenerated(destdir, x)]
    print("Will generate ", str(len(files_to_be_regenerated)), "files")

    article_menu = generate_navigation_header(site_config)

    for f in files_to_be_regenerated:
        extra_article_mustache_tags = {"article_menu": article_menu}
        template.process_source_file(
            f, destdir, site_config, additional_mustache_tags=extra_article_mustache_tags)

    static_pages = [e for e in files if (
        e.template_type() == "static_page" and e.publish() == True)]
    static_pages_to_be_regenerated = [
        x for x in static_pages if needs_to_be_regenerated(destdir, x)]

    if (len(static_pages_to_be_regenerated) != 0):
        print("Will generate ", str(
            len(static_pages_to_be_regenerated)), " static pages")

    for f in static_pages_to_be_regenerated:
        extra_article_mustache_tags = {"article_menu": article_menu}
        template.process_source_file(
            f, destdir, site_config, additional_mustache_tags=extra_article_mustache_tags)

    template.copy_template_files(destdir)

    """ generate feed """
    fg = FeedGenerator()
    fg.id(site_config.blog_name)
    fg.language("en")
    fg.title(site_config.blog_name)
    fg.link(href=site_config.root_url, rel='alternate')
    fg.description(site_config.blog_description)

    last_articles = articles[:15]
    for entry in last_articles:
        dest_relative_url = entry.dest_relative_url()
        fe = fg.add_entry()
        link = site_config.root_url + dest_relative_url
        fe.id(link)
        fe.title(entry.title())
        fe.link(link={"href": link})

        if (entry.summary == ""):
            fe.summary(entry.title())
        else:
            fe.summary(entry.summary)

        date = datetime.datetime.fromtimestamp(
            time.mktime(entry.original_date), UTC())
        fe.published(date)
        fe.updated(date)

    fg.rss_file(os.path.join(destdir, 'rss.xml'), pretty=True)
    fg.atom_file(os.path.join(destdir, 'atom.xml'), pretty=True)

    index_element = template.generate_index(articles)
    index = [e for e in files if e.template_type() == "index"][0]
    i = str(lxml.etree.tostring(index_element, pretty_print=True), "utf-8")
    template.process_source_file(index, destdir, site_config, additional_mustache_tags={
                                 "index_content": i, "article_menu": article_menu, "rss_path": "/rss.xml"}, force_write=True)

    """ tag cloud stuff """
    tag_cloud_template = [
        e for e in files if e.template_type() == "tag_cloud"][0]
    print(tag_cloud_template)
    tag_cloud_json = json.dumps(build_tagging_data(
        site_config, articles), indent=2, sort_keys=True)
    template.process_source_file(tag_cloud_template,
                                 destdir,
                                 site_config,
                                 additional_mustache_tags={"tag_json": tag_cloud_json,
                                                           "article_menu": article_menu},
                                 force_write=True)

    """ copy static files """
    static_files = get_files_in_dir(sourcedir)
    num_static_files = 0
    for s in static_files:
        t = os.path.join(sourcedir, s)
        if (os.path.splitext(s)[1] == ".md"):
            continue
        if (s == "config.js"):
            continue
        f = FileDef(os.path.join(sourcedir, s), cache=False,
                    relative_path=os.path.split(s)[0])
        if f.copy_if_required(destdir):
            num_static_files += 1
    print("Copied " + str(num_static_files) + " static files")
    if (len(unpublished_articles) != 0):
        print("The following files are marked as unpublished and were not processed: ")
        for u in unpublished_articles:
            print("  ", u.file_name)


def create_new_article(base_dir, title, author, date, template_type="article", initial_contents=""):
    metadata = {"title": title,
                "author": author,
                "template_type": "article",
                "original_date": time.strftime("%a, %d %b %Y %H:%M:%SZ", date),
                "tags": [],
                "publish": False
                }

    p = os.path.join(os.path.abspath(base_dir),
                     str(date.tm_year), str(date.tm_mon))

    os.makedirs(p, exist_ok=True)
    p = os.path.join(p, make_filename_safe_title(title) + ".md")

    with open(p, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent="  ")
        f.write("\n\n")
        f.write(initial_contents)
    return p
