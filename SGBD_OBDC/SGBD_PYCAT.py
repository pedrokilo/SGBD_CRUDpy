import sys
import traceback
import pyodbc
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QLineEdit, QTreeWidgetItem, QTableWidgetItem, \
    QTableWidget
from PyQt5.uic import loadUi

class InicioSesion(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("interfaz_ingreso.ui", self)
        self.le_Contra.setEchoMode(QLineEdit.Password)
        self.btn_conectar.clicked.connect(self.conectar_db)

    def conectar_db(self):
        usuario = self.le_User.text()
        contrasena = self.le_Contra.text()
        dsn_name = self.le_Dns.text()
        host = self.le_Host.text()
        port = self.le_Port.text()

        if host and port:
            connection_string = f"DRIVER={{ODBC Driver}};SERVER={host},{port};DATABASE=myDB;UID={usuario};PWD={contrasena}"
        elif usuario and contrasena:
            connection_string = f'DSN={dsn_name};UID={usuario};PWD={contrasena}'
        else:
            connection_string = f'DSN={dsn_name}'

        try:
            conn = pyodbc.connect(connection_string)
            self.mostrar_mensaje("Conexión exitosa")
            self.main_window = InterfazSgbd(conn,dsn_name)
            self.main_window.show()
            self.close()
        except Exception as e:
            error_details = traceback.format_exc()
            self.mostrar_mensaje(f"Error al conectar: {str(e)}\nDetalles:\n{error_details}")

    def mostrar_mensaje(self, mensaje):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(mensaje)
        msg.setWindowTitle("Mensaje")
        msg.exec_()

class InterfazSgbd(QMainWindow):
    def __init__(self, conn,dsn_name):
        super().__init__()
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.dsn_name = dsn_name
        loadUi("INTERFAZ DE BASE DE DATOS0.ui", self)
        self.tab_objetos = self.findChild(QTableWidget, 'tab_objetos')
        if not self.tab_objetos:
            raise ValueError("tab_objetos no fue encontrado en la UI")
        self.esquema_db = EsquemaBaseDatos(self.conn)
        self.tabla_esquema = TablasEsquema(self.conn)
        self.informacion_db = InformacionBaseDatos(self.conn)
        self.sentencias_sql = SentenciasSQL(self.conn)
        self.arbol.setHeaderLabel(self.dsn_name)
        self.cargar_esquemas_y_tablas()
        self.tab_objetos.setRowCount(0)
        self.tab_objetos.setColumnCount(1)
        self.tab_objetos.setHorizontalHeaderLabels(["Nombre de la tabla"])
        self.arbol.itemClicked.connect(self.tabla_objetos_llenar)
        self.arbol.itemClicked.connect(self.mostrar_informacion_esquema)

    def cargar_esquemas_y_tablas(self):
        self.arbol.clear()
        esquemas = self.esquema_db.obtener_esquemas()
        for esquema in esquemas:
            esquema_item = QTreeWidgetItem(self.arbol)
            esquema_item.setText(0, esquema)
            tablas = self.tabla_esquema.obtener_tablas_de_esquema(esquema)
            for tabla in tablas:
                tabla_item = QTreeWidgetItem(esquema_item)
                tabla_item.setText(0, tabla)

    def tabla_objetos_llenar(self, item):
        # Si el item tiene un padre, entonces es una tabla, y se toma el padre como el esquema seleccionado
        esquema_seleccionado = item.parent().text(0) if item.parent() else item.text(0)

        # Limpiamos la tabla `tab_objetos`
        self.tab_objetos.setRowCount(0)

        # Obtenemos las tablas del esquema seleccionado
        tablas = self.tabla_esquema.obtener_tablas_de_esquema(esquema_seleccionado)

        for tabla in tablas:
            row_position = self.tab_objetos.rowCount()
            self.tab_objetos.insertRow(row_position)
            self.tab_objetos.setItem(row_position, 0, QTableWidgetItem(tabla))

    def mostrar_informacion_esquema(self, item):
        # Verifica si el ítem seleccionado tiene un padre (es decir, si es una tabla).
        if item.parent():
            nombre_tabla = item.text(0)
            nombre_esquema = item.parent().text(0)  # Obtiene el nombre del esquema padre.
            nombre_dsn = self.dsn_name

            # Aquí, asumimos que tienes un método que pueda obtener el número de filas de una tabla.
            numero_rows = self._obtener_numero_rows(nombre_esquema, nombre_tabla)

            info_text = f'"{nombre_tabla}"\n\nTable\n\n"{nombre_dsn}"\n"{nombre_esquema}"\n\nRows\n"{numero_rows}"'
        else:
            nombre_esquema = item.text(0)
            nombre_dsn = self.dsn_name
            character_set = "UTF-8"  # Por ejemplo, puedes ajustar esto según tus necesidades.
            info_text = f'"{nombre_esquema}"\n\nDatabase\n\n"{nombre_dsn}"\n\nCharacter set  {character_set}'

        self.label_informacion.setText(info_text)
        self.stackedWidget.setCurrentIndex(0)  # Asegúrate de que se muestra la página correcta en tu QStackedWidget.

    def _obtener_numero_rows(self, esquema, tabla):
        query = f"SELECT COUNT(*) FROM {esquema}.{tabla}"
        self.cursor.execute(query)
        numero_rows = self.cursor.fetchone()[0]
        return numero_rows

class EsquemaBaseDatos:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.sentencias_sql = SentenciasSQL(self.conn)

    def obtener_esquemas(self):
        self.cursor.execute(self.sentencias_sql.mostrar_esquemas())
        return [row[0] for row in self.cursor.fetchall()]

class TablasEsquema:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.sentencias_sql = SentenciasSQL(self.conn)

    def obtener_tablas_de_esquema(self, esquema):
        query = self.sentencias_sql.mostrar_tablas_de_esquema(esquema)
        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]

