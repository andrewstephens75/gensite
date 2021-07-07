# GENSITE

A static webside generator written in Python 3. I use this code to maintain my blog - [sheep.horse](https://sheep.horse/)

## Goals of this Project

* Simple to use, idiot-proof static website generator
* Configurable, but designed specifically for blog-like structures
* Article creation and editing should be easy
* Default template produces clean, simple, and modern html5 without relying on external libraries.
* All text files are UTF8 - no exceptions

## Dependencies

I try to keep the list of dependeccies very short. Please note that the Markdown python package
introduced breaking changes so 2.6.11 is the last supported version that works.

Python 3

pip3 install Markdown==2.6.11

pip3 install Pygments

pip3 feedgen
