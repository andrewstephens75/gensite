# Tufte.css works best if standalone images are wrapped in <figure> tags 
# This extension turns blocks like                                       
#    ![This is a cool image](image.jpg)                                     
# into                 
#    <figure>
#        <img alt="This is a cool image" src="image.jpg" />
#        <figcaption>This is a cool image</figcaption>
#    </figure>

from markdown import Extension
from markdown.blockprocessors import BlockProcessor
import xml.etree.ElementTree as etree
import re 

# copied from markdown 2.6 inlinepatterns.py because these definitions have been removed in 3.0
NOBRACKET = r'[^\]\[]*'
BRK = (
    r'\[(' +
    (NOBRACKET + r'(\[')*6 +
    (NOBRACKET + r'\])*')*6 +
    NOBRACKET + r')\]'
)

IMAGE_LINK_RE = r'\!' + BRK + r'\s*\(\s*(<.*?>|([^"\)\s]+\s*"[^"]*"|[^\)\s]*))\s*\)'
IMAGE_REFERENCE_RE = r'\!' + BRK + r'\s?\[([^\]]*)\]'

# start whitespace  image, whitespace  line ends
FIGURES = [r'^\s*'+IMAGE_LINK_RE+r'(!?)\s*$',  r'^\s*'+IMAGE_REFERENCE_RE+r'\s*$']

class TufteFigure(BlockProcessor):
  FIGURES_RE = re.compile('|'.join(f for f in FIGURES))
  
  def test(self, parent, block): 
      isImage = bool(self.FIGURES_RE.search(block))
      oneLineBlock = (len(block.splitlines())== 1)
      isAlreadyInFigure = (parent.tag == 'figure')

      if (isImage and oneLineBlock and not isAlreadyInFigure):
          return True
      else:
          return False

  def run(self, parent, blocks): 
      raw_block = blocks.pop(0)
      
      match = self.FIGURES_RE.search(raw_block)
      # group 1 is the alt text for ![alt](url); group 11 for ![alt][ref]
      captionText = match.group(1) if match.group(1) is not None else match.group(11)
      trailingBang = match.group(10)

      figure = etree.SubElement(parent, 'figure')
      if (trailingBang == "!"):
        figure.set("class", "fullwidth")
        pos = raw_block.rindex('!')
        raw_block = raw_block[:pos] + raw_block[pos+1:]
      figure.text = raw_block
      

      figcaptionElem = etree.SubElement(figure,'figcaption')
      figcaptionElem.text = captionText 
      
class TufteFigureExtension(Extension):
    def extendMarkdown(self, md):
        # '<ulist' in the 2.6 API meant "just before ulist". In Markdown 3,
        # olist is 40 and ulist is 30, so 35 slots it in the same place.
        md.parser.blockprocessors.register(TufteFigure(md.parser),
                                           'figureAltcaption', 35)

def makeExtension(**kwargs):
    return TufteFigureExtension(**kwargs)
