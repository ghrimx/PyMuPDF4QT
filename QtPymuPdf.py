import fitz
from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets

class PageSelector(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__()

        hbox = QtWidgets.QHBoxLayout()
        self.setLayout(hbox)
        self.setContentsMargins(0, 0, 0, 0)
        self.setM

        self.current_page: int = 0
        self.current_page_label: str = ""
        self.page_count: int = 0
        
        self.currentpage_label = QtWidgets.QLineEdit()
        self.currentpage_label.setFixedWidth(40)
        self.pagecount_label = QtWidgets.QLabel(f"of {self.page_count}")

        self.previous_page = QtWidgets.QToolButton()
        # self.previous_page.clicked.connect(self.doc_view.previous)
        self.previous_page.setIcon(QtGui.QIcon(':arrow-up-s-line'))
        self.next_page = QtWidgets.QToolButton()
        # self.next_page.clicked.connect(self.doc_view.next)
        self.next_page.setIcon(QtGui.QIcon(':arrow-down-s-line'))

        hbox.addWidget(self.previous_page)
        hbox.addWidget(self.next_page)
        hbox.addWidget(self.currentpage_label)
        hbox.addWidget(self.pagecount_label)

    def setDocument(self, document: fitz.Document):
        self._document = document
    
    def document(self):
        return self._document




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
              

