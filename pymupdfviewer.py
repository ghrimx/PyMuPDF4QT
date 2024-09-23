import fitz
import sys
import pathlib
import logging
import random

from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from enum import Enum
from QtPymuPdf import OutlineModel, OutlineItem, PageNavigator, ZoomSelector

from resources import qrc_resources

from toolbar import ToolBar

SUPPORTED_FORMART = ("png", "jpg", "jpeg", "bmp", "tiff", "pnm", "pam", "ps", "svg",
                     "pdf", "epub", "xps", "fb2", "cbz", "txt")

logger = logging.getLogger(__name__)


class PdfView(QtWidgets.QGraphicsView):

    sig_page_changed = Signal()

    def __init__(self, fitzdoc, current_page=0, parent=None):
        super(PdfView, self).__init__(parent)
        
        self._current_page = current_page

        self.zoom_factor = 1
        self.max_zoom_factor = 3
        self.min_zoom_factor = 0.5
        self.zoom_factor_step = 0.25
        self.max_size = [1920,1080]
        self.prevPoint = QtCore.QPoint()
        self.addOffset = 5

        self.fitzdoc: fitz.Document = fitzdoc
        self.page_count = len(self.fitzdoc)
        self.dlist: list[fitz.DisplayList] = [None] * self.page_count

        self.doc_scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.doc_scene)

        self.page_pixmap_item = self.create_pixmap_item()
        self.doc_scene.addItem(self.page_pixmap_item)

        self.setBackgroundBrush(QtGui.QColor(242, 242, 242))
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)

        self.render_page(0)
       
        self.doc_scene.setSceneRect(self.page_pixmap_item.boundingRect()) 
        self.doc_scene.addRect(self.page_pixmap_item.boundingRect(), QtCore.Qt.GlobalColor.red)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignHCenter)
    
    def showEvent(self, event: QtGui.QShowEvent | None) -> None:
        # r = self.rect().toRectF()
        # self.doc_scene.setSceneRect(r)
        # self.doc_scene.addRect(r, Qt.GlobalColor.red)
        # self.fitInView(self.page_pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        return super().showEvent(event)


    @property
    def current_page(self):
        return self._current_page
    
    @current_page.setter
    def current_page(self, pno):
        if 0 <= pno < self.page_count and pno != self.current_page:
            self._current_page = pno
            self.render_page(pno)
            self.sig_page_changed.emit()

    def convert_to_QPixmap(self, fitzpix:fitz.Pixmap) -> QtGui.QPixmap:
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

    def create_page_displaylist(self, fitzpage: fitz.Page):
        return fitzpage.get_displaylist()
    
    def create_fitzpix(self, page_dlist: fitz.DisplayList, max_size, zoom_factor) -> fitz.Pixmap:
        r = page_dlist.rect

        zoom_0 = 1
        if max_size:
            zoom_0 = min(1, max_size[0] / r.width, max_size[1] / r.height)
            if zoom_0 == 1:
                zoom_0 = min(max_size[0] / r.width, max_size[1] / r.height)

        mat_0 = fitz.Matrix(zoom_0, zoom_0)
        mat = mat_0 * fitz.Matrix(zoom_factor, zoom_factor)  # zoom matrix
        fitzpix: fitz.Pixmap = page_dlist.get_pixmap(alpha=False, matrix=mat)
        return fitzpix  

    def render_page(self, pno=0):
        page_dlist: fitz.DisplayList = self.dlist[pno] 
        if not page_dlist :  # create if not yet there
            self.dlist[pno] = self.create_page_displaylist(self.fitzdoc[pno])
            page_dlist = self.dlist[pno]
        
        fitzpix = self.create_fitzpix(page_dlist, self.max_size, self.zoom_factor)
        pixmap = self.convert_to_QPixmap(fitzpix)
        # image = QImage(fitzpix.samples_ptr, fitzpix.width, fitzpix.height, QImage.Format.Format_RGB888)
        # self.page_pixmap_item.setPixmap(QPixmap.fromImage(image))
        self.page_pixmap_item.setPixmap(pixmap)

        self.centerOn(self.page_pixmap_item)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignCenter)
        self.doc_scene.setSceneRect(self.page_pixmap_item.boundingRect()) 
        self.viewport().update()

    def next(self):
        self.current_page += 1

    def previous(self):
        self.current_page -= 1

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key.Key_Left:
            self.previous()
        elif event.key() == QtCore.Qt.Key.Key_Right:
            self.next()

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
    def __init__(self, doc, parent=None):
        super(PdfViewer, self).__init__(parent)
        self.document = doc
        self.fitzdoc: fitz.Document = fitz.Document(doc)
        self.outline_model = OutlineModel(self.getToc())
        self.initUI()
        

    def initUI(self):
        vbox = QtWidgets.QVBoxLayout()

        self._toolbar = ToolBar(self, icon_size=(24, 24))

        self.doc_view = PdfView(self.fitzdoc)

        # Toolbar button        
        self.search_in_doc = QtWidgets.QLineEdit()
        self.search_in_doc.setPlaceholderText("Find in document")
        self.search_in_doc.setFixedWidth(180)

        self.capture_area_btn = QtWidgets.QToolButton()
        self.capture_area_btn.setIcon(QtGui.QIcon(':capture_area'))
        self.mark_pen_btn = QtWidgets.QToolButton()
        self.mark_pen_btn.setIcon(QtGui.QIcon(':mark_pen'))
        # self.mark_pen_btn.clicked.connect(self.zoom)

        self.page_navigator = PageNavigator(self._toolbar)
        self.page_navigator.setDocument(self.fitzdoc)

        self.zoom_selector = ZoomSelector(self._toolbar)

        self._toolbar.addWidget(self.page_navigator)
        self._toolbar.addWidget(self.zoom_selector)
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
        for column in range(self.outline_model.columnCount()):
            self.outline_tab.resizeColumnToContents(column)
        
        self.outline_tab.setHeaderHidden(True)
        self.outline_tab.hideColumn(1)
        self.outline_tab.hideColumn(2)
        self.outline_tab.hideColumn(3)
        self.outline_tab.selectionModel().selectionChanged.connect(self.onOutlineSelected)
        self.left_pane.addTab(self.outline_tab, "Outline")

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_pane)
        splitter.addWidget(self.doc_view)

        vbox.addWidget(self._toolbar)
        vbox.addWidget(splitter)
        self.setLayout(vbox)

        self.getToc()
        self.getLinks()
        
        self.page_navigator.currentPageChanged.connect(self.doc_view.render_page)
        self.page_navigator.currentLocationChanged.connect(self.doc_view.scrollTo)

        self.installEventFilter(self)

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent):
        if object == self and event.type() == QtCore.QEvent.Type.Wheel:
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                # Special tab handling
                return True
            else:
                return False

        return False

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        #Zoom : CTRL + wheel
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
            pointer_position: QtCore.QPointF = event.globalPosition()
            anchor = self.doc_view.transformationAnchor()
            self.doc_view.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            if event.angleDelta().y() > 0:
                self.doc_view.zoom_factor += self.doc_view.zoom_factor_step
            else:
                self.doc_view.zoom_factor -= self.doc_view.zoom_factor_step
            while self.doc_view.zoom_factor >= self.doc_view.max_zoom_factor:
                self.doc_view.zoom_factor -= self.doc_view.zoom_factor_step
            while self.doc_view.zoom_factor < self.doc_view.min_zoom_factor:
                self.doc_view.zoom_factor += self.doc_view.zoom_factor_step
            self.doc_view.render_page(self.doc_view.current_page)
            self.doc_view.setTransformationAnchor(anchor)
            # self.doc_view.centerOn(self.doc_view.mapFromGlobal(pointer_position))
        else:
            # Scroll Down
            if event.angleDelta().y() < 0 and self.doc_view.verticalScrollBar().sliderPosition() == self.doc_view.verticalScrollBar().maximum():
                if self.page_navigator.currentPage() < self.fitzdoc.page_count - 1:
                    location = QtCore.QPointF()
                    location.setY(self.doc_view.verticalScrollBar().minimum())
                    self.page_navigator.jump(self.page_navigator.currentPage() + 1, location)
            # Scroll Up
            elif  event.angleDelta().y() > 0 and self.doc_view.verticalScrollBar().sliderPosition() == self.doc_view.verticalScrollBar().minimum():
                if self.page_navigator.currentPage() > 0:
                    location = QtCore.QPointF()
                    location.setY(self.doc_view.verticalScrollBar().maximum())
                    self.page_navigator.jump(self.page_navigator.currentPage() - 1, location)
            else:
                self.doc_view.verticalScrollBar().setValue(self.doc_view.verticalScrollBar().sliderPosition() - event.angleDelta().y())

    @Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def onOutlineSelected(self, selected: QtCore.QItemSelection, deseleted: QtCore.QItemSelection):
        for idx in selected.indexes():
            item: OutlineItem = self.outline_tab.model().itemFromIndex(idx)
            if item.details is not None:
                self.page_navigator.jump(item.details.page)

    def getToc(self):
        toc = self.fitzdoc.get_toc(simple=False)
        return toc

    def getLinks(self):
        for page in self.fitzdoc:
            for link in page.links():
                # print(link)
                # print(page.get_textbox(link['from']))
                ...

    def showEvent(self, event):
        self.doc_view.scrollTo(self.doc_view.verticalScrollBar().minimum())
        super().showEvent(event)    

def main():

    app = QtWidgets.QApplication(sys.argv)

    # doc = PdfViewer(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\Sample PDF.pdf")
    doc = PdfViewer(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\Master File.pdf")
    doc.showMaximized()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()




