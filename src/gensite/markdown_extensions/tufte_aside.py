# Markdown extension that allows Tufte-style asides (in conjuction with
# the tufte.css
# Supported syntax:
# ->[This is a margin note. It will be placed next to the main text]
# +->[This is a side note. It will be placed next the main text with a reference number]


from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.treeprocessors import Treeprocessor

import xml.etree.ElementTree as etree

# copied from markdown 2.6 inlinepatterns.py because these definitions have been removed in 3.0
NOBRACKET = r'[^\]\[]*'
BRK = (
    r'\[(' +
    (NOBRACKET + r'(\[')*6 +
    (NOBRACKET + r'\])*')*6 +
    NOBRACKET + r')\]'
)

MARGINNOTEPATTERN = r'\-\>' + BRK   # matches ->[margin note]
SIDENOTEPATTERN = r'\+\-\>' + BRK   # matches +->[side note]


class TufteMargin(InlineProcessor):
    def handleMatch(self, m, data):
        el = etree.Element('span')
        el.set("class", "importantmarginnote")
        # InlineProcessor regexes aren't wrapped in "^(.*?)...(.*)$" like the
        # old Pattern class, so the bracket contents are group 1, not group 2
        el.text = m.group(1)
        return el, m.start(0), m.end(0)


class TufteSidenote(InlineProcessor):
    def handleMatch(self, m, data):
        el = etree.Element('span')
        el.set("class", "sidenote")
        el.text = m.group(1)
        return el, m.start(0), m.end(0)


class TufteSidenoteTreeProcessor(Treeprocessor):
    """ Puts the numbered label and toggle checkbox that tufte.css expects
        in front of each sidenote span:
        <label class="margin-toggle sidenote-number" for="sidenoteN"></label>
        <input type="checkbox" id="sidenoteN" class="margin-toggle"/>
        <span class="sidenote">...</span> """

    def run(self, root):
        # Collect first: inserting while iterating the tree isn't safe
        sidenotes = [(parent, child) for parent in root.iter() for child in parent
                     if child.tag == 'span' and child.get('class') == 'sidenote']

        for n, (parent, span) in enumerate(sidenotes, start=1):
            id = "sidenote" + str(n)
            i = list(parent).index(span)
            # Inserted elements have no tail, so the text around the span is untouched
            parent.insert(i, etree.Element("input", {"type": "checkbox", "id": id, "class": "margin-toggle"}))
            parent.insert(i, etree.Element("label", {"for": id, "class": "margin-toggle sidenote-number"}))


class TufteAsideExtension(Extension):
    """ Extenstion to build Tufte-style margin notes
        ->[This is a margin note that will go in the margin] """
    def extendMarkdown(self, md):
        # Markdown 3 replaced the OrderedDict .add(name, item, location) API with
        # priority-based .register(item, name, priority); higher runs first.
        # Built-in inline patterns top out at 190 (backtick), so these run first,
        # like '_begin' did. Sidenote must beat margin, or "+->[x]" would be
        # consumed as "+" followed by a margin note.
        md.inlinePatterns.register(TufteSidenote(SIDENOTEPATTERN, md), 'tufte_sidenote', 201)
        md.inlinePatterns.register(TufteMargin(MARGINNOTEPATTERN, md), 'tufte_margin', 200)
        # Must run after the 'inline' treeprocessor (20), which creates the spans.
        md.treeprocessors.register(TufteSidenoteTreeProcessor(md), 'tufte_sidenote_tree', 5)


def makeExtension(**kwargs):
    return TufteAsideExtension(**kwargs)
