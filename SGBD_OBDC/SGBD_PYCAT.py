import sys
import traceback
import pyodbc
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QLineEdit, QTreeWidgetItem
from PyQt5.uic import loadUi

class InicioSesion(QMainWindow):
    # se ocupa de todo lo relacionado al inicio de sesión
    def __init__(self):
        # Inicializar el QMainWindow
        super().__init__()

        # Cargar el diseño de la interfaz desde un archivo .ui
        loadUi("C:/Users/pedro/PycharmProjects/SGBD_CRUDpy/SGBD_OBDC/interfaz_ingreso.ui", self)

        # Configurar el campo de contraseña para ocultar el texto ingresado
        self.le_Contra.setEchoMode(QLineEdit.Password)

        # Conectar el botón de conexión a la función que inicia el proceso de conexión a la DB
        self.btn_conectar.clicked.connect(self.conectar_db)

    def conectar_db(self):
        """Intenta conectar a la base de datos usando la información proporcionada por el usuario."""

        # Obtener los datos ingresados por el usuario
        usuario = self.le_User.text()
        contrasena = self.le_Contra.text()
        dsn_name = self.le_Dns.text()
        host = self.le_Host.text()
        port = self.le_Port.text()

        # Construir la cadena de conexión basada en la información ingresada
        if usuario and contrasena:
            connection_string = f'DSN={dsn_name};UID={usuario};PWD={contrasena}'
        else:
            connection_string = f'DSN={dsn_name}'

        if host and port:
            connection_string = f"DRIVER={{ODBC Driver}};SERVER={host},{port};DATABASE=myDB;UID={usuario};PWD={contrasena}"

        # Intentar establecer la conexión
        try:
            conn = pyodbc.connect(connection_string)
            self.mostrar_mensaje("Conexión exitosa")

            # Mostrar la ventana principal si la conexión es exitosa
            self.main_window = InterfazSgbd(conn, dsn_name)
            self.main_window.show()

            # Cerrar la ventana de conexión
            self.close()
        except Exception as e:
            # Mostrar detalles del error si la conexión falla
            error_details = traceback.format_exc()
            self.mostrar_mensaje(f"Error al conectar: {str(e)}\nDetalles:\n{error_details}")

    def mostrar_mensaje(self, mensaje):
        """Muestra un mensaje emergente al usuario."""

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(mensaje)
        msg.setWindowTitle("Mensaje")
        msg.exec_()

class InterfazSgbd(QMainWindow):
    # se ocupa de todo lo relacionado a la interfaz gráfica
    def __init__(self, conn,dsn_name):
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.dsn_name = dsn_name
        super().__init__()
        loadUi("C:/Users/pedro/OneDrive/Desktop/INTERFAZ/INTERFAZ DE BASE DE DATOS0.ui", self)

        # Instanciar las clases para manejar esquemas y tablas
        self.esquema_db = EsquemaBaseDatos(self.conn)
        self.tabla_esquema = TablasEsquema(self.conn)
        self.informacion_db = InformacionBaseDatos(conn)
        self.sentencias_sql = SentenciasSQL(conn)


        # Establecer el nombre de la conexión como encabezado del TreeWidget
        self.arbol.setHeaderLabel(self.dsn_name)

        # Llenar el TreeWidget una vez iniciada la interfaz
        self.cargar_esquemas_y_tablas()

    def cargar_esquemas_y_tablas(self):
        # Limpiar el TreeWidget primero
        self.arbol.clear()

        # Obtener esquemas
        esquemas = self.esquema_db.obtener_esquemas()

        # Por cada esquema, obtener sus tablas y añadir al TreeWidget
        for esquema in esquemas:
            esquema_item = QTreeWidgetItem(self.arbol)
            esquema_item.setText(0, esquema)

            tablas = self.tabla_esquema.obtener_tablas_de_esquema(esquema)
            for tabla in tablas:
                tabla_item = QTreeWidgetItem(esquema_item)
                tabla_item.setText(0, tabla)

class EsquemaBaseDatos:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()

    def obtener_esquemas(self):
        """Obtener una lista de esquemas de la base de datos"""
        self.cursor.execute("SHOW DATABASES")
        return [row[0] for row in self.cursor.fetchall()]

class TablasEsquema:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()

    def obtener_tablas_de_esquema(self, esquema):
        """Obtener una lista de tablas para un esquema específico"""
        self.cursor.execute(f"SHOW TABLES FROM {esquema}")
        return [row[0] for row in self.cursor.fetchall()]

class InformacionBaseDatos:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()

class SentenciasSQL:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InicioSesion()
    window.show()
    sys.exit(app.exec_())
