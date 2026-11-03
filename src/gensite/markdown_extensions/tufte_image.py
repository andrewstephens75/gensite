# Markdown extension that turns <img> tags into <figure> tags with captions
# Also builds a list of images for further processing

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markdown.util import etree

class TufteFigureTreeProcessor(Treeprocessor):
    def __init__(self):

    def run(self, root):
        # etree sucks
        parents = root.findall(".//img/..")
        for parent in parents:
