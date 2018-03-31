import time
from PyQt5 import QtGui

from PyQt5.QtCore import QObject, pyqtSignal, QRect, QPoint, Qt
from PyQt5.QtGui import QPainter, QPixmap, QImage
from PyQt5.QtWidgets import QWidget

from utils import QColor, hsv_ranged


class Communicate(QObject):

    selection_update = pyqtSignal()


class ImageWidget(QWidget):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent

        self.imageOrigin = None  # type: QImage
        self.image = None  # type: QImage

        self.selection = None  # type: QRect
        self.selection_img = None  # type: QRect
        self.coef = None

        self._communicate = Communicate()

        self.selection_update = self._communicate.selection_update

        self._init_ui()

        self.endMouse = True

        self._shift_hsv_values = [0, 0, 0]
        self.need_hsv_recalc = False
    
    def set_status(self, msg, sec=0):
        self.parent.status(msg, sec)

    @property
    def shift_hsv(self):
        return tuple(self._shift_hsv_values)

    @shift_hsv.setter
    def shift_hsv(self, value):
        if len(value) != 3:
            raise ValueError("Shift_hsv may be 3 int!")
        self._shift_hsv_values = list(value)
        self.need_hsv_recalc = True

        self._rescale()
        self.update()

    def _shift_hsv(self):
        if not self.need_hsv_recalc:
            return

        dh, ds, dv = self._shift_hsv_values

        img = self.image
        for x in range(self.image.width()):
            self.set_status("Recalc HSV {:.1f}%".format(
                x / self.image.width() * 100
            ))

            for y in range(self.image.height()):
                color = img.pixelColor(x, y)
                h, s, v, a = color.getHsv()
                color.setHsv(*hsv_ranged(h + dh, s + ds, v + dv), a)
                img.setPixelColor(x, y, color)
        self.need_hsv_recalc = False

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

    def _init_ui(self):
        self.setMinimumSize(10, 10)

    def paintEvent(self, e):
        qp = QPainter()
        qp.begin(self)
        self._draw_widget(e, qp)
        qp.end()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self._rescale()

    def _draw_widget(self, event, qp):
        qp.setBrush(QColor(0, 0, 0))
        qp.setPen(QColor(0, 0, 0))

        if self.imageOrigin is None:
            qp.drawText(event.rect(), Qt.AlignCenter, "Open image")
        else:
            qp.drawImage(0, 0, self.image)

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
        if self.imageOrigin is None:
            return

        self.set_status("Rescaling...")

        aspect = self.width() / self.height()

        aspect_image = self.imageOrigin.width() / self.imageOrigin.height()

        if aspect_image > aspect:
            self.coef = self.imageOrigin.width() / self.width()
            _image = self.imageOrigin.scaledToWidth(self.width())
        else:
            self.coef = self.imageOrigin.height() / self.height()
            _image = self.imageOrigin.scaledToHeight(self.height())

        if self.selection is not None:
            self.selection = self.from_image_rect(self.selection_img)

        self.image = _image

        self._shift_hsv()
        self.set_status("Ready")

    def set_image(self, image: QImage):
        self.imageOrigin = image
        self.selection = None
        self.coef = None
        self._rescale()
        self.update()

    def mousePressEvent(self, event):
        if self.imageOrigin is None:
            return
        if event.button() == Qt.LeftButton:
            self.selection = QRect(event.pos(), event.pos())
            self.selection_img = self.to_image_rect(self.selection)
            self.endMouse = False
            self.selection_update.emit()
        self.update()

    def mouseMoveEvent(self, event):
        if self.imageOrigin is None:
            return
        if event.buttons() == Qt.LeftButton:
            self.selection.setBottomRight(event.pos())
            self.selection_img = self.to_image_rect(self.selection)
            self.selection_update.emit()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.imageOrigin is None:
            return
        if event.button() == Qt.LeftButton:
            self.selection.setBottomRight(event.pos())
            self.selection_img = self.to_image_rect(self.selection)
            self.endMouse = True
            self.selection_update.emit()
        self.update()

    @property
    def selected(self) -> QImage:
        img = self.imageOrigin.copy(self.selection_img)

        need = 700000 / 30
        resolution = img.height() * img.width()

        if self.endMouse or resolution < need:
            return img
        else:
            coef = (resolution / need) ** 0.5
            return img.scaled(img.width() / coef, img.height() / coef)
