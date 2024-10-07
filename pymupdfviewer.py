import pymupdf
import fitz
import sys
import pathlib
import logging
import random

from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from enum import Enum
from QtPymuPdf import OutlineModel, OutlineItem, PageNavigator, ZoomSelector, SearchModel, LinkModel, LinkItem, GoToLink, NamedLink, SearchItem, MetaDataWidget

from resources import qrc_resources

from toolbar import ToolBar

SUPPORTED_FORMART = ("png", "jpg", "jpeg", "bmp", "tiff", "pnm", "pam", "ps", "svg",
                     "pdf", "epub", "xps", "fb2", "cbz", "txt")

logger = logging.getLogger(__name__)   


class PdfView(QtWidgets.QGraphicsView):

    def __init__(self, parent=None):
        super(PdfView, self).__init__(parent)

        self._page_navigator = PageNavigator(parent)

        self.page_count: int = 0
        self.page_dlist: pymupdf.DisplayList = None

        self.zoom_factor = 1
        self.max_zoom_factor = 3
        self.min_zoom_factor = 0.5
        self.zoom_factor_step = 0.25
 
        self.prevPoint = QtCore.QPoint()
        self.addOffset = 5

        self.annotations = {}

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

        page_width = self.dlist[self.pageNavigator().currentPage()].rect.width
        page_height = self.dlist[self.pageNavigator().currentPage()].rect.height
        
        if mode == ZoomSelector.ZoomMode.FitToWidth:
            self.zoom_factor = (view_width - content_margins.left() - content_margins.right() - 20) / page_width
            self.render_page(self.pageNavigator().currentPage())
        elif mode == ZoomSelector.ZoomMode.FitInView:
            self.zoom_factor = (view_height - content_margins.bottom() - content_margins.top() -20) / page_height
            self.render_page(self.pageNavigator().currentPage())

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
        fitzpix: pymupdf.Pixmap = page_dlist.get_pixmap(alpha=0, matrix=mat)
        return fitzpix
    
    def setAnnotations(self, annotations: dict):
        self.annotations.clear()
        self.annotations.update(annotations)
    
    def render_page(self, pno=0):
        page_dlist: pymupdf.DisplayList = self.dlist[pno]

        if not page_dlist :  # create if not yet there
            fitzpage = self.fitzdoc.load_page(pno)
            self.dlist[pno] = fitzpage.get_displaylist()
            page_dlist = self.dlist[pno]

        # Remove annotations
        page = self.fitzdoc.load_page(pno)
        self.fitzdoc.xref_set_key(page.xref, "Annots", "null")
        
        add_annotations = self.annotations.get(pno)
        if add_annotations is not None:

            for quads in add_annotations:
                page.add_highlight_annot(quads)
            page_dlist = page.get_displaylist()

        fitzpix = self.create_fitzpix(page_dlist, self.zoom_factor)
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
        fitzpage = self.fitzdoc.load_page(pno)
        rotation = fitzpage.rotation + degree
        fitzpage.set_rotation(rotation)
        self.dlist[pno] = fitzpage.get_displaylist()
        self.render_page(pno)

    def next(self):
        self.pageNavigator().jump(self.pageNavigator().currentPage() + 1)

    def previous(self):
        self.pageNavigator().jump(self.pageNavigator().currentPage() - 1)

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

        self.initViewer()

    def loadDocument(self, doc: QtCore.QFile):
        if doc is not None:
            self.pdfdocument = doc
            self.fitzdoc: pymupdf.Document = pymupdf.Document(self.pdfdocument.fileName())
            self.pdfview.setDocument(self.fitzdoc)
            self.outline_model.setDocument(self.fitzdoc)
            self.search_model.setDocument(self.fitzdoc)
            # self.link_model.setDocument(self.fitzdoc)
            self.metadata_tab.setMetadata(self.fitzdoc.metadata)

    def initViewer(self):
        self.fold = False
        vbox = QtWidgets.QVBoxLayout()

        self._toolbar = ToolBar(self, icon_size=(24, 24))
        self._toolbar.setFixedHeight(36)

        self.pdfview = PdfView(self)
        self.outline_model = OutlineModel()
        self.link_model = LinkModel()
        self.search_model = SearchModel()

        # Toolbar button        
        self.search_LineEdit = QtWidgets.QLineEdit()
        self.search_LineEdit.setPlaceholderText("Find in document")
        self.search_LineEdit.setFixedWidth(180)
        self.search_LineEdit.editingFinished.connect(self.searchFor)

        self.capture_area = QtGui.QAction(QtGui.QIcon(':capture_area'), "Capture", self)
        self.capture_area.setShortcut(QtGui.QKeySequence("ctrl+alt+s"))
        # self.capture_area.triggered.connect()

        self.mark_pen = QtGui.QAction(QtGui.QIcon(':mark_pen'), "Mark text", self)
        # self.mark_pen_btn.clicked.connect(self.zoom)

        self.page_navigator = self.pdfview.pageNavigator()
        
        # Zoom
        self.action_fitwidth = QtGui.QAction(QtGui.QIcon(':expand-width-fill'), "Fit Width", self)
        self.action_fitwidth.triggered.connect(self.fitwidth)

        self.action_fitheight = QtGui.QAction(QtGui.QIcon(':expand-height-line'), "Fit Height", self)
        self.action_fitheight.triggered.connect(self.fitheight)

        # Rotate
        self.rotate_anticlockwise = QtGui.QAction(QtGui.QIcon(":anticlockwise"), "Rotate left", self)
        self.rotate_anticlockwise.setToolTip("Rotate anticlockwise")
        self.rotate_anticlockwise.triggered.connect(lambda: self.pdfview.setRotation(-90))

        self.rotate_clockwise = QtGui.QAction(QtGui.QIcon(":clockwise"), "Rotate right", self)
        self.rotate_clockwise.setToolTip("Rotate clockwise")
        self.rotate_clockwise.triggered.connect(lambda: self.pdfview.setRotation(90))

        # Collapse Left pane
        self.fold_left_pane = QtGui.QAction(QtGui.QIcon(':sidebar-fold-line'), "", self, triggered=self.onFoldLeftSidebarTriggered)

        self._toolbar.addAction(self.fold_left_pane)
        self._toolbar.addSeparator()
        self._toolbar.addWidget(self.page_navigator)
        self._toolbar.addSeparator()
        self._toolbar.addAction(self.action_fitwidth)
        self._toolbar.addAction(self.action_fitheight)
        self._toolbar.addAction(self.rotate_anticlockwise)
        self._toolbar.addAction(self.rotate_clockwise)
        self._toolbar.add_spacer()
        self._toolbar.addAction(self.capture_area)
        self._toolbar.addAction(self.mark_pen)
        self._toolbar.add_spacer()
        self._toolbar.addWidget(self.search_LineEdit)
        
        # Left Sidebar
        self.left_pane = QtWidgets.QTabWidget(self)
        self.left_pane.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)
        self.left_pane.setMovable(False)

        # Outline Tab
        self.outline_tab = QtWidgets.QTreeView(self.left_pane)
        self.outline_tab.setModel(self.outline_model)
        self.outline_tab.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.outline_tab.setHeaderHidden(True)
        self.outline_tab.selectionModel().selectionChanged.connect(self.onOutlineSelected)
        self.left_pane.addTab(self.outline_tab, "Outline")

        # Link tab
        self.link_tab = QtWidgets.QTreeView(self.left_pane)
        self.link_tab.setModel(self.link_model)
        self.link_tab.setHeaderHidden(True)
        self.link_tab.selectionModel().selectionChanged.connect(self.onLinkSelected)
        self.left_pane.addTab(self.link_tab, "Links")

        # Search Tab
        search_tab = QtWidgets.QWidget(self.left_pane)
        search_tab_layout = QtWidgets.QVBoxLayout()
        search_tab.setLayout(search_tab_layout)

        self.search_results = QtWidgets.QTreeView(self.left_pane)
        self.search_results.setModel(self.search_model)
        self.search_results.setHeaderHidden(True)
        self.search_results.setRootIsDecorated(False)
        self.search_results.selectionModel().selectionChanged.connect(self.onSearchResultSelected)

        self.search_count = QtWidgets.QLabel("Hits: ")

        search_tab_layout.addWidget(self.search_count)
        search_tab_layout.addWidget(self.search_results)
        self.left_pane.addTab(search_tab, "Search")

        # Metadata
        self.metadata_tab = MetaDataWidget(self.left_pane)
        self.left_pane.addTab(self.metadata_tab, "Metadata")

        # Splitter
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.left_pane)
        self.splitter.addWidget(self.pdfview)
        self.splitter_sizes = [100, 700]
        self.splitter.setSizes(self.splitter_sizes)

        vbox.addWidget(self._toolbar)
        vbox.addWidget(self.splitter)
        self.setLayout(vbox)
        
        # Signals
        self.page_navigator.currentPageChanged.connect(self.pdfview.render_page)
        self.page_navigator.currentLocationChanged.connect(self.pdfview.scrollTo)
        self.search_model.sigTextFound.connect(self.onSearchFound)

        self.installEventFilter(self.pdfview)

        # Collapse Left Side pane by default
        self.onFoldLeftSidebarTriggered()

    @Slot(str)
    def onSearchFound(self, count: str):
        self.search_count.setText(count)
        self.pdfview.setAnnotations(self.search_model.getSearchResults())
        self.pdfview.render_page(self.page_navigator.currentPage())
        self.search_results.resizeColumnToContents(0)

    def pdfViewSize(self) -> QtCore.QSize:
        idx = self.splitter.indexOf(self.pdfview)
        return self.splitter.widget(idx).size()

    def toolbar(self):
        return self._toolbar

    def showEvent(self, event):
        self.pdfview.scrollTo(self.pdfview.verticalScrollBar().minimum())
        super().showEvent(event)

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent):
        if object == self and event.type() == QtCore.QEvent.Type.Wheel:
            return True

        return False
    
    @Slot()
    def searchFor(self):
        self.search_model.searchFor(self.search_LineEdit.text())
    
    @Slot()
    def fitwidth(self):
        self.pdfview.setZoomMode(ZoomSelector.ZoomMode.FitToWidth)

    @Slot()
    def fitheight(self):
        self.pdfview.setZoomMode(ZoomSelector.ZoomMode.FitInView)
    
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

    @Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def onSearchResultSelected(self, selected: QtCore.QItemSelection, deseleted: QtCore.QItemSelection):
        for idx in selected.indexes():
            item: SearchItem = self.search_results.model().itemFromIndex(idx)
            page, quads, page_label = item.results()
            self.page_navigator.jump(page)

    @Slot()
    def onFoldLeftSidebarTriggered(self):
        if not self.fold:
            self.fold = True
        else:
            self.fold = False

        if self.fold:
            self.splitter_sizes = self.splitter.sizes()
            self.splitter.setSizes([0, 800])
            self.fold_left_pane.setIcon(QtGui.QIcon(':sidebar-unfold-line'))
        else:
            self.fold_left_pane.setIcon(QtGui.QIcon(':sidebar-fold-line'))
            self.splitter.setSizes(self.splitter_sizes)
