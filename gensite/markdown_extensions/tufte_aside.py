from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.treeprocessors import Treeprocessor
from markdown.util import etree
import re

MARGINNOTEPATTERN = r'[^\*]\[\-\>([^\]]+)\]'
SIDENOTEPATTERN = r'\*\[\-\>([^\]]+)\]'

class TufteMargin(Pattern):
    def handleMatch(self, m):
        el = etree.Element('span')
        el.set("class", "importantmarginnote")
        el.text = m.group(2)
        return el

class TufteSidenote(Pattern):
    def handleMatch(self, m):
        el = etree.Element('span')
        el.set("class", "sidenote")
        el.text = m.group(2)
        return el

class TufteSidenoteTreeProcessor(Treeprocessor):
    def __init__(self):
        self.count = 1
    
    def run(self, root):
        parents = root.findall(".//span[@class='sidenote']/..")
        for parent in parents:
            self.count = 1
            for p in parents:
                children = p.getchildren()
                p.clear()
                for c in children:
                    if (c.tag == 'span') and (c.get('class', "") == 'sidenote'):
                        id = "sidenote" + str(self.count)
                        self.count = self.count + 1
                        p.append(etree.Element("label", {"for" : id, "class" : "margin-toggle sidenote-number"}))
                        p.append(etree.Element("input", {"type": "checkbox", "id": id, "class" : "sidenote"}))
                    p.append(c)
    
            
            

class TufteAsideExtension(Extension):
    """ Extenstion to build Tufte-style margin notes
        [* This is a margin note that will go in the margin *] """
    def extendMarkdown(self, md, md_globals):

        tufte_magin_tag = TufteMargin(MARGINNOTEPATTERN)
        tufte_sidenote_tag = TufteSidenote(SIDENOTEPATTERN)
        turfe_sidenote_tree = TufteSidenoteTreeProcessor()
        md.inlinePatterns.add('tufte_margin', tufte_magin_tag, '_begin')
        md.inlinePatterns.add('tufte_sidenote', tufte_sidenote_tag, '_begin')
        md.treeprocessors.add('tufte_sidenote_tree', turfe_sidenote_tree, '_end')
        pass
    
        
