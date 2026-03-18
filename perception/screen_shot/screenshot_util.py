import os
import time
from PIL import ImageGrab

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

class ScreenshotUtil:
    @staticmethod
    def save_screenshot_to_records():
        # 获取当前小时
        hour_folder = time.strftime('%Y%m%d_%H')
        records_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'records/pics', hour_folder))
        ensure_dir(records_dir)
        # 获取当前时间戳（ms级）
        timestamp = int(time.time() * 1000)
        file_path = os.path.join(records_dir, f'{timestamp}.png')
        # 截图
        img = ImageGrab.grab()
        img.save(file_path)
        return file_path

if __name__ == '__main__':
    time.sleep(5)
    path = ScreenshotUtil.save_screenshot_to_records()
    print(f'Screenshot saved: {path}')
