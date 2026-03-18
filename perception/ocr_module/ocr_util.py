import os
from paddleocr import PaddleOCR


class OCRUtil:
    def __init__(self, lang='ch'):
        # paddleocr 3.4 自动检测GPU，无需use_gpu参数
        self.ocr = PaddleOCR(use_textline_orientation=True, lang=lang)

    def recognize_text(self, image_path):
        '''
        识别图片中的文字，返回文字内容和坐标
        :param image_path: 图片文件路径
        :return: List[{'text': str, 'box': List[List[int]]}]
        '''
        result = self.ocr.ocr(image_path)
        output = []
        for line in result:
            for item in line:
                text = item[1][0]
                box = item[0]
                output.append({'text': text, 'box': box})
        return output

if __name__ == '__main__':
    # 示例用法
    ocr_util = OCRUtil()
    img_path = os.path.abspath('D:/workspace/TFT_Copilot/records/pics/20260318_21/1773841785879.png')  # 替换为你的图片路径
    res = ocr_util.recognize_text(img_path)
    for item in res:
        print(f"内容: {item['text']}, 坐标: {item['box']}")
