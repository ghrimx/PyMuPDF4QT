import fitz
from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

class PageNavigator(QtWidgets.QWidget):
    currentPageChanged = Signal(int)

    def __init__(self, parent: QtWidgets.QToolBar = None):
        super().__init__()

        if parent is not None:
            icon_size = parent.iconSize()
        else:
            icon_size = QtCore.QSize(24, 24)

        hbox = QtWidgets.QHBoxLayout()
        self.setLayout(hbox)
        self.setContentsMargins(0, 0, 0, 0)

        self._current_page: int = 0
        self._current_page_label: str = ""
        
        self.currentpage_lineedit = QtWidgets.QLineEdit()
        self.currentpage_lineedit.setFixedWidth(40)
        self.pagecount_label = QtWidgets.QLabel()

        self.previous = QtWidgets.QToolButton(parent)
        self.previous.setIcon(QtGui.QIcon(':arrow-up-s-line'))
        self.previous.setIconSize(icon_size)
        self.previous.clicked.connect(self.onPreviousPage)
        self.next = QtWidgets.QToolButton(parent)
        self.next.setIcon(QtGui.QIcon(':arrow-down-s-line'))
        self.next.setIconSize(icon_size)
        self.next.clicked.connect(self.onNextPage)

        hbox.addWidget(self.previous)
        hbox.addWidget(self.next)
        hbox.addWidget(self.currentpage_lineedit)
        hbox.addWidget(self.pagecount_label)

    @Slot()
    def onNextPage(self):
        self.jump(self.currentPage() + 1)

    @Slot()
    def onPreviousPage(self):
        self.jump(self.currentPage() - 1)

    def setDocument(self, document: fitz.Document):
        self._document: fitz.Document = document
        self.pagecount_label.setText(f"of {self._document.page_count}")

        self.setCurrentPage(0)

    def updatePageLineEdit(self):
        page_label = self.currentPageLabel()

        if page_label != "":
            self.currentpage_lineedit.setText(page_label)
        else:
            self.currentpage_lineedit.setText(f"{self.currentPage() + 1}")
    
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
        page: fitz.Page = self._document[self.currentPage()]
        return page.get_label()

    def currentPage(self) -> int:
        return self._current_page
    
    def jump(self, page: int, location: QtCore.QPointF = None):
        self.setCurrentPage(page)        


class OutlineItem(QtGui.QStandardItem):
    def __init__(self, data: list):
        super().__init__()
        self.item_data = data
        self.lvl: int = data[0]
        self.title: str = data[1]
        self.page: int = data[2]
        self.dest: dict = data[3]

        self.setData(self.title, role=QtCore.Qt.ItemDataRole.DisplayRole)

class OutlineModel(QtGui.QStandardItemModel):
    def __init__(self, outline: list[list], parent=None):
        super().__init__(parent)

        self.setupModelData(outline)

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
              

