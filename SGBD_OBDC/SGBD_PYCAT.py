import sys
import traceback
import pyodbc
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QLineEdit, QTreeWidgetItem, QTableWidgetItem, \
    QTableWidget, QStackedWidget, QComboBox, QSpinBox, QCheckBox
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
        self.sentencias_sql = SentenciasSQL(self.conn, self.tab_DatosTabla, self.cursor)
        self.arbol.setHeaderLabel(self.dsn_name)
        self.cargar_esquemas_y_tablas()
        self.stackedWidget = QStackedWidget(self)
        self.tab_objetos.setRowCount(0)
        self.tab_objetos.setColumnCount(1)
        self.tab_DatosTabla.setRowCount(0)
        self.tab_DatosTabla.setColumnCount(1)
        self.tab_EdicionTabla.setRowCount(0)
        self.tab_EdicionTabla.setColumnCount(1)
        self.tab_objetos.setHorizontalHeaderLabels(["Nombre de la tabla"])
        self.arbol.itemClicked.connect(self.tabla_objetos_llenar)
        self.arbol.itemClicked.connect(self.mostrar_informacion_esquema)
        self.tab_objetos.itemClicked.connect(self.mostrar_informacion_tabla_seleccionada)
        self.tab_objetos.itemDoubleClicked.connect(self.cambiar_a_ventana_indice_2)
        self.btn_abrir_tabla.clicked.connect(self.abrir_tabla_seleccionada)
        self.btn_modificar_tabla.clicked.connect(self.modificar_tabla)

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
        self.tab_objetos.resizeColumnsToContents()  # Ajusta el ancho de las columnas según su contenido

    def mostrar_informacion_tabla_seleccionada(self, item):
        nombre_tabla = item.text()
        # Aquí, necesitas encontrar el esquema correspondiente a la tabla seleccionada.
        # Puedes hacerlo buscando el nombre de la tabla en el árbol y tomando el nombre del esquema padre.
        esquema_seleccionado = None
        root = self.arbol.invisibleRootItem()
        for i in range(root.childCount()):
            esquema_item = root.child(i)
            for j in range(esquema_item.childCount()):
                tabla_item = esquema_item.child(j)
                if tabla_item.text(0) == nombre_tabla:
                    esquema_seleccionado = esquema_item.text(0)
                    break
            if esquema_seleccionado:
                break

        if esquema_seleccionado:
            self.seleccionar_item_arbol(esquema_seleccionado, nombre_tabla)

            nombre_dsn = self.dsn_name
            numero_rows = self._obtener_numero_rows(esquema_seleccionado, nombre_tabla)
            comentario_tabla = self._obtener_comentario_tabla(esquema_seleccionado, nombre_tabla)

            info_text = (f'\n\nNombre de Tabla:\n\n"{nombre_tabla}"'
                         f'\n\nNombre de Conexión:\n\n"{nombre_dsn}"'
                         f'\n\nNombre de Esquema:\n\n"{esquema_seleccionado}"'
                         f'\n\nRows:\n\n"{numero_rows}"'
                         f'\n\nComentario:\n\n"{comentario_tabla}"\n\n')

            self.label_informacion.setText(info_text)

    def mostrar_informacion_esquema(self, item):
        # Verifica si el ítem seleccionado tiene un padre (es decir, si es una tabla).
        if item.parent():
            nombre_tabla = item.text(0)
            nombre_esquema = item.parent().text(0)  # Obtiene el nombre del esquema padre.
            nombre_dsn = self.dsn_name

            # Aquí, asumimos que tienes un método que pueda obtener el número de filas de una tabla.
            numero_rows = self._obtener_numero_rows(nombre_esquema, nombre_tabla)
            comentario_tabla = self._obtener_comentario_tabla(nombre_esquema, nombre_tabla)

            info_text = f'\n\nNombre de Tabla:\n\n"{nombre_tabla}"\n\nNombre de Conexión:\n\n"{nombre_dsn}"\n\nNombre de Esquema:\n\n"{nombre_esquema}"\n\nRows\n"{numero_rows}"\n\nComentario:\n\n"{comentario_tabla}"\n\n'
        else:
            nombre_esquema = item.text(0)
            nombre_dsn = self.dsn_name
            character_set = "UTF-8"  # Por ejemplo, puedes ajustar esto según tus necesidades.
            info_text = f'\n\nNombre de Esquema:\n\n"{nombre_esquema}"\n\nNombre de Conexión:\n\n"{nombre_dsn}"\n\nCharacter set:  {character_set}'

        self.label_informacion.setText(info_text)
        self.stackedWidget.setCurrentIndex(0)  # Asegúrate de que se muestra la página correcta en tu QStackedWidget.

    def seleccionar_item_arbol(self, esquema, tabla):
        root = self.arbol.invisibleRootItem()
        for i in range(root.childCount()):
            esquema_item = root.child(i)
            if esquema_item.text(0) == esquema:
                for j in range(esquema_item.childCount()):
                    tabla_item = esquema_item.child(j)
                    if tabla_item.text(0) == tabla:
                        self.arbol.setCurrentItem(tabla_item)
                        return

    def _obtener_esquema_de_tabla_seleccionada(self, tabla_seleccionada):
        root = self.arbol.invisibleRootItem()
        for i in range(root.childCount()):
            esquema_item = root.child(i)
            for j in range(esquema_item.childCount()):
                tabla_item = esquema_item.child(j)
                if tabla_item.text(0) == tabla_seleccionada:
                    return esquema_item.text(0)
        return None

    def cambiar_a_ventana_indice_2(self):
        # Cambia a la ventana con índice 2
        self.ventanas_tablas.setCurrentIndex(2)

        # Obtener el nombre de la tabla seleccionada
        tabla_seleccionada = self.tab_objetos.item(self.tab_objetos.currentRow(), 0).text()

        # Obtener el nombre del esquema de la tabla seleccionada
        nombre_del_esquema = self._obtener_esquema_de_tabla_seleccionada(tabla_seleccionada)

        # Carga los datos en tab_DatosTabla
        if nombre_del_esquema:
            self.sentencias_sql.cargar_datos_tabla(nombre_del_esquema, tabla_seleccionada)
        else:
            self.mostrar_mensaje("No se pudo encontrar el esquema para la tabla seleccionada.")

    def modificar_tabla(self):
        # Cambiar al índice 1 del QStackedWidget
        self.stackedWidget.setCurrentIndex(1)

        # Obtener el nombre de la tabla seleccionada
        if self.tab_objetos.currentRow() != -1:
            tabla_seleccionada = self.tab_objetos.item(self.tab_objetos.currentRow(), 0).text()
            # Obtener el nombre del esquema de la tabla seleccionada
            nombre_del_esquema = self._obtener_esquema_de_tabla_seleccionada(tabla_seleccionada)
            # Obtener los datos de la tabla (deberás implementar esta función)
            tabla_data = self.sentencias_sql.cargar_datos_tabla(tabla_seleccionada, nombre_del_esquema)

            # Llenar el QTableWidget tab_EdicionTabla
            self.sentencias_sql.cargar_datos_tabla(self.tab_EdicionTabla, tabla_data)

    def abrir_tabla_seleccionada(self):
        # Verifica si hay alguna fila seleccionada en tab_objetos
        if self.tab_objetos.currentRow() != -1:  # -1 significa que ninguna fila está seleccionada
            self.ventanas_tablas.setCurrentIndex(2)
            # Obtener el nombre de la tabla seleccionada
            tabla_seleccionada = self.tab_objetos.item(self.tab_objetos.currentRow(), 0).text()

            # Obtener el nombre del esquema de la tabla seleccionada
            nombre_del_esquema = self._obtener_esquema_de_tabla_seleccionada(tabla_seleccionada)

            if nombre_del_esquema:
                self.sentencias_sql.cargar_datos_tabla(nombre_del_esquema, tabla_seleccionada)
            else:
                self.mostrar_mensaje("No se pudo encontrar el esquema para la tabla seleccionada.")
        else:
            # Opcional: Mostrar un mensaje de alerta si ninguna fila está seleccionada
            self.mostrar_mensaje("Por favor, seleccione una tabla antes de presionar 'abrir tabla'.")

    def _obtener_comentario_tabla(self, esquema, tabla):
        query = f"""
            SELECT table_comment
            FROM information_schema.tables 
            WHERE table_schema = '{esquema}' AND table_name = '{tabla}';
        """
        self.cursor.execute(query)
        comentario = self.cursor.fetchone()[0]
        return comentario or "Sin comentario"

    def _obtener_numero_rows(self, esquema, tabla):
        query = f"SELECT COUNT(*) FROM {esquema}.{tabla}"
        self.cursor.execute(query)
        numero_rows = self.cursor.fetchone()[0]
        return numero_rows

    def cargar_datos_en_tabla(self, tabla_widget, datos_tabla):
        tabla_widget.setRowCount(len(datos_tabla))
        tabla_widget.setColumnCount(6)  # 6 columnas: Nombre, Tipo, Tamaño, Not Null, Llave, Comentario

        for row, atributo in enumerate(datos_tabla):
            # Insertar los datos en las celdas correspondientes
            tabla_widget.setItem(row, 0, QTableWidgetItem(atributo['nombre']))

            # Crear y configurar un QComboBox para la columna 'Tipo'
            tipo_combo = QComboBox()
            tipo_combo.addItems(["Tipo1", "Tipo2", "Tipo3"])  # Agrega tus tipos de datos comunes aquí
            tipo_index = tipo_combo.findText(atributo['tipo'])
            if tipo_index != -1:
                tipo_combo.setCurrentIndex(tipo_index)
            tabla_widget.setCellWidget(row, 1, tipo_combo)

            # Crear y configurar un QSpinBox o QDoubleSpinBox para la columna 'Tamaño'
            tamaño_spinbox = QSpinBox()  # o QDoubleSpinBox según corresponda
            tamaño_spinbox.setValue(atributo['tamaño'])
            tabla_widget.setCellWidget(row, 2, tamaño_spinbox)

            # Crear y configurar un QCheckBox para las columnas 'Not Null' y 'Llave'
            not_null_checkbox = QCheckBox()
            not_null_checkbox.setChecked(atributo['not_null'])
            tabla_widget.setCellWidget(row, 3, not_null_checkbox)

            llave_checkbox = QCheckBox()
            llave_checkbox.setChecked(atributo['llave'])
            tabla_widget.setCellWidget(row, 4, llave_checkbox)

            # Insertar los datos de comentario en la columna 'Comentario'
            tabla_widget.setItem(row, 5, QTableWidgetItem(atributo['comentario']))

        # Ajustar el tamaño de las columnas según su contenido
        tabla_widget.resizeColumnsToContents()

