from exif import Image

def copy_image_remove_gps(sourcePath, destPath):
    try:
        with open(sourcePath, "rb") as input:
            sourceImage = Image(input)
        if (sourceImage.has_exif):  
            for i in sourceImage.list_all():
                if (i.startswith("gps")):
                    del sourceImage[i]
        with open(destPath, "wb") as output:
            output.write(sourceImage.get_file())
        return True
    except Exception as e:
        print("Image File ", sourcePath, " could not be parsed: ", e)
    return False

    
