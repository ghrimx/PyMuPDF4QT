import pymupdf
from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from dataclasses import dataclass, InitVar
from enum import Enum
from math import sqrt


class ZoomSelector(QtWidgets.QComboBox):

    class ZoomMode(Enum):
        Custom = 0
        FitToWidth = 1
        FitInView = 2

    zoomModeChanged = Signal(ZoomMode)
    zoomFactorChanged = Signal(float)
    zoom_levels = ["Fit Width", "Fit Page", "12%", "25%", "33%", "50%", "66%", "75%", "100%", "125%", "150%", "200%", "400%"]
    zoom_multiplier = sqrt(2.0)

    def __init__(self, parent):
        super().__init__(parent)
        self.setEditable(True)

        for zoom_level in self.zoom_levels:
            self.addItem(zoom_level)

        self.currentTextChanged.connect(self.onCurrentTextChanged)
        self.lineEdit().editingFinished.connect(self._editingFinished)

    @Slot()
    def _editingFinished(self):
        self.onCurrentTextChanged(self.lineEdit().text())

    @Slot(float)
    def setZoomFactor(self, zoomFactor):
        zoom_level = int(100 * zoomFactor)
        self.setCurrentText(f"{zoom_level}%")

    @Slot()
    def reset(self):
        self.setCurrentIndex(8)  # 100%

    @Slot(str)
    def onCurrentTextChanged(self, text: str):
        if text == "Fit Width":
            self.zoomModeChanged.emit(ZoomSelector.ZoomMode.FitToWidth)
        elif text == "Fit Page":
            self.zoomModeChanged.emit(ZoomSelector.ZoomMode.FitInView)
        else:
            factor = 1.0
            withoutPercent = text.replace('%', '')
            zoomLevel = int(withoutPercent)
            if zoomLevel:
                factor = zoomLevel / 100.0

            self.zoomModeChanged.emit(ZoomSelector.ZoomMode.Custom)
            self.zoomFactorChanged.emit(factor)


class PageNavigator(QtWidgets.QWidget):
    currentPageChanged = Signal(int)
    currentLocationChanged = Signal(QtCore.QPointF)

    def __init__(self, parent: QtWidgets = None):
        super().__init__()
        self._current_page: int = None
        self._current_page_label: str = ""
        self._current_location: QtCore.QPointF = QtCore.QPointF()
        self._page_index:  dict[str, int] = {}

        if parent is not None:
            parent = parent.toolbar()
            icon_size = parent.iconSize()
        else:
            icon_size = QtCore.QSize(24, 24)

        hbox = QtWidgets.QHBoxLayout()
        hbox.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        self.setLayout(hbox)
        self.setContentsMargins(0, 0, 0, 0)
        hbox.setContentsMargins(5, 0, 5, 0)
        
        self.currentpage_lineedit = QtWidgets.QLineEdit()
        self.currentpage_lineedit.setFixedWidth(40)
        self.currentpage_lineedit.editingFinished.connect(self.onPageLineEditChanged)
        self.pagecount_label = QtWidgets.QLabel()
        # self.pagecount_label.setFixedWidth(40)

        self.previous_btn = QtWidgets.QToolButton(parent)
        self.previous_btn.setIcon(QtGui.QIcon(':arrow-up-s-line'))
        self.previous_btn.setIconSize(icon_size)
        self.previous_btn.clicked.connect(self.previous)

        self.next_btn = QtWidgets.QToolButton(parent)
        self.next_btn.setIcon(QtGui.QIcon(':arrow-down-s-line'))
        self.next_btn.setIconSize(icon_size)
        self.next_btn.clicked.connect(self.next)

        hbox.addWidget(self.previous_btn)
        hbox.addWidget(self.next_btn)
        hbox.addWidget(self.currentpage_lineedit)
        hbox.addWidget(self.pagecount_label)

    def setDocument(self, document: pymupdf.Document):
        self._document: pymupdf.Document = document
        self.indexPages()

    def indexPages(self):
        for page in self._document:
            self._page_index.update({page.get_label() : page.number})
    
    def pageNumberFromLabel(self, label) -> int | None:
        return self._page_index.get(label)

    def updatePageLineEdit(self):
        page_label = self.currentPageLabel()

        if page_label != "":
            self.currentpage_lineedit.setText(page_label)
        else:
            self.currentpage_lineedit.setText(f"{self.currentPage() + 1}")
        
        self.pagecount_label.setText(f"{self.currentPage() + 1} of {self._document.page_count}")
    
    def document(self):
        return self._document
    
    def setCurrentPage(self, index: int):
        old_index = self._current_page

        if 0<= index < self._document.page_count:
            self._current_page = index
            self.updatePageLineEdit()

            if old_index != self._current_page:
                self.currentPageChanged.emit(self._current_page)

    def currentPageLabel(self) -> str:
        page: pymupdf.Page = self._document[self.currentPage()]
        return page.get_label()

    def currentPage(self) -> int:
        return self._current_page
    
    def jump(self, page: int, location = QtCore.QPointF()):
        self.setCurrentPage(page)
        self._current_location = location
        self.currentLocationChanged.emit(location)  

    @Slot()
    def onPageLineEditChanged(self):
        p = self.currentpage_lineedit.text()  #  page requested by user
        pno = self.pageNumberFromLabel(p)
 
        if pno is None:
            try:
                pno = int(p) - 1
            except:
                ...
        
        if isinstance(pno, int):
            self.jump(pno)
  
    @Slot()
    def next(self):
        self.jump(self.currentPage() + 1, QtCore.QPointF())

    @Slot()
    def previous(self):
        self.jump(self.currentPage() - 1, QtCore.QPointF())

