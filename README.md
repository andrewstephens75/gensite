# GENSITE

A static webside generator written in Python 3. I use this code to maintain my blog - [sheep.horse](https://sheep.horse/)

## Goals of this Project

* Simple to use, idiot-proof static website generator.
* Configurable, but designed specifically for blog-like structures.
* Article creation and editing should be easy.
* Default template produces clean, simple, and modern html5 without relying on external libraries.
* All text files are UTF8 - no exceptions.

## Features

 * Uploaded images have EXIF gps data removed automatically.
 * Images can be displayed in a simple image album.
 * Custom +->[] and ->[] tags for creating sidenotes and asides.
 * Markdown processing including source syntax highlighting.
 * Article tagging.
 * Both blog posts and static pages are supported. 

## Dependencies

Dependencies are now managed with [uv](https://docs.astral.sh/uv/).

## Usage

Install `uv`. Then gensite can be invoked by `uv run gensite.py <command>`.

`uv run gensite.py init` - creates a new blog at the current directory. Edit the config file to customize.

`uv run gensite.py new` - creates a new post.

`uv run gensite.py build` - compiles the blog source and copies all files into the destination directory.

`uv run gensite.py deploy` - runs the configured deploy command to upload built files to your webserver

`uv run gensite.py tags` - prints the configured tags

`uv run gensite.py clean` - completely cleans the build directory, forcing reprocessing every file on the next `build`