class InformacionBaseDatos:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()

class SentenciasSQL:
    def __init__(self, conn):
        self.dbms_name = self._get_dbms_name(conn)

    def _get_dbms_name(self, conn):
        return conn.getinfo(pyodbc.SQL_DBMS_NAME)

    def mostrar_esquemas(self):
        if self.dbms_name == 'SQL Server' or self.dbms_name in ['SQL Server Native Client RDA 11.0', 'ODBC Driver 17 for SQL Server']:
            return "SELECT name FROM sys.databases"
        elif self.dbms_name in ['Microsoft Access Driver (*.mdb, *.accdb)', 'Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)', 'Microsoft Access Text Driver (*.txt, *.csv)']:
            # Suponiendo que para Access y Excel las bases de datos son archivos, podrías tener una lógica diferente.
            # Aquí solo es un ejemplo.
            return "SELECT [name] FROM [some_system_table]"
        elif self.dbms_name in ['SQLite3 ODBC Driver', 'SQLite ODBC Driver', 'SQLite ODBC (UTF-8) Driver']:
            return "SELECT name FROM sqlite_master WHERE type='table'"
        elif self.dbms_name in ['SQLite']:
            return "SELECT name FROM sqlite_master WHERE type='table'"
        elif self.dbms_name in ['MySQL ODBC 8.0 ANSI Driver', 'MySQL ODBC 8.0 Unicode Driver']:
            return "SHOW DATABASES"
        elif self.dbms_name in ['MySQL']:
            return "SHOW DATABASES"
        else:
            raise ValueError(f"No se soporta el driver: {self.dbms_name}")

    def mostrar_tablas_de_esquema(self, esquema):
        if self.dbms_name == 'SQL Server' or self.dbms_name in ['SQL Server Native Client RDA 11.0', 'ODBC Driver 17 for SQL Server']:
            return f"SELECT name FROM {esquema}.sys.tables"
        elif self.dbms_name in ['Microsoft Access Driver (*.mdb, *.accdb)', 'Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)', 'Microsoft Access Text Driver (*.txt, *.csv)']:
            # De nuevo, es solo un ejemplo.
            return f"SELECT [name] FROM {esquema}.[some_system_table]"
        elif self.dbms_name in ['SQLite3 ODBC Driver', 'SQLite ODBC Driver', 'SQLite ODBC (UTF-8) Driver']:
            return "SELECT name FROM sqlite_master WHERE type='table'"
        elif self.dbms_name in ['SQLite']:
            return "SELECT name FROM sqlite_master WHERE type='table'"
        elif self.dbms_name in ['MySQL ODBC 8.1 ANSI Driver', 'MySQL ODBC 8.1 Unicode Driver']:
            return f"SHOW TABLES FROM {esquema}"
        elif self.dbms_name in ['MySQL']:
            return f"SHOW TABLES FROM {esquema}"
        else:
            raise ValueError(f"No se soporta el driver: {self.dbms_name}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InicioSesion()
    window.show()
    sys.exit(app.exec_())
