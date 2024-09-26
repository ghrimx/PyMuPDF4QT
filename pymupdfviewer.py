import pymupdf
import sys
import pathlib
import logging
import random

from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from enum import Enum
from QtPymuPdf import OutlineModel, OutlineItem, PageNavigator, ZoomSelector, LinkFactory, LinkModel, LinkItem, GoToLink, NamedLink

from resources import qrc_resources

from toolbar import ToolBar

SUPPORTED_FORMART = ("png", "jpg", "jpeg", "bmp", "tiff", "pnm", "pam", "ps", "svg",
                     "pdf", "epub", "xps", "fb2", "cbz", "txt")

logger = logging.getLogger(__name__)


class PdfView(QtWidgets.QGraphicsView):

    sig_page_changed = Signal()

    def __init__(self, parent=None):
        super(PdfView, self).__init__(parent)

        self._page_navigator = PageNavigator(parent)
        
        self._current_page: int = 0
        self.page_count: int = 0
        self.page_dlist: pymupdf.DisplayList = None
        self.dlist: list[pymupdf.DisplayList] = [None]

        self.zoom_factor = 1
        self.max_zoom_factor = 3
        self.min_zoom_factor = 0.5
        self.zoom_factor_step = 0.25
 
        self.prevPoint = QtCore.QPoint()
        self.addOffset = 5

        self.doc_scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.doc_scene)

        self.page_pixmap_item = self.create_pixmap_item()
        self.doc_scene.addItem(self.page_pixmap_item)

        self.setBackgroundBrush(QtGui.QColor(242, 242, 242))
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)

        self.doc_scene.setSceneRect(self.page_pixmap_item.boundingRect()) 
        self.doc_scene.addRect(self.page_pixmap_item.boundingRect(), QtCore.Qt.GlobalColor.red)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignHCenter)
    
    def showEvent(self, event: QtGui.QShowEvent | None) -> None:
        # r = self.rect().toRectF()
        # self.doc_scene.setSceneRect(r)
        # self.doc_scene.addRect(r, Qt.GlobalColor.red)
        # self.fitInView(self.page_pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        return super().showEvent(event)
    
    def setDocument(self, doc: pymupdf.Document):
        self.fitzdoc: pymupdf.Document = doc
        self._page_navigator.setDocument(self.fitzdoc)
        self.page_count = len(self.fitzdoc)
        self.dlist: list[pymupdf.DisplayList] = [None] * self.page_count
        self._page_navigator.setCurrentPage(0)

    def pageNavigator(self):
        return self._page_navigator
    
    @Slot(ZoomSelector.ZoomMode)
    def setZoomMode(self, mode: ZoomSelector.ZoomMode):
        view_width = self.width()
        view_height = self.height()

        content_margins = self.contentsMargins()

        page_width = self.page_dlist.rect.width
        page_height = self.page_dlist.rect.height
        
        if mode == ZoomSelector.ZoomMode.FitToWidth:
            self.zoom_factor = (view_width - content_margins.left() - content_margins.right() - 20) / page_width
            self.render_page(self.pageNavigator().currentPage())
        elif mode == ZoomSelector.ZoomMode.FitInView:
            self.zoom_factor = (view_height - content_margins.bottom() - content_margins.top() -20) / page_height
            self.render_page(self.pageNavigator().currentPage())

    @Slot(float)
    def setZoomFactor(self, factor: float):
        ...

    @property
    def current_page(self):
        return self._current_page
    
    @current_page.setter
    def current_page(self, pno):
        if 0 <= pno < self.page_count and pno != self.current_page:
            self._current_page = pno
            self.render_page(pno)
            self.sig_page_changed.emit()

    def convert_to_QPixmap(self, fitzpix:pymupdf.Pixmap) -> QtGui.QPixmap:
        fitzpix_bytes = fitzpix.tobytes()
        pixmap = QtGui.QPixmap()
        r = pixmap.loadFromData(fitzpix_bytes)
        if not r:
            logger.error(f"Cannot load pixmap from data")
        return pixmap
    
    def create_pixmap_item(self, pixmap=None, position=None, matrix=None) -> QtWidgets.QGraphicsPixmapItem:
        item = QtWidgets.QGraphicsPixmapItem(pixmap)

        if position is not None:
            item.setPos(position)
        if matrix is not None:
            item.setTransform(matrix)

        return item

    def add_pixmap(self, pixmap):
        item = self.create_pixmap_item(pixmap)
        self.doc_scene.addItem(item)
    
    def create_fitzpix(self, page_dlist: pymupdf.DisplayList, zoom_factor=1) -> pymupdf.Pixmap:
        mat = pymupdf.Matrix(zoom_factor, zoom_factor)  # zoom matrix
        fitzpix: pymupdf.Pixmap = page_dlist.get_pixmap(alpha=False, matrix=mat)
        return fitzpix
    
    def render_page(self, pno=0):
        self.page_dlist: pymupdf.DisplayList = self.dlist[pno] 
        if not self.page_dlist :  # create if not yet there
            fitzpage = self.fitzdoc[pno]
            self.dlist[pno] = fitzpage.get_displaylist()
            self.page_dlist = self.dlist[pno]
        
        fitzpix = self.create_fitzpix(self.page_dlist, self.zoom_factor)
        pixmap = self.convert_to_QPixmap(fitzpix)
        # image = QImage(fitzpix.samples_ptr, fitzpix.width, fitzpix.height, QImage.Format.Format_RGB888)
        # self.page_pixmap_item.setPixmap(QPixmap.fromImage(image))
        self.page_pixmap_item.setPixmap(pixmap)

        self.centerOn(self.page_pixmap_item)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignCenter)
        self.doc_scene.setSceneRect(self.page_pixmap_item.boundingRect()) 
        self.viewport().update()

    def setRotation(self, degree):
        pno = self.pageNavigator().currentPage()
        fitzpage = self.fitzdoc[pno]
        rotation = fitzpage.rotation + degree
        fitzpage.set_rotation(rotation)
        self.dlist[pno] = fitzpage.get_displaylist()
        self.render_page(pno)

    def next(self):
        self.current_page += 1

    def previous(self):
        self.current_page -= 1

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key.Key_Left:
            self.previous()
        elif event.key() == QtCore.Qt.Key.Key_Right:
            self.next()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        #Zoom : CTRL + wheel
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
            anchor = self.transformationAnchor()
            self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            if event.angleDelta().y() > 0:
                self.zoom_factor += self.zoom_factor_step
            else:
                self.zoom_factor -= self.zoom_factor_step
            while self.zoom_factor >= self.max_zoom_factor:
                self.zoom_factor -= self.zoom_factor_step
            while self.zoom_factor < self.min_zoom_factor:
                self.zoom_factor += self.zoom_factor_step
            self.render_page(self.pageNavigator().currentPage())
            self.setTransformationAnchor(anchor)
            # self.doc_view.centerOn(self.doc_view.mapFromGlobal(pointer_position))
        else:
            # Scroll Down
            if event.angleDelta().y() < 0 and self.verticalScrollBar().sliderPosition() == self.verticalScrollBar().maximum():
                if self.pageNavigator().currentPage() < self.fitzdoc.page_count - 1:
                    location = QtCore.QPointF()
                    location.setY(self.verticalScrollBar().minimum())
                    self.pageNavigator().jump(self.pageNavigator().currentPage() + 1, location)
            # Scroll Up
            elif  event.angleDelta().y() > 0 and self.verticalScrollBar().sliderPosition() == self.verticalScrollBar().minimum():
                if self.pageNavigator().currentPage() > 0:
                    location = QtCore.QPointF()
                    location.setY(self.verticalScrollBar().maximum())
                    self.pageNavigator().jump(self.pageNavigator().currentPage() - 1, location)
            else:
                self.verticalScrollBar().setValue(self.verticalScrollBar().sliderPosition() - event.angleDelta().y())

    def position(self):
        point = self.mapFromGlobal(QtGui.QCursor.pos())
        if not self.geometry().contains(point):
            coord = random.randint(36, 144)
            point = QtCore.QPoint(coord, coord)
        else:
            if point == self.prevPoint:
                point += QtCore.QPoint(self.addOffset, self.addOffset)
                self.addOffset += 5
            else:
                self.addOffset = 5
                self.prevPoint = point
        return self.mapToScene(point)
    
    @Slot(QtCore.QPointF)
    def scrollTo(self, location: QtCore.QPointF | int):
        if isinstance(location, QtCore.QPointF):
            location = location.toPoint().y()
        self.verticalScrollBar().setValue(location)


class PdfViewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(PdfViewer, self).__init__(parent)

        self.initUI()

    def loadDocument(self, doc: QtCore.QFile):
        if doc is not None:
            self.pdfdocument = doc
            self.fitzdoc: pymupdf.Document = pymupdf.Document(self.pdfdocument.fileName())
            self.doc_view.setDocument(self.fitzdoc)
            self.outline_model.setDocument(self.fitzdoc)
            # self.link_model.setDocument(self.fitzdoc)

    def initUI(self):
        vbox = QtWidgets.QVBoxLayout()

        self._toolbar = ToolBar(self, icon_size=(24, 24))

        self.doc_view = PdfView(self)
        self.outline_model = OutlineModel()
        self.link_model = LinkModel()

        # Toolbar button        
        self.search_in_doc = QtWidgets.QLineEdit()
        self.search_in_doc.setPlaceholderText("Find in document")
        self.search_in_doc.setFixedWidth(180)

        self.capture_area_btn = QtWidgets.QToolButton()
        self.capture_area_btn.setIcon(QtGui.QIcon(':capture_area'))
        self.mark_pen_btn = QtWidgets.QToolButton()
        self.mark_pen_btn.setIcon(QtGui.QIcon(':mark_pen'))
        # self.mark_pen_btn.clicked.connect(self.zoom)

        self.page_navigator = self.doc_view.pageNavigator()
        
        # Zoom
        self.btn_fitwidth = QtWidgets.QToolButton(self._toolbar)
        self.btn_fitwidth.setIcon(QtGui.QIcon(':expand-width-fill'))
        self.btn_fitwidth.clicked.connect(self.fitwidth)

        self.btn_fitheight = QtWidgets.QToolButton(self._toolbar)
        self.btn_fitheight.setIcon(QtGui.QIcon(':expand-height-line'))
        self.btn_fitheight.clicked.connect(self.fitheight)

        # Rotate
        self.btn_rotate_anticlockwise = QtWidgets.QToolButton(self)
        self.btn_rotate_anticlockwise.setIcon(QtGui.QIcon(":anticlockwise"))
        self.btn_rotate_anticlockwise.setToolTip("Rotate anticlockwise")
        self.btn_rotate_anticlockwise.clicked.connect(lambda: self.doc_view.setRotation(-90))

        self.btn_rotate_clockwise = QtWidgets.QToolButton(self)
        self.btn_rotate_clockwise.setIcon(QtGui.QIcon(":clockwise"))
        self.btn_rotate_clockwise.setToolTip("Rotate clockwise")
        self.btn_rotate_clockwise.clicked.connect(lambda: self.doc_view.setRotation(90))

        self._toolbar.addWidget(self.page_navigator)
        self._toolbar.addWidget(self.btn_fitwidth)
        self._toolbar.addWidget(self.btn_fitheight)
        self._toolbar.addWidget(self.btn_rotate_anticlockwise)
        self._toolbar.addWidget(self.btn_rotate_clockwise)
        self._toolbar.add_spacer()
        self._toolbar.addWidget(self.capture_area_btn)
        self._toolbar.addWidget(self.mark_pen_btn)
        self._toolbar.add_spacer()
        self._toolbar.addWidget(self.search_in_doc)
        
        # Left Sidebar
        self.left_pane = QtWidgets.QTabWidget(self)
        self.left_pane.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)
        self.left_pane.setMovable(False)

        self.outline_tab = QtWidgets.QTreeView(self.left_pane)
        self.outline_tab.setModel(self.outline_model)
        self.outline_tab.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.outline_tab.setHeaderHidden(True)
        self.outline_tab.selectionModel().selectionChanged.connect(self.onOutlineSelected)
        self.left_pane.addTab(self.outline_tab, "Outline")

        self.link_tab = QtWidgets.QTreeView(self.left_pane)
        self.link_tab.setModel(self.link_model)
        self.link_tab.setHeaderHidden(True)
        self.link_tab.selectionModel().selectionChanged.connect(self.onLinkSelected)
        self.left_pane.addTab(self.link_tab, "Links")

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.left_pane)
        self.splitter.addWidget(self.doc_view)

        vbox.addWidget(self._toolbar)
        vbox.addWidget(self.splitter)
        self.setLayout(vbox)
        
        # Signals
        self.page_navigator.currentPageChanged.connect(self.doc_view.render_page)
        self.page_navigator.currentLocationChanged.connect(self.doc_view.scrollTo)

        self.installEventFilter(self.doc_view)

    def pdfViewSize(self) -> QtCore.QSize:
        idx = self.splitter.indexOf(self.doc_view)
        return self.splitter.widget(idx).size()

    def toolbar(self):
        return self._toolbar

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent):
        if object == self and event.type() == QtCore.QEvent.Type.Wheel:
            return True

        return False
    
    @Slot()
    def fitwidth(self):
        self.doc_view.setZoomMode(ZoomSelector.ZoomMode.FitToWidth)

    @Slot()
    def fitheight(self):
        self.doc_view.setZoomMode(ZoomSelector.ZoomMode.FitInView)
    
    @Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def onOutlineSelected(self, selected: QtCore.QItemSelection, deseleted: QtCore.QItemSelection):
        for idx in selected.indexes():
            item: OutlineItem = self.outline_tab.model().itemFromIndex(idx)
            if item.details is not None:
                self.page_navigator.jump(item.page)

    @Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def onLinkSelected(self, selected: QtCore.QItemSelection, deseleted: QtCore.QItemSelection):
        for idx in selected.indexes():
            item: LinkItem = self.link_tab.model().itemFromIndex(idx)
            link = item.link()
            if isinstance(link, (GoToLink, NamedLink)):
                self.page_navigator.jump(link.page_to)

    def showEvent(self, event):
        self.doc_view.scrollTo(self.doc_view.verticalScrollBar().minimum())
        super().showEvent(event)    

def main():

    app = QtWidgets.QApplication(sys.argv)

    # doc = QtCore.QFile(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\PSMF_BBL_PV_04-Sep-2024.pdf")
    # doc = QtCore.QFile(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\IPCC_AR6_WGI_FullReport_small.pdf")
    # doc = QtCore.QFile(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\Sample PDF.pdf")
    doc = QtCore.QFile(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\Master File.pdf")
    # doc = None
    pdf_viewer = PdfViewer()
    pdf_viewer.loadDocument(doc)
    pdf_viewer.showMaximized()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()




