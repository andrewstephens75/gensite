{
  "title" : "Test article 1",
  "author" : "Andrew Stephens",
  "template_type" : "article",
  "types" : ["general"]
}
# This is a test article to try out some stuff

Well, here we are. GenSite is now able to generate web pages from markdown reasonably well. This document is a quick test to see what sorts of features I would like to have

First up - code blocks:

~~~~
include <stdio>

int main(int argc, char* argv[])
{
  std::cout << "Hello world" << std::endl;
}
~~~~


Next up - my proposed syntax for margin notes [* I think something like this should work out well. Open square brackets and an asterix.] which I think should be simple and foolproof. I'll have to write my own markdown plugin to get this to work though. It doesn't look that hard.

Finally (at least in this document), I want to have an easy way to embed images. Ideally this should:

  * automatically take the source image and produce a scaled down version for embedding on the page. Maybe more than one if the hi-dpi image is required.
  * provide a neat way to specify captions
  * Use the picture tag to provide multiple resolutions.
  * auto-link to the fullsized image
  * whatever else I can think of

+[image_path_name][This is the image caption]








