import fitz
import sys
import pathlib
import logging
import random

from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

from QtPymuPdf import OutlineModel, OutlineItem, PageNavigator

from resources import qrc_resources

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
        self.viewport().update()
    
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

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        print(f"viewport height: {self.verticalScrollBar().maximum()}")
        print(f"scroll: {self.verticalScrollBar().value()}")
        #Zoom : CTRL + wheel
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_factor += self.zoom_factor_step
            else:
                self.zoom_factor -= self.zoom_factor_step
            while self.zoom_factor >= self.max_zoom_factor:
                self.zoom_factor -= self.zoom_factor_step
            while self.zoom_factor < self.min_zoom_factor:
                self.zoom_factor += self.zoom_factor_step
            self.render_page(self.current_page)
        else:
            #Scroll-up and down
            print(event.angleDelta().y())
            if event.angleDelta().y() < 0 and self.verticalScrollBar().sliderPosition() == self.verticalScrollBar().maximum():
                self.next()
                self.verticalScrollBar().setValue(self.verticalScrollBar().minimum())
            elif  event.angleDelta().y() > 0 and self.verticalScrollBar().sliderPosition() == self.verticalScrollBar().minimum():
                self.previous()
                self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
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


class PdfViewer(QtWidgets.QWidget):
    def __init__(self, doc, parent=None):
        super(PdfViewer, self).__init__(parent)
        self.document = doc
        self.fitzdoc: fitz.Document = fitz.Document(doc)
        self.outline_model = OutlineModel(self.getToc())
        self.initUI()

    def initUI(self):
        vbox = QtWidgets.QVBoxLayout()

        docview_toolbar = QtWidgets.QToolBar()
        docview_toolbar.setIconSize(QtCore.QSize(24, 24))

        self.doc_view = PdfView(self.fitzdoc)
        
        # self.doc_view = PdfViewer()
        # self.doc_view.loadDocument(self.document)

        # Toolbar
        toolbar_separator_1 = QtWidgets.QWidget()
        toolbar_separator_1.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                          QtWidgets.QSizePolicy.Policy.Preferred)
        
        toolbar_separator_2 = QtWidgets.QWidget()
        toolbar_separator_2.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                          QtWidgets.QSizePolicy.Policy.Preferred)
        
        self.search_in_doc = QtWidgets.QLineEdit()
        self.search_in_doc.setPlaceholderText("Find in document")
        self.search_in_doc.setFixedWidth(180)

        self.capture_area_btn = QtWidgets.QToolButton()
        self.capture_area_btn.setIcon(QtGui.QIcon(':capture_area'))
        self.mark_pen_btn = QtWidgets.QToolButton()
        self.mark_pen_btn.setIcon(QtGui.QIcon(':mark_pen'))
        self.mark_pen_btn.clicked.connect(self.zoom)

        self.page_navigator = PageNavigator(docview_toolbar)
        self.page_navigator.setDocument(self.fitzdoc)

        docview_toolbar.addWidget(self.page_navigator)

        docview_toolbar.addWidget(toolbar_separator_1)
        docview_toolbar.addWidget(self.capture_area_btn)
        docview_toolbar.addWidget(self.mark_pen_btn)
        docview_toolbar.addWidget(toolbar_separator_2)
        docview_toolbar.addWidget(self.search_in_doc)
        
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

        vbox.addWidget(docview_toolbar)
        vbox.addWidget(splitter)
        self.setLayout(vbox)

        self.getToc()
        self.getLinks()
        self.page_navigator.currentPageChanged.connect(self.doc_view.render_page)



    @Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def onOutlineSelected(self, selected: QtCore.QItemSelection, deseleted: QtCore.QItemSelection):
        for idx in selected.indexes():
            item: OutlineItem = self.outline_tab.model().itemFromIndex(idx)

    def getToc(self):
        toc = self.fitzdoc.get_toc(simple=False)
        return toc

    def getLinks(self):
        for page in self.fitzdoc:
            for link in page.links():
                # print(link)
                # print(page.get_textbox(link['from']))
                ...
        
    def connect_signals(self):
        pass


    def handle_sig_page_changed(self):
        self.current_page.setText(str(self.doc_view.current_page+1))

    def goto_page(self):
        self.doc_view.current_page = int(self.current_page.text())-1

    def zoom(self):
        self.doc_view.scale(1.2, 1.2)

    

def main():

    app = QtWidgets.QApplication(sys.argv)

    # doc = DocViewer(r"C:\Users\debru\Documents\GitHub\pymupdfviewer\resources\IPCC_AR6_WGI_FullReport_small.pdf")
    doc = PdfViewer(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\Sample PDF.pdf")
    doc.showMaximized()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()




