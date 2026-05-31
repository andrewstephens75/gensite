import struct

class AvifImageException(Exception):
    pass    

class FileExtent:
    """
    A simple class to help with sanity checking of blocks and boxes. All reads should go through a FileExtent, the read*
    methods do additional checking to make sure the bytes are contained in the box they say they are in.
    Usage: 
    t = FileExtent(baseFile, offset, length)
    t.open() # actually seeks
    """
    def __init__(self, baseFile, offset, length):
        self.baseFile = baseFile
        self.offset = offset
        self.length = length
        self.bytesLeft = 0

    def open(self):
        self.bytesLeft = self.length
        self.baseFile.seek(self.offset, 0)

    def readBuffer(self, length):
        if (self.bytesLeft < length):
            raise AvifImageException("buffer too small")
        buffer = self.baseFile.read(length)
        if len(buffer) != length:
            raise AvifImageException("file ended unexpectedly")
        self.bytesLeft -= length
        return buffer
    
    def readUnsigned2Bytes(self):
        buffer = self.readBuffer(2)
        return struct.unpack(">H", buffer)[0]
    
    def readUnsigned4Bytes(self):
        buffer = self.readBuffer(4)
        return struct.unpack(">I", buffer)[0]

    def readUnsigned8Bytes(self):
        buffer = self.readBuffer(8)
        return struct.unpack(">Q", buffer)[0]
    
    def readFourCC(self):
        buffer = self.readBuffer(4)
        return buffer.decode("utf-8")
    
    def readItemBoxHeader(self):
        buffer = self.readBuffer(4) 
        return struct.unpack("bbbb", buffer)
    
    def readString(self):
        # it is apparently not an error to have 0 bytes left - just denotes an empty string
        result = ""
        byteArray = []
        while self.bytesLeft > 0:
            byte = self.baseFile.read(1)
            if len(byte) == 0:
                raise AvifImageException("file ended unexpectedly")
            if byte[0] == 0:
                break
            byteArray.append(byte[0])
            self.bytesLeft -= 1
        b = bytes(byteArray)
        return b.decode("utf-8")
    
    def readOneChar(self):
        buffer = self.readBuffer(1)
        return chr(buffer[0])

def _scanForTag(f:FileExtent):
    c = 0
    tagContents = ""
    while c != '<':
        c = f.readOneChar()
    c = f.readOneChar()
    while c != '>':
        tagContents += c
        c = f.readOneChar()
    return tagContents.split(" ")[0]

# Possibly the world's worst xml parser. Extracts a list of tags with the byte extents
# for processing later. Probably does bad things with malformed xml
def _extractTagPositions(f:FileExtent):
    stack = []
    results = []
    while True:
        try:
            tagName = _scanForTag(f)
        except AvifImageException as err:
            break
        if (tagName[0] == '/'):
            oldTagName, oldTagContentsOffset = stack.pop()
            if ("/" + oldTagName != tagName):
                raise Exception("Mismatched tag names {} {}" % (oldTagName, tagName))
            endContentsOffset = f.baseFile.tell() - len(tagName) - 2
            results.append((oldTagName, oldTagContentsOffset, endContentsOffset - oldTagContentsOffset))
        else:
            stack.append((tagName, f.baseFile.tell()))
    return results


