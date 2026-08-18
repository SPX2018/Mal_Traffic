
# read file as bytes and transfer it into base64. Finally decode it by utf-8
import base64
def readToBase64(file_path : str):
    with open(file_path, 'rb') as f:
        file_rawData = f.read()
    return base64.b64encode(file_rawData).decode("utf-8")
    