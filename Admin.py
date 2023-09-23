import sys
import sqlite3
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QMessageBox, QWidget
from Interfaz import MainWindow

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ingreso de Administrador")
        self.setGeometry(100, 100, 372, 384)

        self.initUI()

    def initUI(self):
        self.centralwidget = QWidget(self)

        self.label = QLabel("INICIO DE SESIÓN", self.centralwidget)
        self.label.setGeometry(120, 0, 121, 31)

        self.label_2 = QLabel("BIENVENIDO AL SGBD DE LA BIBLIOTECA ESCOLAR.", self.centralwidget)
        self.label_2.setGeometry(40, 40, 301, 16)

        self.label_3 = QLabel("USUARIO", self.centralwidget)
        self.label_3.setGeometry(140, 100, 55, 16)

        self.label_4 = QLabel("CONTRASEÑA", self.centralwidget)
        self.label_4.setGeometry(120, 170, 81, 16)

        self.pushButton = QPushButton("INGRESAR", self.centralwidget)
        self.pushButton.setGeometry(120, 260, 93, 28)
        self.pushButton.clicked.connect(self.login)

        self.lineEdit = QLineEdit(self.centralwidget)
        self.lineEdit.setGeometry(110, 120, 113, 22)

        self.lineEdit_2 = QLineEdit(self.centralwidget)
        self.lineEdit_2.setGeometry(110, 200, 113, 22)
        self.lineEdit_2.setEchoMode(QLineEdit.Password)

        self.setCentralWidget(self.centralwidget)

        # Variable para mantener una referencia a la ventana principal
        self.main_window = None

    def login(self):
        username = self.lineEdit.text()
        password = self.lineEdit_2.text()

        try:
            # Conectarse a la base de datos SQLite
            conn = sqlite3.connect("biblioteca_bd.db")
            cursor = conn.cursor()

            # Verificar las credenciales en la tabla "Biblioteca_Escolar"
            self.cursor.execute("SELECT * FROM Biblioteca_Escolar WHERE Nombre_Admin = ? AND Contraseña_Admin = ?",
                           (username, password))
            user = cursor.fetchone()

            conn.close()

            if user:
                QMessageBox.information(self, "Éxito", "Inicio de sesión exitoso")

                # Oculta la ventana de inicio de sesión
                self.hide()

                # Abre la ventana principal desde interfaz.py
                self.main_window = MainWindow()
                self.main_window.show()

            else:
                QMessageBox.warning(self, "Error", "Credenciales incorrectas")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
