import sys
from PyQt5 import QtWidgets, QtCore, QtGui
import ctypes

class OverlayWidget(QtWidgets.QWidget):
    def __init__(self, lines=None, texts=None):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setWindowTitle('Overlay')
        self.resize(QtWidgets.QApplication.primaryScreen().size())
        self.lines = lines or []  # [(x1, y1, x2, y2), ...]
        self.texts = texts or []  # [(text, x, y, color, font_size), ...]
        self._set_click_through()

    def _set_click_through(self):
        # 仅Windows下设置点击穿透
        hwnd = int(self.winId())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style |= 0x80000 | 0x20  # WS_EX_LAYERED | WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        # 画折线
        pen = QtGui.QPen(QtCore.Qt.green, 2)
        painter.setPen(pen)
        for line in self.lines:
            painter.drawLine(*line)
        # 画文字
        for text, x, y, color, font_size in self.texts:
            painter.setPen(QtGui.QColor(color))
            font = QtGui.QFont('Arial', font_size)
            painter.setFont(font)
            painter.drawText(x, y, text)

class OverlayUtil:
    @staticmethod
    def show_overlay(lines=None, texts=None):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        overlay = OverlayWidget(lines=lines, texts=texts)
        overlay.show()
        sys.exit(app.exec_())

if __name__ == '__main__':
    # 测试：显示一条折线和两段文字
    lines = [(100, 200, 400, 300), (400, 300, 600, 250)]
    texts = [
        ("测试文字1", 120, 180, '#FF0000', 24),
        ("测试文字2", 500, 320, '#00FF00', 18)
    ]
    OverlayUtil.show_overlay(lines=lines, texts=texts)