class Kind(Enum):
    LINK_NONE = 0
    LINK_GOTO = 1
    LINK_URI = 2
    LINK_LAUNCH = 3
    LINK_NAMED = 4
    LINK_GOTOR = 5

class OutlineItem(QtGui.QStandardItem):
    def __init__(self, data: list):
        super().__init__()
        self.lvl: int = data[0]
        self.title: str = data[1]
        self.page: int = int(data[2]) - 1

        try:
            self.details: dict = data[3]
        except IndexError as e:
            # data[2] is 1-based source page number
            pass

        self.setData(self.title, role=QtCore.Qt.ItemDataRole.DisplayRole)

    def getDetails(self):
        return self.details


class OutlineModel(QtGui.QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setupModelData(self, outline: list[list]):    
        parents: list[OutlineItem] = []

        prev_child = OutlineItem([0, "", 0, {}])
        parents.append(prev_child)

        for item in outline:
            child = OutlineItem(item)

            if child.lvl == 1:
                parent = self.invisibleRootItem()
            elif child.lvl > prev_child.lvl:
                parents.append(prev_child)
                parent = parents[-1]
            elif child.lvl < prev_child.lvl:
                parents.pop()
                parent = parents[-1]

            parent.appendRow(child)

            prev_child = child

    def setDocument(self, doc: pymupdf.Document):
        self._document = doc
        self.setupModelData(self.getToc())

    def getToc(self):
        toc = self._document.get_toc(simple=False)
        return toc

@dataclass
class GoToLink:
    kind: Kind = Kind.LINK_GOTO
    xref: int = 0
    hotspot: pymupdf.Rect = None
    page_to: int = 0
    to: pymupdf.Point = None
    zoom: float = 1.0
    id: str = ""
    page: InitVar[pymupdf.Page | None] = None
    page_from: int = 0
    label: str = ""

    def __post_init__(self, page: pymupdf.Page):
        self.page_from = page.number
        height_correction = self.hotspot.height * 0.1
        rect = self.hotspot + [0, height_correction, 0, -height_correction]
        label: str = page.get_textbox(rect)
        self.label = label.strip().replace("\n", " ")

@dataclass
class UriLink:
    kind: Kind = Kind.LINK_URI
    xref: int = 0
    hotspot: pymupdf.Rect = None
    uri: str = ""
    id: str = ""
    page: InitVar[pymupdf.Page | None] = None
    page_from: int = 0
    label: str = ""

    def __post_init__(self, page: pymupdf.Page):
        self.page_from = page.number
        height_correction = self.hotspot.height * 0.1
        rect = self.hotspot + [0, height_correction, 0, -height_correction]
        label: str = page.get_textbox(rect)
        self.label = label.strip().replace("\n", " ")

@dataclass
class NamedLink:
    kind: Kind = Kind.LINK_NAMED
    xref: int = 0
    hotspot: pymupdf.Rect = None
    page_to: int = 0
    to: pymupdf.Point = None
    zoom: float = 1.0
    nameddest: str = ""
    id: str = ""
    page: InitVar[pymupdf.Page | None] = None
    page_from: int = 0
    label: str = ""

    def __post_init__(self, page: pymupdf.Page):
        self.page_from = page.number
        height_correction = - self.hotspot.height * 0.1
        rect = self.hotspot + [0, height_correction, 0, -height_correction]
        label: str = page.get_textbox(rect)
        self.label = label.strip().replace("\n", " ")

class LinkFactory:
    def __init__(self):
        self.link_types = {}

        link_type: GoToLink | UriLink | NamedLink
        for link_type in [GoToLink, UriLink, NamedLink]:
            self.link_types[link_type.kind] = link_type

    def createLink(self, link: dict, page: pymupdf.Page):
        val: GoToLink | UriLink | NamedLink
        # val = self.link_types.get(link['kind'])
        for key, val in self.link_types.items():
            if link['kind'] == key.value:
                return val(*link.values(), page)
            
class LinkItem(QtGui.QStandardItem):
    def __init__(self, link: GoToLink | UriLink | NamedLink):
        super().__init__()
        self._link = link

        self.setData(self._link.label, role=QtCore.Qt.ItemDataRole.DisplayRole)
    
    def link(self):
        return self._link

class LinkModel(QtGui.QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setDocument(self, doc: pymupdf.Document):
        self._document = doc
        self.setupModelData()

    def setupModelData(self):    
        parent = self.invisibleRootItem()

        link_factory = LinkFactory()

        for page in self._document:
            for link in page.links([pymupdf.LINK_GOTO, pymupdf.LINK_NAMED]):
                link_object = link_factory.createLink(link, page)

                link_item = LinkItem(link_object)
                parent.appendRow(link_item)


class SearchItem(QtGui.QStandardItem):
    def __init__(self, result: dict):
        super().__init__()

        self.pno = result['pno']
        self.quads = result['quads']
        self.page_label = result['label']

        self.setData(f"index: {self.pno}\tlabel: {self.page_label}", role=QtCore.Qt.ItemDataRole.DisplayRole)
    
    def results(self):
        return self.pno, self.quads, self.page_label


class SearchModel(QtGui.QStandardItemModel):
    sigTextFound = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._search_results: dict[int, list] = {}

    def setDocument(self, doc: pymupdf.Document):
        self._document = doc

    def searchFor(self, text: str):
        self.clear()
        self._search_results.clear()
        
        self._found_count = 0

        if text != "":
            root_item = self.invisibleRootItem()
            page: pymupdf.Page
            for page in self._document:
                quads: list = page.search_for(text, quads=True)
                
                if len(quads) > 0:
                    self._found_count = self._found_count + len(quads)
                    page_result = {"pno" : page.number, "label": page.get_label(), "quads" : quads}
                    self._search_results.update({page.number: quads})
                    search_item = SearchItem(page_result)
                    root_item.appendRow(search_item)
        
        self.sigTextFound.emit(f"Hits: {self._found_count}")

    def foundCount(self):
        return self._found_count
    
    def getSearchResults(self):
        return self._search_results
    
class MetaDataWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._metadata = None
        self.metadata_label = QtWidgets.QLabel()
        self.metadata_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        
        vbox = QtWidgets.QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(self.metadata_label)
    
    def setMetadata(self, metadata: dict):
        self._metadata = '\n'.join(f"{key} : {val}" for key, val in metadata.items())
        self.metadata_label.setText(self._metadata.strip())
