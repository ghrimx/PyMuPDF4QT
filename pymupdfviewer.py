import fitz
import sys
import pathlib
import logging
import random

from PyQt6.QtCore import (Qt,
                          QRectF,
                          QPointF,
                          QPoint)
from PyQt6.QtCore import pyqtSignal as pyqtSignal
from PyQt6.QtWidgets import (QApplication,
                             QWidget,
                             QGraphicsScene,
                             QGraphicsView,
                             QGraphicsPixmapItem,
                             QVBoxLayout,
                             QSplitter,
                             QTreeView,
                             QLabel,
                             QToolButton,
                             QLineEdit,
                             QToolBar,
                             QSizePolicy)
from PyQt6.QtGui import (QIcon,
                         QKeyEvent,
                         QPixmap, QShowEvent,
                         QWheelEvent,
                         QColor,
                         QCursor,
                         QShortcutEvent,
                         QPainter,
                         QImage,
                         QTransform)

from resources import qrc_resources

from viewer import PdfViewer

SUPPORTED_FORMART = ("png", "jpg", "jpeg", "bmp", "tiff", "pnm", "pam", "ps", "svg",
                     "pdf", "epub", "xps", "fb2", "cbz", "txt")

logger = logging.getLogger(__name__)


class DocView(QGraphicsView):

    sig_page_changed = pyqtSignal()

    def __init__(self, fitzdoc, current_page=0, parent=None):
        super(DocView, self).__init__(parent)
        
        self._current_page = current_page

        self.zoom_factor = 1
        self.max_zoom_factor = 3
        self.min_zoom_factor = 0.5
        self.zoom_factor_step = 0.25
        self.max_size = [1920,1080]
        self.prevPoint = QPoint()
        self.addOffset = 5

        self.fitzdoc: fitz.Document = fitzdoc
        self.page_count = len(self.fitzdoc)
        self.dlist: list[fitz.DisplayList] = [None] * self.page_count

        self.doc_scene = QGraphicsScene(self)
        self.setScene(self.doc_scene)

        self.page_pixmap_item = self.create_pixmap_item()
        self.doc_scene.addItem(self.page_pixmap_item)

        self.setBackgroundBrush(QColor(242, 242, 242))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        self.render_page(0)
       
        self.doc_scene.setSceneRect(self.page_pixmap_item.boundingRect()) 
        self.doc_scene.addRect(self.page_pixmap_item.boundingRect(), Qt.GlobalColor.red)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignHCenter)
        self.viewport().update()
    
    def showEvent(self, event: QShowEvent | None) -> None:
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

    def convert_to_QPixmap(self, fitzpix:fitz.Pixmap) -> QPixmap:
        fitzpix_bytes = fitzpix.tobytes()
        pixmap = QPixmap()
        r = pixmap.loadFromData(fitzpix_bytes)
        if not r:
            logger.error(f"Cannot load pixmap from data")
        return pixmap
    
    def create_pixmap_item(self, pixmap=None, position=None, matrix=None) -> QGraphicsPixmapItem:
        item = QGraphicsPixmapItem(pixmap)

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
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter)
        self.doc_scene.setSceneRect(self.page_pixmap_item.boundingRect()) 
        self.viewport().update()

    def next(self):
        self.current_page += 1

    def previous(self):
        self.current_page -= 1

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Left:
            self.previous()
        elif event.key() == Qt.Key.Key_Right:
            self.next()
            

    def wheelEvent(self, event: QWheelEvent) -> None:
        #Zoom : CTRL + wheel
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
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
            if event.angleDelta().y() < 0:
                self.next()
            else:
                self.previous()

    def position(self):
        point = self.mapFromGlobal(QCursor.pos())
        if not self.geometry().contains(point):
            coord = random.randint(36, 144)
            point = QPoint(coord, coord)
        else:
            if point == self.prevPoint:
                point += QPoint(self.addOffset, self.addOffset)
                self.addOffset += 5
            else:
                self.addOffset = 5
                self.prevPoint = point
        return self.mapToScene(point)


class DocViewer(QWidget):
    def __init__(self, doc, parent=None):
        super(DocViewer, self).__init__(parent)
        self.document = doc
        self.fitzdoc: fitz.Document = fitz.Document(doc)
        self.initUI()

    def initUI(self):
        vbox = QVBoxLayout()

        docview_toolbar = QToolBar()

        self.doc_view = DocView(self.fitzdoc)
        
        # self.doc_view = PdfViewer()
        # self.doc_view.loadDocument(self.document)

        toolbar_separator_1 = QWidget()
        toolbar_separator_1.setSizePolicy(QSizePolicy.Policy.Expanding,
                                        QSizePolicy.Policy.Preferred)
        
        toolbar_separator_2 = QWidget()
        toolbar_separator_2.setSizePolicy(QSizePolicy.Policy.Expanding,
                                        QSizePolicy.Policy.Preferred)
        
        self.search_in_doc = QLineEdit()
        self.search_in_doc.setPlaceholderText("Find in document")
        self.search_in_doc.setFixedWidth(180)

        self.capture_area_btn = QToolButton()
        self.capture_area_btn.setIcon(QIcon(':capture_area'))
        self.mark_pen_btn = QToolButton()
        self.mark_pen_btn.setIcon(QIcon(':mark_pen'))
        self.mark_pen_btn.clicked.connect(self.zoom)

        self.current_page = QLineEdit()
        self.current_page.setFixedWidth(40)
        self.current_page.setText(str(self.doc_view.current_page+1))
        self.current_page.returnPressed.connect(self.goto_page)
        # self.page_count = QLabel(f' of {len(self.fitzdoc)}')
        self.previous_page = QToolButton()
        # self.previous_page.clicked.connect(self.doc_view.previous)
        self.previous_page.setIcon(QIcon(':arrow-up-s-line'))
        self.next_page = QToolButton()
        # self.next_page.clicked.connect(self.doc_view.next)
        self.next_page.setIcon(QIcon(':arrow-down-s-line'))

        docview_toolbar.addWidget(self.previous_page)
        docview_toolbar.addWidget(self.next_page)
        docview_toolbar.addWidget(self.current_page )
        # docview_toolbar.addWidget(self.page_count)

        docview_toolbar.addWidget(toolbar_separator_1)
        docview_toolbar.addWidget(self.capture_area_btn)
        docview_toolbar.addWidget(self.mark_pen_btn)
        docview_toolbar.addWidget(toolbar_separator_2)
        docview_toolbar.addWidget(self.search_in_doc)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)

        splitter.addWidget(self.doc_view)


        vbox.addWidget(docview_toolbar)
        vbox.addWidget(splitter)
        self.setLayout(vbox)

   
        
    def connect_signals(self):
        pass


    def handle_sig_page_changed(self):
        self.current_page.setText(str(self.doc_view.current_page+1))

    def goto_page(self):
        self.doc_view.current_page = int(self.current_page.text())-1

    def zoom(self):
        self.doc_view.scale(1.2, 1.2)

    

def main():

    app = QApplication(sys.argv)

    # doc = DocViewer(r"C:\Users\debru\Documents\GitHub\pymupdfviewer\resources\IPCC_AR6_WGI_FullReport_small.pdf")
    doc = DocViewer(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\Sample_PDF.pdf")
    doc.showMaximized()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()




