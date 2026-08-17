# scratch code to generate markdown for a thumbnail collection
import argparse
import pathlib

if __name__ == "__main__":
     parser = argparse.ArgumentParser()
     parser.add_argument("dir", help="Relative Path to Thumbs Directory")
     args = parser.parse_args()

     template = "[![Description]({{thumb}})]({{fullsized}})"
     images = []
     for i in pathlib.Path(args.dir).iterdir():
          images.append(i)

     for i in images:
          t = template
          thumb = pathlib.Path(*(i.parts[-3:]))
          fullsize = pathlib.Path(thumb.parts[0], thumb.parts[2])
          t = t.replace("{{thumb}}", str(thumb))
          t = t.replace("{{fullsized}}", str(fullsize))
          print(t)
     