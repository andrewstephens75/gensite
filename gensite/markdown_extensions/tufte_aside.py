from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.treeprocessors import Treeprocessor
from markdown.util import etree
import re

MARGINNOTEPATTERN = r'[^\*]\[\-\>([^\]]+)\]'
FOOTNOTEPATTERN = r'\*\[\-\>([^\]]+)\]'

class TafteMargin(Pattern):
    def handleMatch(self, m):
        el = etree.Element('span')
        el.set("class", "importantmarginnote")
        el.text = m.group(2)
        return el

class TafteFootnote(Pattern):
    def handleMatch(self, m):
        el = etree.Element('tafte-footnote-element')
        el.text = m.group(2)
        return el

class TufteAsideExtension(Extension):
    """ Extenstion to build Tufte-style margin notes
        [* This is a margin note that will go in the margin *] """
    def extendMarkdown(self, md, md_globals):

        tafte_magin_tag = TafteMargin(MARGINNOTEPATTERN)
        tafte_footnote_tag = TafteFootnote(FOOTNOTEPATTERN)
        md.inlinePatterns.add('tufte_margin', tafte_magin_tag, '_begin')
        md.inlinePatterns.add('tufte_footnote', tafte_footnote_tag, '_begin')
        pass
    
        
