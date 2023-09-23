import sys
import pyodbc
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidget, QAbstractItemView, QTableWidgetItem, \
    QVBoxLayout, QWidget, QLineEdit
from PyQt5.uic import loadUi
import traceback


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("interfaz_ingreso.ui", self)  # Carga el archivo de diseño
        # Ocultar el texto del QLineEdit de la contraseña
        self.le_Contra.setEchoMode(QLineEdit.Password)
        # Conectar el botón "CONECTAR" a una función
        self.btn_conectar.clicked.connect(self.conectar_db)

    def conectar_db(self):
        usuario = self.le_User.text()
        contrasena = self.le_Contra.text()
        dsn_name = self.le_Dns.text()  # Usamos el QLineEdit le_Dns para obtener el nombre del DSN
        host = self.le_Host.text()  # Obtener el host
        port = self.le_Port.text()  # Obtener el puerto

        # Si el DSN no requiere usuario y contraseña, puedes hacer una verificación y ajustar la cadena de conexión en consecuencia
        if usuario and contrasena:
            connection_string = f'DSN={dsn_name};UID={usuario};PWD={contrasena}'
        else:
            connection_string = f'DSN={dsn_name}'

        # Si se proporcionan host y puerto, ajusta la cadena de conexión (esto es solo un ejemplo, puede variar según la base de datos y el controlador que estés utilizando)
        if host and port:
            connection_string = f"DRIVER={{ODBC Driver}};SERVER={host},{port};DATABASE=myDB;UID={usuario};PWD={contrasena}"

        try:
            conn = pyodbc.connect(connection_string)
            self.mostrar_mensaje("Conexión exitosa")

            # Si la conexión es exitosa, muestra la ventana principal
            self.main_window = MainApp(conn)  # Aquí pasamos la conexión como argumento
            self.main_window.show()

            # Opcionalmente, cierra la ventana de conexión
            self.close()

        except Exception as e:
            error_details = traceback.format_exc()
            self.mostrar_mensaje(f"Error al conectar: {str(e)}\nDetalles:\n{error_details}")

    def mostrar_mensaje(self, mensaje):
        # Esta función muestra un mensaje emergente al usuario
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(mensaje)
        msg.setWindowTitle("Mensaje")
        msg.exec_()

