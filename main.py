from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from models.distribution import *
from ui.interface import Ui_MainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.pushButton.clicked.connect(self.open_file)
        self.ui.pushButton_2.clicked.connect(self.open_sumo)
        self.ui.pushButton_3.clicked.connect(self.start)

    def open_file(self):
        self.excel_path = QFileDialog.getOpenFileName(self, "Seleccionar Archivo .xlsx", filter="*.xlsx")[0]
        if self.excel_path:
            self.ui.lineEdit.setText(self.excel_path)

    def open_sumo(self):
        self.netfile_path = QFileDialog.getOpenFileName(self, "Seleccionar Archivo xml", filter="*.xml")[0]
        if self.netfile_path:
            self.ui.lineEdit_2.setText(self.netfile_path)

    def start(self):
        origins, destinations = contours_finder(self.netfile_path)
        costs = costs_matrix(origins, destinations, self.netfile_path)
        G, A = read_counts(self.excel_path)
        df_od = gravity_model(G, A, costs)
        statusBar = self.ui.statusbar
        statusBar.showMessage("¡Proceso finalizado con éxito!")
        print(sum(df_od['viajes']))

def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()

if __name__ == '__main__':
    main()