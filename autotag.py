
from gensite import files
from gensite import siteconfig
from gensite import userconfig
import re
import readline

import json

def writeFile(sourceFile):
    with open(sourceFile.file_name, "w", encoding="utf-8") as output:
        json.dump(sourceFile.metadata, output, indent=2)
        output.write("\n")
        output.write(sourceFile.contents)


def tagArticle(article):
    tags = article.tags()

    validTags = { "b" : "book" ,
                  "f" : "film" ,
                  "t" : "travel" ,
                  "fo" : "food",
                  "po" : "politics",
                  "c" : "computing",
                  "bg" : "board_games",
                  "4" : "48_hours",
                  "p" : "popular",
                  "s" : "scifi",
                  "fa" : "fantasy",
                  "v" : "video",
                  "h" : "happening",
                  "r" : "rant"};

    if (len(tags) == 0):
        print(article.metadata["title"])
        print(article.contents[0:100])

        newtags = []
        error = False

        while (len(newtags) == 0 or error == True):
            error = False
            t = input("Tags: " + ",".join(newtags)).split(",")
            for a in t:
                s = a.strip().lower()
                if s in validTags:
                    newtags.append(validTags[s])
                else:
                    print("Invalid tag: ", s)
                    error = True

        article.metadata["tags"] = newtags

if __name__ == "__main__":
    user_config = userconfig.read_user_config()
    base_dir = user_config["source_dir"]
    site_config = siteconfig.SiteConfig(base_dir)
    articles, unpublished_articles = files.get_articles(files.gather_source_files(base_dir, [".md"]))

    for a in articles:
        tagArticle(a)
        writeFile(a)
