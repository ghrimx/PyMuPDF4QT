import fitz

from PyQt6.QtCore import Qt
from PyQt6 import QtGui, QtWidgets

class PdfViewer(QtWidgets.QGraphicsView):
    def __init__(self):
        super().__init__()
        self.aspectRatioMode = Qt.AspectRatioMode.KeepAspectRatio
        self.initVal()

    def initVal(self):
        self._scene = QtWidgets.QGraphicsScene()
        self._p = QtGui.QPixmap()
        self.item: QtWidgets.QGraphicsPixmapItem = None
        self._current_page: int = 0
        self.dlist: list[fitz.DisplayList] = [None]

    def nextPage(self):
        ...

    def previousPage(self):
        ...

    def jump(self, pno: int):
        ...

    def renderPage(self, pno: int, zoom_factor):
        page_display: fitz.DisplayList = self.dlist[pno]

        if page_display is None:
            page: fitz.Page = self.fitzdoc[pno]
            self.dlist[pno] = page.get_displaylist()
            page_display = self.dlist[pno]

        rect = page_display.rect
        max_size = [1920,1080]
        zoom_0 = 1
        if max_size:
            zoom_0 = min(1, self.viewport().width() / rect.width, self.viewport().height() / rect.height)
            if zoom_0 == 1:
                zoom_0 = min(self.viewport().width() / rect.width, self.viewport().height() / rect.height)

        mat_0 = fitz.Matrix(zoom_0, zoom_0)
        mat = mat_0 * fitz.Matrix(zoom_factor, zoom_factor)  # zoom matrix
        
        pix = page_display.get_pixmap(alpha=False, matrix=mat)
        pix_bytes = pix.tobytes()
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(pix_bytes)
        self.setPixmap(pixmap)

    @property
    def current_page(self):
        return self._current_page
    
    @current_page.setter
    def current_page(self, pno: int):
        if 0 <= pno < self.page_count and pno != self.current_page:
            self._current_page = pno

    def setFilename(self, filename: str):
        self._p = QtGui.QPixmap(filename)
        self._setPixmap(self._p)

    def setPixmap(self, p):
        self._setPixmap(p)

    def _setPixmap(self, p: QtGui.QPixmap):
        self._p = p
        self._scene = QtWidgets.QGraphicsScene()
        self._item = self._scene.addPixmap(self._p)
        self.setScene(self._scene)
        self._scene.setSceneRect(self._item.boundingRect()) 
        # self.fitInView(self._item, self.aspectRatioMode)

    def loadDocument(self, filename: str):
        self.fitzdoc: fitz.Document = fitz.Document(filename)
        self.page_count = len(self.fitzdoc)
        self.dlist: list[fitz.DisplayList] = [None] * self.page_count

    def setAspectRatioMode(self, mode):
        self.aspectRatioMode = mode

    # def resizeEvent(self, e):
    #     if self._item:
    #         self.fitInView(self._item, self.aspectRatioMode)
    #     return super().resizeEvent(e)
    
    def showEvent(self, event: QtGui.QShowEvent):
        self.renderPage(0, 1)