class MainApp(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.cursor = self.conn.cursor()
        loadUi("C:/Users/pedro/PycharmProjects/SGBD_CRUDpy/interfaz_sgbd.ui", self)
        self.dbms = self.conn.getinfo(pyodbc.SQL_DBMS_NAME)
        # Crear un diccionario para almacenar las tablas y sus datos
        self.tablas = {}
        # Inicializar el diccionario de filas agregadas
        self.filas_agregadas = {}
        # Configurar la pestaña/tabla inicial
        self.cargar_tablas_desde_db()
        self.cargar_esquemas_disponibles()

        # Configurar la pestaña/tabla inicial
        self.tabWidget.currentChanged.connect(self.cambiar_tabla_actual)

        # Configurar la selección de filas completas
        for nombre_tabla in self.tablas:
            tabla_widget = self.tablas[nombre_tabla]["tabla_widget"]
            tabla_widget.setEditTriggers(QTableWidget.NoEditTriggers)
            tabla_widget.setSelectionBehavior(QTableWidget.SelectRows)
            tabla_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        self.cargar_tipos_datos()

        self.tabWidget.currentChanged.connect(self.actualizar_combobox_atributos)
        self.tabWidget.currentChanged.connect(self.actualizar_combobox_llaves)
        self.cbox_tiposdatos.currentIndexChanged.connect(self.mostrar_spinbox_si_es_necesario)

        # Variable para rastrear si la edición está habilitada
        self.modificar_habilitado = False

        self.conectar_senales()

        # Conectar la señal currentChanged del QTabWidget a la función actualizar_vista_tabla_actual
        self.tabWidget.currentChanged.connect(self.actualizar_vista_tabla_actual)

        print(f"Nombre de tabla: {nombre_tabla}")  # Imprimir el nombre de la tabla
        self.cursor.execute(f"SELECT * FROM `{nombre_tabla}`")

    def closeEvent(self, event):
        self.desconectar_bd()
        event.accept()

    def actualizar_fila_en_bd(self, nombre_tabla, fila_data, id_fila):
        # Construir la consulta SQL para actualizar la fila
        columnas = self.tablas[nombre_tabla]["columnas"]
        set_clauses = ", ".join([f"{col} = ?" for col in columnas])
        query = f"UPDATE `{nombre_tabla}` SET {set_clauses} WHERE `{columnas[0]}` = ?"

        try:
            # Ejecutar la consulta SQL
            self.cursor.execute(query, (*fila_data, id_fila))
            self.conn.commit()
        except Exception as e:
            self.mostrar_mensaje_emergente(f"Error al actualizar fila en {nombre_tabla}: {str(e)}")

    def conectar_senales(self):
        # Conexiones para los botones de gestión de registros
        self.AGREGARbtn.clicked.connect(self.gestionar_registro_crear)
        self.ELIMINARbtn.clicked.connect(self.gestionar_registro_eliminar)
        self.CANCELARbtn.clicked.connect(self.cancelar_modificacion)
        self.ACEPTARbtn.clicked.connect(self.aceptar_modificacion)
        self.MODIFICARbtn.clicked.connect(self.habilitar_modificacion)

        # Conexiones para los botones de gestión de esquemas y tablas
        self.btn_CrearEsque.clicked.connect(self.crear_esquema)
        self.btn_CargarEsque.clicked.connect(self.cargar_esquema)
        self.btn_CrearTabla.clicked.connect(self.crear_tabla)
        self.btn_BorrarTabla.clicked.connect(self.borrar_tabla)

        # Conexiones para los botones de gestión de atributos
        self.btn_CrearAtri.clicked.connect(self.crear_atributo)
        self.btn_BorrarAtri.clicked.connect(self.borrar_atributo)

        # Conexiones para el cambio de pestaña/tabla
        self.tabWidget.currentChanged.connect(self.cambiar_tabla_actual)
        self.tabWidget.currentChanged.connect(self.actualizar_vista_tabla_actual)

    def desconectar_bd(self):
        # Solo necesitas hacer commit y cerrar la conexión
        if hasattr(self, 'conn') and self.conn is not None:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    def cargar_tablas_desde_db(self):

        # Suponiendo que tienes una variable de instancia que almacena el DBMS actual
        dbms = self.dbms

        # Determinar la consulta adecuada según el DBMS
        if dbms == 'SQL Server' or dbms == 'SQL Server (Old)':
            query = "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE'"
        elif dbms == 'Microsoft Access':
            query = "SELECT name FROM MSysObjects WHERE type=1 AND flags=0"
        elif dbms == 'SQL Server Native Client RDA':
            # Suponiendo que es similar a SQL Server
            query = "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE'"
        elif dbms in ['SQLite3', 'SQLite', 'SQLite UTF-8']:
            query = "SELECT name FROM sqlite_master WHERE type='table'"
        elif dbms == 'MySQL':
            query = "SHOW TABLES"
        else:
            # Consulta genérica como fallback
            query = "SELECT table_name FROM information_schema.tables"

        if query:
            self.cursor.execute(query)
            tablas = self.cursor.fetchall()

            while self.tabWidget.count() > 0:
                self.tabWidget.removeTab(0)

            for tabla in tablas:
                nombre_tabla = tabla[0]
                self.agregar_tabla(nombre_tabla)
        else:
            print(f"No se pudo determinar una consulta para el DBMS: {dbms}")

    # Forzar una actualización de la pestaña/tabla actual
        self.tabWidget.currentWidget().repaint()

    def obtener_llaves_primarias(self, nombre_tabla):
        """Obtiene las llaves primarias de una tabla."""
        dbms = self.dbms
        if dbms == 'SQL Server' or dbms == 'SQL Server (Old)':
            query = f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                WHERE TABLE_NAME = '{nombre_tabla}' AND CONSTRAINT_SCHEMA = 'dbo';
            """
        elif dbms == 'Microsoft Access':
            # Para Microsoft Access, obtener las llaves primarias puede ser más complicado.
            # Esta consulta es una suposición y puede que necesites ajustarla.
            # Nota: Esta consulta podría no ser precisa para obtener llaves primarias en Access.
            query = f"SELECT name FROM MSysObjects WHERE type=1 AND flags=0 AND name LIKE '{nombre_tabla}%'"
        elif dbms == 'SQL Server Native Client RDA':
            # Suponiendo que es similar a SQL Server
            query = f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                WHERE TABLE_NAME = '{nombre_tabla}';
            """
        elif dbms in ['SQLite3', 'SQLite', 'SQLite UTF-8']:
            query = f"PRAGMA table_info({nombre_tabla})"
        elif dbms == 'MySQL':
            query = f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                WHERE TABLE_NAME = '{nombre_tabla}' AND CONSTRAINT_NAME = 'PRIMARY';
            """
        else:
            # Consulta genérica como fallback
            query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nombre_tabla}'"

        self.cursor.execute(query)
        resultados = self.cursor.fetchall()

        if dbms in ['SQLite3', 'SQLite', 'SQLite UTF-8']:
            # En SQLite, la consulta PRAGMA table_info devuelve una lista de columnas.
            # La columna 'pk' indica si es una llave primaria (1 si es llave primaria, 0 si no lo es).
            llaves = [columna[1] for columna in resultados if columna[5] == 1]
        else:
            llaves = [resultado[0] for resultado in resultados]

        return llaves

    def actualizar_combobox_llaves(self, index):
        nombre_tabla_actual = self.tabWidget.tabText(index)
        todas_las_tablas = [self.tabWidget.tabText(i) for i in range(self.tabWidget.count())]

        # Excluir la tabla actual de la lista de todas las tablas
        otras_tablas = [tabla for tabla in todas_las_tablas if tabla != nombre_tabla_actual]

        # Limpiar el combobox antes de llenarlo
        self.comboBox_TablasLlaves.clear()

        # Cargar las llaves primarias de las otras tablas
        for tabla in otras_tablas:
            llaves = self.obtener_llaves_primarias(tabla)
            for llave in llaves:
                self.comboBox_TablasLlaves.addItem(f"{tabla}.{llave}")

    def cargar_llaves_en_combobox(self, nombre_tabla, tabla_a_excluir=None):
        """Carga las llaves primarias de una tabla en el QComboBox."""
        print("cargar_llaves_en_combobox se está ejecutando")  # Añade esta línea
        llaves = self.obtener_llaves_primarias(nombre_tabla)

        # Si la tabla actual es la misma que la tabla a excluir, no agregues sus llaves al combobox
        if nombre_tabla != tabla_a_excluir:
            self.comboBox_TablasLlaves.addItems(llaves)

    def cargar_atributos_en_combobox(self, nombre_tabla):
        """Carga los atributos de una tabla en el QComboBox."""
        print("cargar_atributos_en_combobox se está ejecutando")  # Añade esta línea
        # Suponiendo que tienes una función que devuelve los nombres de los atributos de una tabla
        atributos = self.obtener_atributos_de_tabla(nombre_tabla)
        self.cbox_atributo.clear()
        self.cbox_atributo.addItems(atributos)

    def actualizar_combobox_atributos(self, index):
        nombre_tabla_actual = self.tabWidget.tabText(index)
        self.cargar_atributos_en_combobox(nombre_tabla_actual)

    def obtener_atributos_de_tabla(self, nombre_tabla):
        dbms = self.dbms
        if dbms == 'SQL Server' or dbms == 'SQL Server (Old)':
            query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nombre_tabla}'"
        elif dbms == 'Microsoft Access':
            # Para Microsoft Access, obtener los atributos puede ser un poco más complicado.
            # Esta consulta es una suposición y puede que necesites ajustarla.
            query = f"SELECT name FROM MSysObjects WHERE type=1 AND flags=0 AND name LIKE '{nombre_tabla}%'"
        elif dbms == 'SQL Server Native Client RDA':
            # Suponiendo que es similar a SQL Server
            query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nombre_tabla}'"
        elif dbms in ['SQLite3', 'SQLite', 'SQLite UTF-8']:
            query = f"PRAGMA table_info({nombre_tabla})"
        elif dbms == 'MySQL':
            query = f"SHOW COLUMNS FROM `{nombre_tabla}`"
        else:
            # Consulta genérica como fallback
            query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nombre_tabla}'"

        self.cursor.execute(query)
        columnas = self.cursor.fetchall()

        if dbms in ['SQLite3', 'SQLite', 'SQLite UTF-8']:
            return [columna[1] for columna in columnas]
        elif dbms == 'MySQL':
            return [columna[0] for columna in columnas]
        else:
            return [columna[0] for columna in columnas]

        print(f"Consulta ejecutada: {query}")  # Imprimir la consulta
        print(f"Resultados: {columnas}")  # Imprimir los resultados

    def cancelar_modificacion(self):
        # Esta función se llama cuando se hace clic en el botón "CANCELARbtn"
        if self.modificar_habilitado:
            self.mostrar_mensaje_emergente("La acción de modificar ha sido desactivada")
            self.modificar_habilitado = False

            # Eliminar las filas que se agregaron durante la modificación
            if self.tabWidget.currentWidget() in self.filas_agregadas:
                tabla_widget = self.tabWidget.currentWidget()
                filas_a_eliminar = self.filas_agregadas[self.tabWidget.currentWidget()]
                for fila in filas_a_eliminar:
                    tabla_widget.removeRow(fila)
                del self.filas_agregadas[self.tabWidget.currentWidget()]

        else:
            self.mostrar_mensaje_emergente("La acción de modificar no esta activada")

    def actualizar_vista_tabla_actual(self, index):
        # Obtener el nombre de la tabla actual basado en el índice de la pestaña
        nombre_tabla_actual = self.tabWidget.tabText(index)

        # Actualizar la vista de la tabla (esto es solo un ejemplo, puedes agregar más funcionalidad)
        self.mostrar_datos_tabla(nombre_tabla_actual)

        # Si necesitas más funcionalidad, agrégala aquí

    def aceptar_modificacion(self):
        if self.modificar_habilitado:
            index = self.tabWidget.currentIndex()
            nombre_tabla_actual = self.tabWidget.tabText(index)

            if nombre_tabla_actual:
                tabla_info = self.tablas[nombre_tabla_actual]
                tabla_widget = tabla_info["tabla_widget"]

                for fila_idx in range(tabla_widget.rowCount()):
                    fila_data = []
                    for columna_idx in range(tabla_widget.columnCount()):
                        item = tabla_widget.item(fila_idx, columna_idx)
                        fila_data.append(item.text())

                    # Comprobando si la fila es nueva o es una fila existente
                    if fila_idx < len(tabla_info["datos"]):
                        # Fila existente, actualizamos
                        id_fila = tabla_info["datos"][fila_idx][0]
                        self.actualizar_fila_en_bd(nombre_tabla_actual, fila_data, id_fila)
                    else:
                        # Nueva fila, insertamos
                        self.insertar_fila_en_bd(nombre_tabla_actual, fila_data)

                self.desactivar_edicion_celdas()

                mensaje = f"Cambios aplicados en la tabla {nombre_tabla_actual}"
                self.mostrar_mensaje_emergente(mensaje)
                print(mensaje)

                self.modificar_habilitado = False
                self.cargar_tablas_desde_db()
        else:
            self.mostrar_mensaje_emergente("La acción de modificar no esta activada")

    def habilitar_modificacion(self):
        # Esta función se llama cuando se hace clic en el botón "MODIFICARbtn"
        self.modificar_habilitado = True
        self.mostrar_mensaje_emergente("La acción de modificar ha sido activada")

        # Obtener la pestaña actual
        tabla_widget = self.tabWidget.currentWidget()

        # Verificar que sea un QWidget y contenga una QTableWidget
        if isinstance(tabla_widget, QWidget):
            tabla = tabla_widget.findChild(QTableWidget)

            # Verificar que se haya encontrado la QTableWidget
            if tabla is not None and isinstance(tabla, QTableWidget):
                # Habilitar la edición de celdas en la tabla actual
                tabla.setEditTriggers(QTableWidget.DoubleClicked)
                for fila_idx in range(tabla.rowCount()):
                    for columna_idx in range(tabla.columnCount()):
                        item = tabla.item(fila_idx, columna_idx)
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
            else:
                print("No se encontró la QTableWidget en la pestaña actual.")
        else:
            print("La pestaña actual no es un QWidget.")

    def crear_tabla(self):
            nombre_tabla = self.le_NTabla.text().strip()  # Obtener el nombre de la tabla
            if not nombre_tabla:
                self.mostrar_mensaje_emergente("Por favor, ingrese un nombre para la tabla.")
                return

            # Aquí, puedes construir tu consulta para crear la tabla. Por simplicidad, solo crearé una tabla con una columna ID.
            consulta = f"CREATE TABLE `{nombre_tabla}` (ID INT PRIMARY KEY)"

            try:
                self.cursor.execute(consulta)
                self.conn.commit()
                self.mostrar_mensaje_emergente("Tabla creada con éxito.")
            except Exception as e:
                self.mostrar_mensaje_emergente(f"Error al crear la tabla: {str(e)}")

    def borrar_tabla(self):
        tabla_seleccionada = self.tabWidget.tabText(self.tabWidget.currentIndex())
        try:
            self.cursor.execute(f"DROP TABLE `{tabla_seleccionada}`")
            self.conn.commit()
            self.mostrar_mensaje_emergente(f"Tabla {tabla_seleccionada} eliminada con éxito.")
        except Exception as e:
            self.mostrar_mensaje_emergente(f"Error al eliminar la tabla: {str(e)}")

    def mostrar_spinbox_si_es_necesario(self, index):
        tipo_dato = self.cbox_tiposdatos.itemText(index)
        if tipo_dato in ["TINYINT", "SMALLINT", "MEDIUMINT", "INT", "INTEGER", "BIGINT", "CHAR", "VARCHAR"]:
            self.spinBox_atributo.show()
        else:
            self.spinBox_atributo.hide()

    def cargar_tipos_datos(self):
        tipos_datos = [
            "TINYINT", "SMALLINT", "MEDIUMINT", "INT", "INTEGER", "BIGINT",
            "REAL", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC",
            "DATE", "TIME", "TIMESTAMP", "DATETIME",
            "CHAR", "VARCHAR", "TINYBLOB", "BLOB", "MEDIUMBLOB", "LONGBLOB",
            "TINYTEXT", "TEXT", "MEDIUMTEXT", "LONGTEXT", "ENUM", "SET", "spatial_type"
        ]
        self.cbox_tiposdatos.addItems(tipos_datos)

    def crear_atributo(self):
        nombre_tabla_actual = self.tabWidget.tabText(self.tabWidget.currentIndex()).strip()
        nombre_atributo = self.le_NTupla.text().strip()
        tipo_dato = self.cbox_tiposdatos.currentText().strip()

        # Considerar los detalles adicionales según el tipo de dato seleccionado
        if tipo_dato in ["TINYINT", "SMALLINT", "MEDIUMINT", "INT", "INTEGER", "BIGINT", "CHAR", "VARCHAR"]:
            longitud = self.spinBox_atributo.value()
            tipo_dato += f"({longitud})"
        elif tipo_dato in ["REAL", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC"]:
            longitud = self.spinBox_atributo.value()
            decimales = self.decimales_input.text().strip()
            tipo_dato += f"({longitud},{decimales})"
        elif tipo_dato == "ENUM" or tipo_dato == "SET":
            valores = self.valores_input.text().strip()
            tipo_dato += f"({valores})"

        consulta = f"ALTER TABLE `{nombre_tabla_actual}` ADD {nombre_atributo} {tipo_dato}"

        # Verificar si el radio button de llave primaria está seleccionado
        if self.radioButton_primario.isChecked():
            consulta += f", ADD PRIMARY KEY ({nombre_atributo})"
        # Si deseas manejar el radioButton_noaplica, puedes agregar una condición adicional aquí, aunque no parece necesario
        # ya que si no es una llave primaria simplemente no haces nada adicional.

        try:
            self.cursor.execute(consulta)
            self.conn.commit()
            self.mostrar_mensaje_emergente("Atributo añadido con éxito.")
        except Exception as e:
            self.mostrar_mensaje_emergente(f"Error al añadir el atributo: {str(e)}")

    def cargar_esquemas_disponibles(self):
        # Suponiendo que tienes una variable de instancia que almacena el DBMS actual
        dbms = self.dbms

        # Determinar la consulta adecuada según el DBMS
        if dbms == 'SQL Server' or dbms == 'SQL Server (Old)':
            query = "SELECT schema_name FROM information_schema.schemata"
        elif dbms == 'MySQL':
            query = "SHOW SCHEMAS"
        else:
            # Consulta genérica como fallback
            query = "SELECT schema_name FROM information_schema.schemata"

        if query:
            self.cursor.execute(query)
            esquemas = self.cursor.fetchall()

            # Limpiar el combobox
            self.cbox_Esque.clear()

            for esquema in esquemas:
                self.cbox_Esque.addItem(esquema[0])
        else:
            print(f"No se pudo determinar una consulta para el DBMS: {dbms}")

    def crear_esquema(self):
        esquema = self.nombre_esqueCrea.text()
        try:
            self.cursor.execute(f"CREATE SCHEMA `{esquema}`")
            self.conn.commit()
            self.cbox_Esque.addItem(esquema)  # Añadir el nuevo esquema al combobox
            self.mostrar_mensaje_emergente(f"Esquema {esquema} creado con éxito.")
        except Exception as e:
            self.mostrar_mensaje_emergente(f"Error al crear el esquema: {str(e)}")

    def cargar_esquema(self):
            esquema_seleccionado = self.cbox_Esque.currentText()

            if not esquema_seleccionado:
                self.mostrar_mensaje_emergente("Por favor, seleccione un esquema.")
                return

            # Suponiendo que tienes una variable de instancia que almacena el DBMS actual
            dbms = self.dbms

            # Determinar la consulta adecuada según el DBMS
            if dbms == 'SQL Server' or dbms == 'SQL Server (Old)':
                query = f"SELECT table_name FROM information_schema.tables WHERE table_schema='{esquema_seleccionado}' AND table_type='BASE TABLE'"
            elif dbms == 'MySQL':
                query = f"SHOW TABLES FROM `{esquema_seleccionado}`"
            else:
                # Consulta genérica como fallback
                query = f"SELECT table_name FROM information_schema.tables WHERE table_schema='{esquema_seleccionado}'"

            if query:
                self.cursor.execute(query)
                tablas = self.cursor.fetchall()

                # Limpiar las pestañas actuales
                while self.tabWidget.count() > 0:
                    self.tabWidget.removeTab(0)

                for tabla in tablas:
                    nombre_tabla = tabla[0]
                    self.agregar_tabla(nombre_tabla)
            else:
                print(f"No se pudo determinar una consulta para el DBMS: {dbms}")

            # Forzar una actualización de la pestaña/tabla actual
            self.tabWidget.currentWidget().repaint()

    def borrar_atributo(self):
        # 1. Obtener el nombre de la tabla actualmente seleccionada
        nombre_tabla_actual = self.tabWidget.tabText(self.tabWidget.currentIndex()).strip()

        # 2. Obtener el nombre del atributo que el usuario desea eliminar desde el combobox `cbox_atributo`
        nombre_atributo = self.cbox_atributo.currentText().strip()

        if not nombre_tabla_actual or not nombre_atributo:
            self.mostrar_mensaje_emergente(
                "Por favor, asegúrese de que hay una tabla seleccionada y de que ha seleccionado el atributo a eliminar.")
            return

        # 3. Construir una consulta SQL para eliminar ese atributo de la tabla seleccionada
        consulta = f"ALTER TABLE `{nombre_tabla_actual}` DROP COLUMN {nombre_atributo}"

        try:
            # 4. Ejecutar la consulta SQL
            self.cursor.execute(consulta)
            self.conn.commit()
            self.mostrar_mensaje_emergente("Atributo eliminado con éxito.")

            # 5. Actualizar el combobox `cbox_atributo` para reflejar los cambios
            self.cargar_atributos_en_combobox(nombre_tabla_actual)
        except Exception as e:
            self.mostrar_mensaje_emergente(f"Error al eliminar el atributo: {str(e)}")

    def desactivar_edicion_celdas(self):
        # Obtener la pestaña actual
        tabla_widget = self.tabWidget.currentWidget()

        # Verificar que sea un QWidget y contenga una QTableWidget
        if isinstance(tabla_widget, QWidget):
            tabla = tabla_widget.findChild(QTableWidget)

            # Verificar que se haya encontrado la QTableWidget
            if tabla is not None and isinstance(tabla, QTableWidget):
                # Deshabilitar la edición de celdas en la tabla actual
                tabla.setEditTriggers(QTableWidget.NoEditTriggers)
                for fila_idx in range(tabla.rowCount()):
                    for columna_idx in range(tabla.columnCount()):
                        item = tabla.item(fila_idx, columna_idx)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            else:
                print("No se encontró la QTableWidget en la pestaña actual.")
        else:
            print("La pestaña actual no es un QWidget.")

    def agregar_tabla(self, nombre_tabla):
        nueva_tab = QWidget()
        self.tabWidget.addTab(nueva_tab, nombre_tabla)

        layout = QVBoxLayout()
        nueva_tab.setLayout(layout)

        tabla_widget = QTableWidget()
        layout.addWidget(tabla_widget)

        # Configurar la selección de filas completas
        tabla_widget.setSelectionBehavior(QTableWidget.SelectRows)
        tabla_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        # Obtener los nombres de las columnas de la tabla desde la base de datos y asignarlos a 'columnas'
        cursor = self.cursor

        # Suponiendo que tienes una variable de instancia que almacena el DBMS actual
        dbms = self.dbms

        # Consulta para obtener las llaves primarias
        if dbms == 'SQL Server' or dbms == 'SQL Server (Old)':
            query_pk = f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                WHERE TABLE_NAME = '{nombre_tabla}' AND CONSTRAINT_SCHEMA = 'dbo';
            """
        elif dbms in ['SQLite3', 'SQLite', 'SQLite UTF-8']:
            query_pk = f"PRAGMA table_info({nombre_tabla})"
        elif dbms == 'MySQL':
            query_pk = f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                WHERE TABLE_NAME = '{nombre_tabla}' AND CONSTRAINT_NAME = 'PRIMARY';
            """
        else:
            query_pk = None

        primary_keys = []
        if query_pk:
            cursor.execute(query_pk)
            primary_keys_data = cursor.fetchall()
            if dbms in ['SQLite3', 'SQLite', 'SQLite UTF-8']:
                primary_keys = [row[1] for row in primary_keys_data if row[5] == 1]
            else:
                primary_keys = [row[0] for row in primary_keys_data]

        # Determinar la consulta adecuada según el DBMS
        if dbms == 'SQL Server' or dbms == 'SQL Server (Old)':
            query = f"""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{nombre_tabla}' AND TABLE_SCHEMA = 'dbo';
            """
        elif dbms == 'Microsoft Access':
            # Para Microsoft Access, obtener el tipo de dato puede ser más complicado.
            # Esta consulta es una suposición y puede que necesites ajustarla.
            query = f"SELECT name, type FROM MSysObjects WHERE type=1 AND flags=0 AND name LIKE '{nombre_tabla}%'"
        elif dbms == 'SQL Server Native Client RDA':
            query = f"""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{nombre_tabla}';
            """
        elif dbms in ['SQLite3', 'SQLite', 'SQLite UTF-8']:
            query = f"PRAGMA table_info({nombre_tabla})"
        elif dbms == 'MySQL':
            query = f"""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{nombre_tabla}';
            """
        else:
            # Consulta genérica como fallback
            query = f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{nombre_tabla}'"

        try:
            cursor.execute(query)
            columnas = cursor.fetchall()

            if dbms in ['SQLite3', 'SQLite', 'SQLite UTF-8']:
                nombres_columnas = [f"{columna[1]} ({columna[2]}){' [PK]' if columna[1] in primary_keys else ''}" for
                                    columna in columnas]
            else:
                nombres_columnas = [f"{columna[0]} ({columna[1]}){' [PK]' if columna[0] in primary_keys else ''}" for
                                    columna in columnas]

            self.tablas[nombre_tabla] = {
                "tabla_widget": tabla_widget,
                "datos": [],
                "columnas": nombres_columnas
            }
        except Exception as e:
            print(f"No se pudo determinar una consulta para el DBMS: {dbms}. Error: {str(e)}")

    def mostrar_datos_tabla(self, nombre_tabla):
        cursor = self.cursor
        self.cursor.execute(f"SELECT * FROM `{nombre_tabla}`")
        datos = cursor.fetchall()

        tabla_info = self.tablas[nombre_tabla]
        tabla_widget = tabla_info["tabla_widget"]
        tabla_widget.setColumnCount(len(tabla_info["columnas"]))
        tabla_widget.setHorizontalHeaderLabels(tabla_info["columnas"])

        tabla_info["datos"] = datos

        tabla_widget.setRowCount(len(datos))

        for fila_idx, fila in enumerate(datos):
            for columna_idx, valor in enumerate(fila):
                item = QTableWidgetItem(str(valor))
                tabla_widget.setItem(fila_idx, columna_idx, item)

    def cambiar_tabla_actual(self, index):
        nombre_tabla_actual = self.tabWidget.tabText(index)
        self.mostrar_datos_tabla(nombre_tabla_actual)

    def gestionar_registro_crear(self):
        if self.modificar_habilitado:
            index = self.tabWidget.currentIndex()
            nombre_tabla_actual = self.tabWidget.tabText(index)

            if nombre_tabla_actual:
                tabla_info = self.tablas[nombre_tabla_actual]
                tabla_widget = tabla_info["tabla_widget"]

                num_columnas = tabla_widget.columnCount()
                nueva_fila = ["" for _ in range(num_columnas)]

                fila_actual = tabla_widget.rowCount()
                tabla_widget.setRowCount(fila_actual + 1)

                for columna_idx, valor in enumerate(nueva_fila):
                    item = QTableWidgetItem(str(valor))
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    tabla_widget.setItem(fila_actual, columna_idx, item)

                if tabla_widget not in self.filas_agregadas:
                    self.filas_agregadas[tabla_widget] = []
                self.filas_agregadas[tabla_widget].append(fila_actual)

                print("Fila en blanco creada y habilitada para edición en la tabla actual en la pestaña/tab",
                      nombre_tabla_actual)
        else:
            self.mostrar_mensaje_emergente("La modificación no está habilitada, no se agregará ninguna fila.")

    def gestionar_registro_eliminar(self):
        if self.modificar_habilitado:
            tabla_widget = self.tabWidget.currentWidget()
            if tabla_widget is not None:
                tabla = tabla_widget.findChild(QTableWidget)
                if tabla is not None:
                    selected_items = tabla.selectedItems()
                    if selected_items:
                        fila_a_eliminar = selected_items[0].row()
                        id_fila = tabla.item(fila_a_eliminar, 0).text()
                        index = self.tabWidget.currentIndex()
                        nombre_tabla_actual = self.tabWidget.tabText(index)
                        self.eliminar_fila_en_bd(nombre_tabla_actual, id_fila)
                        tabla.removeRow(fila_a_eliminar)
                        print("Fila eliminada.")
                    else:
                        print("No hay filas seleccionadas para eliminar.")
                else:
                    print("No se encontró la QTableWidget en la pestaña actual.")
            else:
                print("El widget de la pestaña actual no existe.")
        else:
            self.mostrar_mensaje_emergente("No se puede eliminar filas sin habilitar la modificación.")

    def insertar_fila_en_bd(self, nombre_tabla, fila_data):
        # Construye una consulta SQL para insertar datos en la tabla
        placeholders = ', '.join(['?'] * len(fila_data))
        columns = ', '.join(self.tablas[nombre_tabla]["columnas"])
        query = f"INSERT INTO `{nombre_tabla}` ({columns}) VALUES ({placeholders})"

        try:
            self.cursor.execute(query, fila_data)
            self.conn.commit()
        except Exception as e:
            self.mostrar_mensaje_emergente(f"Error al insertar fila en {nombre_tabla}: {str(e)}")

    def eliminar_fila_en_bd(self, nombre_tabla, id_fila):
        columnas = self.tablas[nombre_tabla]["columnas"]
        query = f"DELETE FROM `{nombre_tabla}` WHERE {columnas[0]} = ?"
        try:
            self.cursor.execute(query, (id_fila,))
            self.conn.commit()
        except Exception as e:
            self.mostrar_mensaje_emergente(f"Error al eliminar fila en {nombre_tabla}: {str(e)}")

    def mostrar_mensaje_emergente(self, mensaje):
        # Muestra un mensaje emergente con el mensaje dado
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(mensaje)
        msg.setWindowTitle("Mensaje")
        msg.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())