class AvifImage:
    """
    Utility class for parsing the blocks and boxes out of an AVIF image in a heif container. Does just enough work to get the positions of all the iinf boxes.
    Has a very bad XML parser to dump out the tags in any rdf boxes and a hacky way of overwriting sensitive data.
    This will probably all fall apart on malformed (or even just complicated) files
    Usage:
            with open(destPath, "r+b") as f:
                t = avif_image.AvifImage(f)
                t.scan()
                t.overwriteSensitiveXmlData()

    I've tried to make the parser throw AvifImageException for anything that looks weird or is unhandled
    """

    class Extent:
        offset = 0
        length = 0

    class Item:
        id = 0
        extents = []
        type = ""
        mimeType = ""
        uri = ""

        def totalDataSize(self):
            total = 0
            for e in self.extents:
                total = total + e.length
            return total

        def readDataFromExtents(self, file):
            result = bytearray()
            for e in self.extents:
                file.seek(e.offset, 0)
                result.extend(file.read(e.length))
            return result


    def __init__(self, f):
        self.file = f
        self.blocks = {}
        self.items = {}
        self.xmlTags = []

    def scan(self):
        self.scanBlocks()
        self.scanSubBlock("meta")
        self.parseIloc()
        self.parseIinfBox()
        self.scanXmlBoxes()

    def read4ByteLength(self):
        bytes = self.file.read(4)
        if len(bytes) < 4:
            return None
        result = struct.unpack(">I", bytes)[0]
        return result

    def readBoxHeader(self):
        pos = self.file.tell()
        length = self.read4ByteLength()
        if length == None:
            return None
        bytes = self.file.read(4)
        type = bytes.decode('utf-8')
        dataOffset = pos + 8
        dataLength = length - 8
        if (len(bytes) != 4):
            return None
        if length == 1:
            # 64 bit length stored after the name
            length = self.readUnsigned8Bytes()
            dataOffset = pos + 16
            dataLength = length - 16

        return (pos, length, type, dataOffset, dataLength)

    def scanBlocks(self):
        while True:
            result = self.readBoxHeader()
            if result == None:
                break
            pos, length, name, _, _ = result
            if len(name) == 0:
                break
            self.blocks[name] = {"pos": pos, "length": length}
            self.file.seek(length - 8, 1)
    
    def readBlock(self, name):
        # this is going to be wrong for blocks with 64 bit length
        details = self.blocks.get(name)
        pos = details["pos"]
        length = details["length"]
        self.file.seek(pos + 8, 0)
        buffer = self.file.read(length - 8)
        return buffer
    
    def scanSubBlock(self, parent):
        details = self.blocks.get(parent)
        pos = details["pos"]
        length = details["length"]
        self.file.seek(pos + 8 + 4, 0)  # meta block has 4 bytes of something in the header
        bytesConsumed = 0
        boxNumber = 0
        while bytesConsumed < length - (8 + 4):
            result = self.readBoxHeader()
            if result == None:
                break
            blockPos, blockLength, name, _, _ = result
            fullName = parent + "." + name
            boxNumber = boxNumber + 1

            self.blocks[fullName] = {"pos": blockPos, "length": blockLength}
            self.file.seek(blockLength - 8, 1)
            bytesConsumed = bytesConsumed + blockLength

    def getFileExtentForNamedBlocksData(self, name):
        boxDetails = self.blocks.get(name)
        self.file.seek(boxDetails["pos"], 0)
        _, _, name, dataOffset, dataLength = self.readBoxHeader()
        blockExtent = FileExtent(self.file, dataOffset, dataLength)
        return blockExtent

    def parseIinfBox(self):
        subFile = self.getFileExtentForNamedBlocksData("meta.iinf")
        subFile.open()

        version, flag1, flag2, flag3 = subFile.readItemBoxHeader()

        numItemInfoBoxes = 0
        if (version > 0):
            numItemInfoBoxes = subFile.readUnsigned4Bytes()
        else:
            numItemInfoBoxes = subFile.readUnsigned2Bytes()

        for i in range(0, numItemInfoBoxes):
            self.parseInfeBox()


    def parseInfeBox(self):
        _, _, name, dataOffset, dataLength = self.readBoxHeader()

        infeSubFile = FileExtent(self.file, dataOffset, dataLength)
        infeSubFile.open()
        
        version, flag1, flag2, flag3 = infeSubFile.readItemBoxHeader()

        itemContentType = ""
        itemName = "unknown"
        itemContentEncoding = ""
        itemUri = ""
        # version 1
        if (version <= 1):
            itemId = infeSubFile.readUnsigned2Bytes()
            itemProtectionIndex = infeSubFile.readUnsigned2Bytes()
            itemName = infeSubFile.readString()
            itemContentType = infeSubFile.readString()
            itemContentEncoding = infeSubFile.readString()
            itemType4CC = ""

        if (version >= 2):
            hiddenItem = flag3 & 0x01;

            if (version == 2):
                itemId = infeSubFile.readUnsigned2Bytes()
            else:
                itemId = infeSubFile.readUnsigned4Bytes()

            itemProtectionIndex = infeSubFile.readUnsigned2Bytes()
            itemType4CC = infeSubFile.readFourCC()
            itemName = infeSubFile.readString()
            if itemType4CC == "mime":
                itemContentType = infeSubFile.readString()
                itemContentEncoding = infeSubFile.readString()
            elif itemType4CC == "uri ":
                itemUri = infeSubFile.readString()
                
        
        if itemId not in self.items:
            self.items[itemId] = AvifImage.Item
        
        self.items[itemId].id = itemId
        self.items[itemId].type = itemType4CC
        self.items[itemId].name = itemName
        self.items[itemId].mimeType = itemContentType
        self.items[itemId].uri = itemUri

    def parseIloc(self):
        # https://github.com/strukturag/libheif/blob/9f7c289d09da044c7ec040d4efe238f3df57fdeb/libheif/box.cc#L438
        # 4 bytes full header (version, flag1, flag2, flag3)
        # 2 bytes size info
        # 2 bytes num items
        ilocSubFile = self.getFileExtentForNamedBlocksData("meta.iloc")
        ilocSubFile.open()

        version, flag1, flag2, flag3 = ilocSubFile.readItemBoxHeader()

        values4 = ilocSubFile.readUnsigned2Bytes()
        offset_size = (values4 >> 12) & 0xf
        length_size = (values4 >> 8) & 0xf
        base_offset_size = (values4 >> 4) & 0xf
        index_size = 0

        if (version == 1 or version == 2):
            index_size = values4 & 0xF

        itemCount = 0
        if (version < 2):
            itemCount = ilocSubFile.readUnsigned2Bytes()
        else:
            itemCount = ilocSubFile.readUnsigned4Bytes()

        for itemNum in range(0, itemCount):
            if version < 2:
                itemId = ilocSubFile.readUnsigned2Bytes()
            else: 
                itemId = ilocSubFile.readUnsigned4Bytes()

            self.items[itemId] = AvifImage.Item()
            self.items[itemId].id = itemId

            if version >= 1:
                values4 = ilocSubFile.readUnsigned2Bytes()
                constructionMethod = values4 & 0xF

            refIndex = ilocSubFile.readUnsigned2Bytes()

            # base offset if it exists
            baseOffset = 0
            if (base_offset_size == 4):
                baseOffset = ilocSubFile.readUnsigned4Bytes()
            elif (base_offset_size == 8):
                baseOffset =ilocSubFile.readUnsigned8Bytes()
            
            numExtents = ilocSubFile.readUnsigned2Bytes()
            extents = []
            for extent in range(0, min(numExtents, 6)):
                extentOffset = ilocSubFile.readUnsigned4Bytes()
                extentLength = ilocSubFile.readUnsigned4Bytes()

                extent = AvifImage.Extent()
                extent.offset = extentOffset + baseOffset
                extent.length = extentLength
                extents.append(extent)
            
            self.items[itemId].extents = extents

    def dumpItems(self):
        """ debugging only """
        for i in self.items.values():
            print("Item#", i.id, " : ", i.name, "(", i.type, ") mime", i.mimeType)
            for e in i.extents:
                print("   ", e.offset, " - ", e.length)

    def getFirstFileExtentForItem(self, itemId):
        if itemId in self.items:
            if len(self.items[itemId].extents) != 1:
                raise AvifImageException("Item does not have one extent - too confusing")
            firstExtent = self.items[itemId].extents[0]
            return FileExtent(self.file, firstExtent.offset, firstExtent.length)
        raise AvifImageException("ItemId not found")
    
    def scanXmlBoxes(self):
        for k, v in self.items.items():
            if v.type == "mime" and v.mimeType == "application/rdf+xml":
                fe = self.getFirstFileExtentForItem(v.id)
                fe.open()
                allTags = _extractTagPositions(fe)
                self.xmlTags.extend(allTags)

    def overwriteSensitiveXmlData(self):
        sensitiveTagPrefixes = ["exif:GPS", "mwg-rs:Regions"]
        for a in self.xmlTags:
            for prefex in sensitiveTagPrefixes:
                if a[0].startswith(prefex):
                    # fill the tag with 0x20 (spaces)
                    self.file.seek(a[1], 0)
                    tempBuffer = bytearray([0x20]) * a[2]
                    self.file.write(tempBuffer)
        self.file.flush()

        
    







    
    # https://github.com/adobe/XMP-Toolkit-SDK/blob/7093513bd3caaad29da01db0f275d88a39d6bcc2/XMPFiles/source/FormatSupport/META_Support.cpp#L257





