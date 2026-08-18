from utils.InputToBase64 import readToBase64
class Input:
    def __init__(self, filePath):
        self.FileData = None
        try:
            self.FileData = readToBase64(file_path = filePath)
        except Exception as e:
            print(e)
            raise
    def get_FileData(self):
        return self.FileData