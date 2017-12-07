""" Custom error class from gensite """

class CompileError(Exception):
    def __init__(self, message, file_name):
        self.message = message
        self.file_name = file_name
