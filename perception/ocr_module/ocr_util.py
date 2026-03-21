import os
import argparse

class OCRUtil:
    def __init__(self, backend='paddle', lang='ch', use_gpu=True, gpu_id=0):
        """初始化 OCR 工具
        backend: 'paddle' 或 'easyocr'
        lang: 简短语言代码 'ch'/'en'，会内部映射到各库所需值
        use_gpu: 是否使用 GPU（若库/环境支持）
        """
        self.backend = backend.lower()
        self.lang = lang
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id

        if self.backend == 'paddle':
            try:
                import paddle
                from paddleocr import PaddleOCR
                if use_gpu:
                    try:
                        paddle.set_device(f'gpu:{gpu_id}')
                    except Exception:
                        pass
                # PaddleOCR 语言参数：'ch'
                self.ocr = PaddleOCR(use_textline_orientation=True, lang=lang, use_gpu=use_gpu)
            except Exception as e:
                raise RuntimeError('无法初始化 PaddleOCR: ' + str(e))

        elif self.backend == 'easyocr':
            try:
                import easyocr
                # easyocr 语言代码：使用 'ch_sim' 表示中文简体，'en' 表示英文
                lang_map = {'ch': 'ch_sim', 'en': 'en'}
                lang_code = lang_map.get(lang, lang)
                # easyocr.Reader 接受语言列表
                self.reader = easyocr.Reader([lang_code], gpu=use_gpu)
            except Exception as e:
                raise RuntimeError('无法初始化 EasyOCR: ' + str(e))
        else:
            raise ValueError('unknown backend: ' + str(backend))

    def recognize_text(self, image_path):
        """识别图片中的文字，返回 List[{'text': str, 'box': List[List[int]]}]"""
        output = []
        if self.backend == 'paddle':
            result = self.ocr.ocr(image_path)
            # PaddleOCR 返回结构为 list(list([box, (text, score)]))
            for line in result:
                for item in line:
                    text = item[1][0]
                    box = [[int(p[0]), int(p[1])] for p in item[0]]
                    output.append({'text': text, 'box': box})

        elif self.backend == 'easyocr':
            # easyocr 返回 list of (bbox, text, prob)
            res = self.reader.readtext(image_path)
            for item in res:
                bbox, text, conf = item
                box = [[int(p[0]), int(p[1])] for p in bbox]
                output.append({'text': text, 'box': box, 'conf': float(conf)})

        return output


def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('image', help='image path')
    p.add_argument('--backend', choices=['paddle', 'easyocr'], default='easyocr')
    p.add_argument('--lang', default='ch')
    p.add_argument('--no-gpu', default=False, action='store_true', help='disable gpu')
    return p.parse_args()


if __name__ == '__main__':
    args = _parse_args()
    use_gpu = not args.no_gpu
    ocr_util = OCRUtil(backend=args.backend, lang=args.lang, use_gpu=use_gpu)
    img_path = os.path.abspath(args.image)
    res = ocr_util.recognize_text(img_path)
    for item in res:
        txt = item.get('text', '')
        box = item.get('box', [])
        conf = item.get('conf', None)
        if conf is not None:
            print(f"内容: {txt}, 置信度: {conf:.3f}, 坐标: {box}")
        else:
            print(f"内容: {txt}, 坐标: {box}")
