import sys
from PyQt6 import QtWidgets, QtCore
from pymupdfviewer import PdfViewer

def main():

    app = QtWidgets.QApplication(sys.argv)
    # doc = QtCore.QFile(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\IPCC_AR6_WGI_FullReport_small.pdf")
    # doc = QtCore.QFile(r"C:\Users\debru\Documents\Inspections\biosimilar\Evidence\001 PSMF_BBL_PV_04-Sep-2024 with attachements\PSMF_BBL_PV_04-Sep-2024.pdf")
    # doc = QtCore.QFile(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\Sample PDF.pdf")
    doc = QtCore.QFile(r"C:\Users\debru\Documents\GitHub\PyMuPDF4QT\resources\Master File.pdf")
    # doc = None
    pdf_viewer = PdfViewer()
    pdf_viewer.loadDocument(doc)
    pdf_viewer.showMaximized()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()