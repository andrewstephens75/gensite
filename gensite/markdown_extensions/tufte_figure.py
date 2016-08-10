# Tufte.css works best if standalone images are wrapped in <figure> tags 
# This extension turns blocks like                                       
#    ![This is a cool image](image.jpg)                                     
# into                 
#    <figure>
#        <img alt="This is a cool image" src="image.jpg" />
#        <figcaption>This is a cool image</figcaption>
#    </figure>

from markdown import Extension
from markdown.inlinepatterns import IMAGE_LINK_RE, IMAGE_REFERENCE_RE, NOBRACKET, BRK
from markdown.blockprocessors import BlockProcessor
from markdown.util import etree
import re 

# start whitespace  image, whitespace  line ends
FIGURES = [u'^\s*'+IMAGE_LINK_RE+u'\s*$', u'^\s*'+IMAGE_REFERENCE_RE+u'\s*$']

class TufteFigure(BlockProcessor):
  FIGURES_RE = re.compile('|'.join(f for f in FIGURES))
  
  def test(self, parent, block): 
      isImage = bool(self.FIGURES_RE.search(block))
      oneLineBlock = (len(block.splitlines())== 1)
      isAlreadyInFigure = (parent.tag == 'figure')

      # print(block, isImage, isOnlyOneLine, isInFigure, "T,T,F")
      if (isImage and oneLineBlock and not isAlreadyInFigure):
          return True
      else:
          return False

  def run(self, parent, blocks): 
      raw_block = blocks.pop(0)
      captionText = self.FIGURES_RE.search(raw_block).group(1)

      figure = etree.SubElement(parent, 'figure')
      figure.text = raw_block

      figcaptionElem = etree.SubElement(figure,'figcaption')
      figcaptionElem.text = captionText 
      
class TufteFigureExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.parser.blockprocessors.add('figureAltcaption',
                                      TufteFigure(md.parser),
                                      '<ulist')

def makeExtension(configs={}):
    return TufteFigureExtension(configs=configs)