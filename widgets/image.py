from PyQt5 import QtGui

from PyQt5.QtCore import QObject, pyqtSignal, QRect, QPoint, Qt
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QWidget
from utils import QColor


class Communicate(QObject):

    selection_update = pyqtSignal()


class ImageWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.pixmapOrigin = None  # type: QPixmap
        self.pixmap = None  # type: QPixmap

        self.selection = None  # type: QRect
        self.selection_img = None  # type: QRect
        self.coef = None

        self._communicate = Communicate()

        self.selection_update = self._communicate.selection_update

        self.initUI()

        self.endMouse = True

    def to_image_rect(self, rect: QRect):
        rect = QRect(rect)
        if rect.top() > rect.bottom():
            _top, _bottom = rect.top(), rect.bottom()
            rect.setBottom(_top), rect.setTop(_bottom)

        if rect.left() > rect.right():
            _left, _right = rect.left(), rect.right()
            rect.setLeft(_right)
            rect.setRight(_left)

        return QRect(
            self.to_image_coord(rect.topLeft()),
            self.to_image_coord(rect.bottomRight())
        )

    def to_image_coord(self, point: QPoint):
        return QPoint(point.x() * self.coef, point.y() * self.coef)

    def from_image_rect(self, rect: QRect):
        return QRect(
            self.from_image_coord(rect.topLeft()),
            self.from_image_coord(rect.bottomRight())
        )

    def from_image_coord(self, point: QPoint):
        return QPoint(point.x() / self.coef, point.y() / self.coef)

    def initUI(self):
        self.setMinimumSize(10, 10)

    def paintEvent(self, e):
        qp = QPainter()
        qp.begin(self)
        self.drawWidget(e, qp)
        qp.end()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self._rescale()

    def drawWidget(self, event, qp):
        qp.setBrush(QColor(0, 0, 0))
        qp.setPen(QColor(0, 0, 0))

        if self.pixmapOrigin is None:
            qp.drawText(event.rect(), Qt.AlignCenter, "Open image")
        else:
            qp.drawPixmap(0, 0, self.pixmap)

            self._draw_selection(qp)

    def _draw_selection(self, qp):
        if self.selection is None:
            return
        pen = QColor(0, 0, 255, 128)
        qp.setPen(pen)
        brush = QColor(0, 0, 128, 128)
        qp.setBrush(brush)
        qp.drawRect(self.selection)

    def _rescale(self):
        if self.pixmapOrigin is None:
            return

        aspect = self.width() / self.height()

        aspect_image = self.pixmapOrigin.width() / self.pixmapOrigin.height()

        if aspect_image > aspect:
            self.coef = self.pixmapOrigin.width() / self.width()
            _pixmap = self.pixmapOrigin.scaledToWidth(self.width())
        else:
            self.coef = self.pixmapOrigin.height() / self.height()
            _pixmap = self.pixmapOrigin.scaledToHeight(self.height())

        if self.selection is not None:
            self.selection = self.from_image_rect(self.selection_img)

        self.pixmap = _pixmap

    def setImage(self, pixmap: QPixmap):
        self.pixmapOrigin = pixmap
        self.selection = None
        self.coef = None
        self._rescale()
        self.update()

    def mousePressEvent(self, event):
        if self.pixmapOrigin is None:
            return
        if event.button() == Qt.LeftButton:
            self.selection = QRect(event.pos(), event.pos())
            self.selection_img = self.to_image_rect(self.selection)
            self.endMouse = False
            self.selection_update.emit()
        self.update()

    def mouseMoveEvent(self, event):
        if self.pixmapOrigin is None:
            return
        if event.buttons() == Qt.LeftButton:
            self.selection.setBottomRight(event.pos())
            self.selection_img = self.to_image_rect(self.selection)
            self.selection_update.emit()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.pixmapOrigin is None:
            return
        if event.button() == Qt.LeftButton:
            self.selection.setBottomRight(event.pos())
            self.selection_img = self.to_image_rect(self.selection)
            self.endMouse = True
            self.selection_update.emit()
        self.update()

    @property
    def selected(self) -> QPixmap:
        img = self.pixmapOrigin.copy(self.selection_img)

        need = 700000 / 30
        resolution = img.height() * img.width()

        if self.endMouse or resolution < need:
            return img
        else:
            coef = (resolution / need) ** 0.5
            return img.scaled(img.width() / coef, img.height() / coef)