class SentenciasSQL:
    def __init__(self, conn, tab_DatosTabla, cursor):
        self.dbms_name = self._get_dbms_name(conn)
        self.tab_DatosTabla = tab_DatosTabla
        self.cursor = cursor

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

    def cargar_datos_tabla(self, nombre_del_esquema, tabla_seleccionada):
        try:
            # Ejecutar la consulta
            query = f"SELECT * FROM `{nombre_del_esquema}`.`{tabla_seleccionada}`"
            self.cursor.execute(query)
            datos = self.cursor.fetchall()

            # Si el objeto cursor tiene la propiedad description, podemos obtener los nombres de las columnas directamente de allí.
            columnas = [description[0] for description in self.cursor.description]

            # Establecer el número de columnas y nombres de columnas en tab_DatosTabla
            self.tab_DatosTabla.setColumnCount(len(columnas))
            self.tab_DatosTabla.setHorizontalHeaderLabels(columnas)

            # Establecer el número de filas según los datos recuperados
            self.tab_DatosTabla.setRowCount(len(datos))

            # Rellenar la tabla con los datos
            for fila_idx, fila in enumerate(datos):
                for columna_idx, valor in enumerate(fila):
                    item = QTableWidgetItem(str(valor))
                    self.tab_DatosTabla.setItem(fila_idx, columna_idx, item)

        except Exception as e:
            # En caso de error, imprimir el error para diagnóstico
            print(f"Error al cargar la tabla {tabla_seleccionada} en el esquema {nombre_del_esquema}: {e}")

class EsquemaBaseDatos:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.sentencias_sql = SentenciasSQL(self.conn, None, self.cursor)  # None ya que no usamos tab_DatosTabla aquí

    def obtener_esquemas(self):
        self.cursor.execute(self.sentencias_sql.mostrar_esquemas())
        return [row[0] for row in self.cursor.fetchall()]

class TablasEsquema:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.sentencias_sql = SentenciasSQL(self.conn, None, self.cursor)  # None ya que no usamos tab_DatosTabla aquí

    def obtener_tablas_de_esquema(self, esquema):
        query = self.sentencias_sql.mostrar_tablas_de_esquema(esquema)
        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]

class InformacionBaseDatos:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InicioSesion()
    window.show()
    sys.exit(app.exec_())
