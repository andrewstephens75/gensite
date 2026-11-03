from exif import Image
from .avif_exif import avif_image
import shutil


def copy_image_remove_gps(sourcePath, destPath):
    if sourcePath.endswith(".avif"):
        shutil.copy(sourcePath, destPath)
        with open(destPath, "r+b") as f:
            t = avif_image.AvifImage(f)
            t.scan()
            t.overwriteSensitiveXmlData()
            return True
    elif sourcePath.endswith(".png"):
        shutil.copy(sourcePath, destPath)
        return True
    else:
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

    
