# scratch code to generate markdown for a thumbnail collection

l = []
for i in Path("/Users/andrew/Documents/blog/2026/8/borneo_pictures/thumbs").iterdir():
     l.append(i)

a = "[![{{description}}]({{thumb}})]({{fullsized}})"

for i in l:
     t = a
     thumb = pathlib.Path(*(i.parts[-3:]))
     fullsize = pathlib.Path(thumb.parts[0], thumb.parts[2])
     t = t.replace("{{thumb}}", str(thumb))
     t = t.replace("{{fullsized}}", str(fullsize))
     print(t)
