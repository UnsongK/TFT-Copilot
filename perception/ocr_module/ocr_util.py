import os
import paddle
from paddleocr import PaddleOCR


class OCRUtil:
    def __init__(self, lang='ch', use_gpu=True, gpu_id=0):
        # 明确设置为使用 GPU（如果可用），并将 use_gpu 传递给 PaddleOCR
        if use_gpu:
            try:
                paddle.set_device(f'gpu:{gpu_id}')
            except Exception:
                # 如果设置设备失败（例如无 GPU），继续使用默认设备
                pass
        self.ocr = PaddleOCR(use_textline_orientation=True, lang=lang, use_gpu=use_gpu)

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
