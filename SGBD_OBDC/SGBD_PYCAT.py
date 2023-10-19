import sys
import traceback
import pyodbc
import re
from PyQt5 import Qt
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QLineEdit, QTreeWidgetItem, QTableWidgetItem, \
    QTableWidget, QStackedWidget, QComboBox, QSpinBox, QCheckBox, QDoubleSpinBox, QRadioButton, QDialog, QLabel, \
    QPushButton, QVBoxLayout, QTextEdit, QGroupBox, QAbstractItemView
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
            # Pasa la conexión y el nombre DSN a la instancia de InterfazSgbd
            self.main_window = InterfazSgbd(conn, dsn_name)
            self.main_window.show()
            self.close()
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Error al conectar: {str(e)}\nDetalles:\n{error_details}")
            self.mostrar_mensaje(f"Error al conectar: {str(e)}\nDetalles:\n{error_details}")

    def mostrar_mensaje(self, mensaje):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(mensaje)
        msg.setWindowTitle("Mensaje")
        msg.exec_()

class InterfazSgbd(QMainWindow):
    def __init__(self, conn, dsn_name):
        super().__init__()
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.dsn_name = dsn_name
        loadUi("INTERFAZ DE BASE DE DATOS0.ui", self)
        self.tab_objetos = self.findChild(QTableWidget, 'tab_objetos')
        self.esquema_db = EsquemaBaseDatos(self.conn)
        self.tabla_esquema = TablasEsquema(self.conn)
        self.sentencias_sql = SentenciasSQL(self.conn, self.tab_DatosTabla, self.cursor, self.tab_EdicionTabla)
        self.arbol.setHeaderLabel(self.dsn_name)
        self.cargar_esquemas_y_tablas()
        self.stackedWidget = QStackedWidget(self)
        self.ventanas_tablas.setCurrentIndex(0)
        self.tab_objetos.setRowCount(0)
        self.tab_objetos.setColumnCount(2)  # Dos columnas: Nombre de la tabla y Comentario de la tabla
        self.tab_objetos.setHorizontalHeaderLabels(["Nombre de la tabla", "Comentario de la tabla"])
        self.tab_DatosTabla.setRowCount(0)
        self.tab_DatosTabla.setColumnCount(1)
        self.tab_EdicionTabla.setRowCount(0)
        self.tab_EdicionTabla.setColumnCount(1)
        self.tab_objetos.resizeColumnsToContents()
        self.arbol.itemClicked.connect(self.tabla_objetos_llenar)
        self.arbol.itemClicked.connect(self.mostrar_informacion_esquema)
        self.tab_objetos.itemClicked.connect(self.mostrar_informacion_tabla_seleccionada)
        self.tab_objetos.itemDoubleClicked.connect(self.cambiar_a_ventana_indice_2)
        self.btn_crear_esquema.clicked.connect(self.mostrar_ventana_crear_esquema)
        self.btn_crear_tabla.clicked.connect(self.mostrar_ventana_crear_tabla)
        self.btn_modificar_tabla.clicked.connect(self.modificar_tabla)
        self.btn_borrar_esquema.clicked.connect(self.borrar_esquema_seleccionado)
        self.btn_abrir_tabla.clicked.connect(self.abrir_tabla_seleccionada)
        self.btn_salir_edicion.clicked.connect(self.salir_ventana_principal)
        self.btn_salir_datos.clicked.connect(self.salir_ventana_principal)
        self.btn_borrar_tabla.clicked.connect(self.borrar_tabla_seleccionada)
        self.btn_borrar_tabla.clicked.connect(self.cargar_esquemas_y_tablas)
        self.actualizar_todo.clicked.connect(self.cargar_esquemas_y_tablas)
        self.btn_activar_mod_objetos.clicked.connect(self.activar_modificacion)
        self.btn_cancelar_mod_objetos.clicked.connect(self.cancelar_modificacion)
        self.btn_guardar_mod_objetos.clicked.connect(self.guardar_modificacion)
        self.modo_edicion_activado = False  # Bandera para controlar el modo de edición
        # Agregar una variable para almacenar el nombre de la tabla seleccionada al hacer doble clic
        self.nombre_tabla_seleccionada = None  # Variable para almacenar el nombre de la tabla seleccionada
        self.btn_activar_mod_objetos.clicked.connect(self.activar_edicion)
        self.btn_borrar_campo.clicked.connect(self.LDD_borrar_campo_seleccionado)
        self.actualizar_ldd.clicked.connect(self.modificar_tabla)
        self.actualizar_lmd.clicked.connect(self.abrir_tabla_seleccionada)

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
        esquema_seleccionado = item.parent().text(0) if item.parent() else item.text(0)
        self.nombre_tabla_seleccionada = None  # Reiniciar la variable al cambiar de esquema

        self.tab_objetos.setRowCount(0)
        self.tab_objetos.setColumnCount(2)  # Agrega una columna adicional

        tablas = self.tabla_esquema.obtener_tablas_de_esquema(esquema_seleccionado)
        self.lbl_nombres_objetos.setText(
            f"Estás viendo las tablas del esquema '{esquema_seleccionado}'")
        for tabla in tablas:
            row_position = self.tab_objetos.rowCount()
            self.tab_objetos.insertRow(row_position)
            self.tab_objetos.setItem(row_position, 0, QTableWidgetItem(tabla))

            # Obtén el comentario de la tabla y agrégalo a la segunda columna de tab_objetos
            comentario_tabla = self._obtener_comentario_tabla(esquema_seleccionado, tabla)
            self.tab_objetos.setItem(row_position, 1, QTableWidgetItem(comentario_tabla))

        self.tab_objetos.setHorizontalHeaderLabels(["Nombre de la tabla", "Comentario de la tabla"])
        self.tab_objetos.resizeColumnsToContents()
        self.tab_objetos.update()
        self.tab_objetos.repaint()

    def mostrar_informacion_tabla_seleccionada(self, item):
        nombre_tabla = item.text()
        esquema_seleccionado = None
        root = self.arbol.invisibleRootItem()
        for i in range(root.childCount()):
            esquema_item = root.child(i)
            for j in range(esquema_item.childCount()):
                tabla_item = esquema_item.child(j)
                if tabla_item.text(0) == nombre_tabla:
                    esquema_seleccionado = esquema_item.text(0)
                    self.nombre_tabla_seleccionada = nombre_tabla  # Almacena el nombre de la tabla seleccionada
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
        elif self.modo_edicion_activado == False:
            # Si no se encuentra el esquema correspondiente, muestra un mensaje o toma alguna acción apropiada.
            self.mostrar_mensaje("Lo que has seleccionado es un comentario o era una tabla que ya no existe en el esquema actual.")

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
            character_set = self.obtener_characterset_esquema(nombre_esquema)
            info_text = f'\n\nNombre de Esquema:\n\n"{nombre_esquema}"\n\nNombre de Conexión:\n\n"{nombre_dsn}"\n\nCharacter set:  {character_set}'

        self.label_informacion.setText(info_text)
        self.stackedWidget.setCurrentIndex(0)  # Asegúrate de que se muestra la página correcta en tu QStackedWidget.

    def guardar_nombre_tabla_seleccionada(self, item):
        # Al hacer doble clic en una casilla, almacenar el nombre de la tabla seleccionada
        self.nombre_tabla_seleccionada = item.text() if item else None

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
         if not self.modo_edicion_activado:
            self.abrir_tabla_seleccionada()

    def activar_edicion(self):
        # Al presionar el botón "Activar", guardar el nombre de la tabla seleccionada
        fila_seleccionada = self.tab_objetos.currentRow()
        if fila_seleccionada >= 0:
            item_seleccionado = self.arbol.currentItem()
            if item_seleccionado:
                self.nombre_tabla_seleccionada = item_seleccionado.text(0)
            else:
                # Si no hay elemento seleccionado en el árbol, muestra un mensaje de error o manejo adecuado.
                self.mostrar_mensaje("Seleccione una tabla en el árbol antes de activar la edición.")
                return

            # Habilitar la edición de la tabla
            self.tab_objetos.setEditTriggers(QAbstractItemView.DoubleClicked)

    def abrir_tabla_seleccionada(self):
        # Verifica si hay alguna fila seleccionada en tab_objetos
        if self.tab_objetos.currentRow() != -1:  # -1 significa que ninguna fila está seleccionada
            self.ventanas_tablas.setCurrentIndex(2)
            # Obtener el nombre de la tabla seleccionada
            tabla_seleccionada = self.tab_objetos.item(self.tab_objetos.currentRow(), 0).text()

            # Obtener el nombre del esquema de la tabla seleccionada
            nombre_del_esquema = self._obtener_esquema_de_tabla_seleccionada(tabla_seleccionada)

            if nombre_del_esquema:
                self.sentencias_sql.cargar_datos_tabla(
                nombre_del_esquema, tabla_seleccionada, self.conn, self.dsn_name)
                self.lbl_nombre_tabla_LMD.setText(
                    f"Estás en la tabla '{tabla_seleccionada}' del esquema '{nombre_del_esquema}'")
            else:
                self.mostrar_mensaje("No se pudo encontrar el esquema para la tabla seleccionada.")
        else:
            # Opcional: Mostrar un mensaje de alerta si ninguna fila está seleccionada
            self.mostrar_mensaje("Por favor, seleccione una tabla antes de presionar 'ENTRAR A MODIFICACION DE DATOS DE LA TABLA'.")

    def activar_modificacion(self):
        # Habilitar la edición de las celdas de la tabla tab_objetos
        self.modo_edicion_activado = True
        self.tab_objetos.setEditTriggers(QAbstractItemView.DoubleClicked)

    def cancelar_modificacion(self):
        # Deshabilitar la edición de las celdas de la tabla tab_objetos
        self.tab_objetos.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def guardar_modificacion(self):
        # Obtener los valores de la fila actualmente seleccionada en la tabla
        fila_seleccionada = self.tab_objetos.currentRow()
        if fila_seleccionada == -1:
            return

        # Obtener el nuevo nombre y comentario de las celdas de la fila
        nuevo_nombre = self.tab_objetos.item(fila_seleccionada, 0).text()
        nuevo_comentario = self.tab_objetos.item(fila_seleccionada, 1).text()

        # Obtener el esquema y nombre de la tabla seleccionada desde el árbol
        item_seleccionado = self.arbol.currentItem()
        if not item_seleccionado or not item_seleccionado.parent():
            # No se seleccionó un esquema, no se puede realizar la modificación
            self.mostrar_mensaje("Por favor, seleccione un esquema antes de guardar la modificación.")
            return

        esquema_seleccionado = item_seleccionado.parent().text(0)
        nombre_tabla_seleccionada = item_seleccionado.text(0)

        # Llamar a la función para modificar la tabla en SentenciasSQL
        if self.sentencias_sql.modificar_tabla_objetos(esquema_seleccionado, nombre_tabla_seleccionada, nuevo_nombre,
                                                       nuevo_comentario):
            self.mostrar_mensaje("Modificación guardada exitosamente.")
            self.tab_objetos.clearSelection()
        else:
            self.mostrar_mensaje("Error al guardar la modificación de la tabla.")

    def salir_ventana_principal(self):
        self.ventanas_tablas.setCurrentIndex(0)

    def modificar_tabla(self):
        try:
            # Verifica si hay alguna fila seleccionada en tab_objetos
            if self.tab_objetos.currentRow() != -1:  # -1 significa que ninguna fila está seleccionada
                # Cambiar al índice 1 del QStackedWidget
                self.ventanas_tablas.setCurrentIndex(1)
                # Obtener el nombre de la tabla seleccionada
                tabla_seleccionada = self.tab_objetos.item(self.tab_objetos.currentRow(), 0).text()

                # Obtener el nombre del esquema de la tabla seleccionada
                nombre_del_esquema = self._obtener_esquema_de_tabla_seleccionada(tabla_seleccionada)

                if nombre_del_esquema:
                    self.sentencias_sql.carga_datos_tabla_diseño(
                        nombre_del_esquema, tabla_seleccionada, self.conn, self.dsn_name)
                    self.lbl_nombre_tabla_LDD.setText(f"Estás en la tabla '{tabla_seleccionada}' del esquema '{nombre_del_esquema}'")
                else:
                    self.mostrar_mensaje("No se pudo encontrar el esquema para la tabla seleccionada.")
            else:
                # Opcional: Mostrar un mensaje de alerta si ninguna fila está seleccionada
                self.mostrar_mensaje("Por favor, seleccione una tabla antes de presionar 'ENTAR AL DISEÑO DE LA TABLA (COLUMNAS)'.")
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Ocurrió un error: {str(error_details)}")
            # Opcionalmente, puedes imprimir el error completo para propósitos de depuración

    def obtener_characterset_esquema(self, nombre_esquema):
        query = f"""SELECT
        default_character_set_name
        FROM
        information_schema.SCHEMATA
        WHERE schema_name = '{nombre_esquema}';"""  # Corrección aquí: Especificar la columna y condición adecuada
        self.cursor.execute(query)
        character_set = self.cursor.fetchone()[0]
        return character_set

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

        item_seleccionado = self.arbol.currentItem()
        if not item_seleccionado or not item_seleccionado.parent():
            # No hay esquema seleccionado
            self.mostrar_mensaje("Por favor, seleccione un esquema para eliminar.")
            return

        nombre_esquema = item_seleccionado.text(0)

        # Pregunta al usuario si está seguro de eliminar el esquema y todas las tablas dentro de él
        respuesta = QMessageBox.question(
            self, "Confirmación", f"¿Está seguro de eliminar el esquema '{nombre_esquema}' y todas sus tablas y objetos?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if respuesta == QMessageBox.Yes:
            # El usuario confirmó, procede a eliminar el esquema y sus objetos
            if self.sentencias_sql.borrar_esquema_completo(nombre_esquema):
                # Recarga la lista de esquemas después de eliminar
                self.cargar_esquemas_y_tablas()
                self.mostrar_mensaje(f"Se eliminó el esquema '{nombre_esquema}' y sus objetos exitosamente.")
            else:
                self.mostrar_mensaje(f"No se pudo eliminar el esquema '{nombre_esquema}' y sus objetos.")

    def mostrar_ventana_crear_esquema(self):
        ventana_crear_esquema = VentanaCrearEsquema()
        if ventana_crear_esquema.exec_() == QDialog.Accepted:
            # La ventana emergente se cerró con "Aceptar", realiza la creación del esquema aquí
            nombre_esquema = ventana_crear_esquema.le_nombre_esquema.text()
            characterset = ventana_crear_esquema.cb_characterset.currentText()

            # Realiza la operación de creación del esquema en la base de datos aquí
            # Llama al método para crear el esquema en la base de datos
            if self.sentencias_sql.crear_esquema(nombre_esquema, characterset):
                self.mostrar_mensaje(f"Se creó el esquema '{nombre_esquema}' con éxito.")
                # Actualiza el árbol u otras partes de la interfaz según sea necesario
                self.cargar_esquemas_y_tablas()
            else:
                self.mostrar_mensaje(f"No se pudo crear el esquema '{nombre_esquema}'.")

    def mostrar_ventana_crear_tabla(self):
        if not self.arbol.currentItem():
            self.mostrar_mensaje("Debe seleccionar un esquema antes de crear una tabla.")
            return

        ventana_crear_tabla = VentanaCrearTabla()
        if ventana_crear_tabla.exec_() == QDialog.Accepted:
            # La ventana fue aceptada (se hizo clic en "Crear")
            # Ahora puedes obtener los datos de la tabla creada
            nombre_tabla = ventana_crear_tabla.nombre_tabla_creada
            comentario_tabla = ventana_crear_tabla.comentario_tabla_creada

            # Abre la ventana InsertadoEnTabla con los datos obtenidos
            self.abrir_insertado_en_tabla(nombre_tabla, comentario_tabla)

    def abrir_insertado_en_tabla(self, nombre_tabla, comentario_tabla):
        insertado_en_tabla = InsertadoEnTabla()
        insertado_en_tabla.set_datos_tabla(nombre_tabla, comentario_tabla)
        insertado_en_tabla.show()

    def borrar_esquema_seleccionado(self):
        # Obtén el esquema seleccionado del árbol
        item_seleccionado = self.arbol.currentItem()
        if item_seleccionado and not item_seleccionado.parent():
            # Se seleccionó un esquema (no es una tabla)
            nombre_esquema = item_seleccionado.text(0)

            # Pregunta al usuario si está seguro de eliminar el esquema
            respuesta = QMessageBox.question(
                self, "Confirmación", f"¿Está seguro de eliminar el esquema '{nombre_esquema}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if respuesta == QMessageBox.Yes:
                # El usuario confirmó, procede a eliminar el esquema
                if self.sentencias_sql.borrar_esquema(nombre_esquema):
                    # Recarga la lista de esquemas después de eliminar
                    self.cargar_esquemas_y_tablas()
                    self.mostrar_mensaje(f"Se eliminó el esquema '{nombre_esquema}' exitosamente.")
                else:
                    self.mostrar_mensaje(f"No se pudo eliminar el esquema '{nombre_esquema}'.")
        else:
            self.mostrar_mensaje("Por favor, seleccione un esquema para eliminar.")

    def borrar_tabla_seleccionada(self):
        # Si no hay una tabla seleccionada, muestra un mensaje y termina.
        if self.tab_objetos.currentRow() == -1:
            self.mostrar_mensaje("Por favor, seleccione una tabla antes de borrar.")
            return

        tabla_seleccionada = self.tab_objetos.item(self.tab_objetos.currentRow(), 0).text()
        nombre_del_esquema = self._obtener_esquema_de_tabla_seleccionada(tabla_seleccionada)

        # Si no se puede encontrar el esquema para la tabla seleccionada, muestra un mensaje y termina.
        if not nombre_del_esquema:
            self.mostrar_mensaje("No se pudo encontrar el esquema para la tabla seleccionada.")
            return

        # Pide confirmación para eliminar.
        respuesta = QMessageBox.question(
            self,
            "Confirmación",
            f"¿Está seguro de eliminar la tabla {tabla_seleccionada} del esquema '{nombre_del_esquema}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        # Si el usuario confirma, procede con la eliminación.
        if respuesta == QMessageBox.Yes:
            if self.sentencias_sql.borrar_tabla_objeto_en_esquema(nombre_del_esquema, tabla_seleccionada):
                self._actualizar_vista_despues_de_borrar(nombre_del_esquema)
                self.mostrar_mensaje(f"Se eliminó la tabla '{tabla_seleccionada}' exitosamente.")

    def LDD_borrar_campo_seleccionado(self):
        # Si no hay una tabla seleccionada, muestra un mensaje y termina.
        if self.tab_EdicionTabla.currentRow() == -1:
            self.mostrar_mensaje("Por favor, seleccione una columna antes de borrar.")
            return
        tabla_seleccionada = self.tab_objetos.item(self.tab_objetos.currentRow(), 0).text()
        nombre_del_esquema = self._obtener_esquema_de_tabla_seleccionada(tabla_seleccionada)
        columna_seleccionada = self.tab_EdicionTabla.item(self.tab_EdicionTabla.currentRow(), 0).text()
        # Si no se puede encontrar el esquema para la tabla seleccionada, muestra un mensaje y termina.
        if not tabla_seleccionada:
            self.mostrar_mensaje("No se pudo encontrar la tabla seleccionada.")
            return
        respuesta = QMessageBox.question(
        self,"Confirmación",
        f"¿Está seguro de eliminar la columna {columna_seleccionada} de la tabla '{tabla_seleccionada}'?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
        )

        # Si el usuario confirma, procede con la eliminación.
        if respuesta == QMessageBox.Yes:
          if self.sentencias_sql.borrar_columna_LDD(nombre_del_esquema, tabla_seleccionada,columna_seleccionada):
              self._actualizar_vista_despues_de_borrar_LDD(tabla_seleccionada)
              self.mostrar_mensaje(f"Se eliminó la tabla '{columna_seleccionada}' exitosamente.")

    def _actualizar_vista_despues_de_borrar(self, nombre_del_esquema):
        """ Actualiza la vista del árbol y selecciona el esquema después de borrar una tabla. """
        self.cargar_esquemas_y_tablas()
        self.tab_objetos.setRowCount(0)
        self.tab_objetos.update()
        self.tab_objetos.repaint()

    def _actualizar_vista_despues_de_borrar_LDD(self,tabla_seleccionada):
        self.cargar_esquemas_y_tablas()
        self.tab_EdicionTabla.setRowCount(0)
        self.tab_EdicionTabla.update()
        self.tab_EdicionTabla.repaint()

    def mostrar_mensaje(self, mensaje):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(mensaje)
        msg.setWindowTitle("Mensaje")
        msg.exec_()

class SentenciasSQL:
    def __init__(self, conn, tab_DatosTabla, cursor, tab_EdicionTabla):
        self.dbms_name = self._get_dbms_name(conn)
        self.tab_DatosTabla = tab_DatosTabla
        self.tab_EdicionTabla = tab_EdicionTabla
        self.conn = conn  # Establece self.conn como un atributo de instancia
        self.dsn_name = None  # Establece self.dsn_name como un atributo de instancia
        self.cursor = cursor

    def _get_dbms_name(self, conn):
        return conn.getinfo(pyodbc.SQL_DBMS_NAME)

    def mostrar_esquemas(self):
        if self.dbms_name == 'SQL Server' or self.dbms_name in ['SQL Server Native Client RDA 11.0', 'ODBC Driver 17 for SQL Server']:
            return "SELECT name FROM sys.databases"
        elif self.dbms_name in ['Microsoft Access Driver (*.mdb, *.accdb)', 'Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)',
                                'Microsoft Access Text Driver (*.txt, *.csv)']:
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

    def carga_datos_tabla_diseño(self, nombre_del_esquema, tabla_seleccionada, conn, dsn_name):
        try:
            # Obtener la información de diseño detallada de la tabla
            query = f"SHOW FULL COLUMNS FROM `{nombre_del_esquema}`.`{tabla_seleccionada}`"
            self.cursor.execute(query)

            # Recuperar la información de diseño como una lista de tuplas
            diseño_tabla = self.cursor.fetchall()

            # Establecer el número de filas y columnas en tab_EdicionTabla
            self.tab_EdicionTabla.setRowCount(len(diseño_tabla))
            self.tab_EdicionTabla.setColumnCount(6)  # 6 columnas: Nombre, Tipo, Tamaño, Not Null, Llave, Comentario

            # Establecer encabezados de columna
            column_headers = ["Nombre", "Tipo", "Tamaño", "Not Null", "Llave", "Comentario"]
            self.tab_EdicionTabla.setHorizontalHeaderLabels(column_headers)

            # Rellenar la tabla con los datos de diseño
            for fila_idx, columna_info in enumerate(diseño_tabla):
                nombre_columna = columna_info[0]
                tipo_dato_full = columna_info[1]
                not_null_value = columna_info[3]
                llave_value = columna_info[4]
                comentario_columna = columna_info[8]  # El comentario de la columna está en la posición 8

                # Extraer tipo y tamaño
                match = re.match(r"([a-z]+)(?:\((\d+)\))?", tipo_dato_full, re.I)
                if match:
                    tipo_dato, tamaño_dato = match.groups()
                else:
                    tipo_dato, tamaño_dato = tipo_dato_full, None

                # Nombre de la columna
                self.tab_EdicionTabla.setItem(fila_idx, 0, QTableWidgetItem(nombre_columna))

                # Tipo de dato (usamos un combobox para seleccionar el tipo)
                tipo_combobox = QComboBox()
                tipo_combobox.addItem(tipo_dato)
                self.tab_EdicionTabla.setCellWidget(fila_idx, 1, tipo_combobox)

                # Tamaño (spinbox o sin contenido)
                if tamaño_dato:
                    tamaño_item = QSpinBox()
                    tamaño_item.setValue(int(tamaño_dato))
                    self.tab_EdicionTabla.setCellWidget(fila_idx, 2, tamaño_item)

                # Not Null (checkbox)
                not_null_checkbox = QCheckBox()
                not_null_checkbox.setChecked(not_null_value == "YES")
                self.tab_EdicionTabla.setCellWidget(fila_idx, 3, not_null_checkbox)

                # Llave
                if llave_value == "PRI":
                    llave_checkbox = QCheckBox("(PK)")
                    llave_checkbox.setChecked(True)
                    self.tab_EdicionTabla.setCellWidget(fila_idx, 4, llave_checkbox)
                elif llave_value == "MUL":
                    llave_radiobutton = QRadioButton("(FK)")
                    llave_radiobutton.setChecked(True)  # Radio button activado
                    self.tab_EdicionTabla.setCellWidget(fila_idx, 4, llave_radiobutton)

                # Comentario de la columna
                comentario_item = QTableWidgetItem(comentario_columna)
                self.tab_EdicionTabla.setItem(fila_idx, 5, comentario_item)

            return True  # Devuelve True para indicar que se cargaron los datos correctamente

        except Exception as e:
            error_details = traceback.format_exc()
            print(
                f"Error al cargar datos de diseño de la tabla {tabla_seleccionada} en el esquema {nombre_del_esquema}: {error_details}")
            return False  # Devuelve False para indicar que se produjo un error

    def cargar_datos_tabla(self, nombre_del_esquema, tabla_seleccionada, conn, dsn_name):
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

    def crear_esquema(self, nombre_esquema, characterset):
        try:
            # Modifica la sentencia SQL para utilizar el conjunto de caracteres válido
            sql = f"CREATE SCHEMA `{nombre_esquema}` DEFAULT CHARACTER SET {characterset};"
            self.cursor.execute(sql)
            self.conn.commit()
            return True
        except Exception as e:
            error_details = traceback.format_exc()
            # En caso de error, imprime el error para diagnóstico
            self.mostrar_mensaje(f"Error al crear el esquema {nombre_esquema}: {str(e)}\nDetalles:\n{error_details}")
            print(f"Error al crear el esquema {nombre_esquema}: {error_details}")
            return False

    def borrar_esquema(self, nombre_esquema):
        try:
            # Modifica la sentencia SQL para eliminar el esquema
            sql = f"DROP SCHEMA `{nombre_esquema}`;"
            self.cursor.execute(sql)
            self.conn.commit()
            return True
        except Exception as e:
            # Manejo de errores
            print(f"Error al eliminar el esquema {nombre_esquema}: {e}")
            return False

    def borrar_esquema_completo(self, nombre_esquema):
        try:
            # Obtén una lista de todas las tablas y objetos en el esquema
            tablas_objetos = self.obtener_tablas_y_objetos_en_esquema(nombre_esquema)

            # Elimina todas las tablas y objetos uno por uno
            for tabla_objeto in tablas_objetos:
                self.borrar_tabla_objeto_en_esquema(nombre_esquema, tabla_objeto)

            # Finalmente, elimina el esquema
            sql = f"DROP SCHEMA `{nombre_esquema}`;"
            self.cursor.execute(sql)
            self.conn.commit()
            return True
        except Exception as e:
            # Manejo de errores
            print(f"Error al eliminar el esquema {nombre_esquema} y sus objetos: {e}")
            return False

    def obtener_tablas_y_objetos_en_esquema(self, nombre_esquema):
        # Aquí debes ejecutar una consulta SQL para obtener una lista de todas las tablas y objetos en el esquema.
        # Deberías devolver una lista de nombres de tablas y objetos.
        # Por ejemplo:
        sql = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{nombre_esquema}';"
        self.cursor.execute(sql)
        tablas = [row[0] for row in self.cursor.fetchall()]
        return tablas

    def modificar_tabla_objetos(self, esquema, nombre_tabla, nuevo_nombre, nuevo_comentario):
        try:
            # Comprueba si se modificó el nombre de la tabla
            if nuevo_nombre != nombre_tabla:
                # Renombra la tabla
                query_rename = f"ALTER TABLE {esquema}.{nombre_tabla} RENAME TO {esquema}.{nuevo_nombre};"
                self.cursor.execute(query_rename)
                self.conn.commit()

            if nuevo_nombre:
                if nuevo_comentario:
                    # Modifica el comentario de la tabla
                    query_comment = f"ALTER TABLE {esquema}.{nuevo_nombre} COMMENT = '{nuevo_comentario}';"
                    self.cursor.execute(query_comment)
                    self.conn.commit()
            else:
                query_comment = f"ALTER TABLE {esquema}.{nombre_tabla} COMMENT = '{nuevo_comentario}';"
                self.cursor.execute(query_comment)
                self.conn.commit()

            return True
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Error al modificar la tabla: {str(error_details)}")
            return False

    def creacion_tabla_en_esquema(self, nombre_tabla, comentario_tabla, columnas):
        try:
            # Construye la sentencia SQL para crear la tabla
            # Utiliza columnas para construir la definición de la tabla
            columnas_definicion = ", ".join(columnas)
            sql = f"CREATE TABLE `{nombre_tabla}` ({columnas_definicion}) COMMENT '{comentario_tabla}';"
            self.cursor.execute(sql)
            self.conn.commit()
            return True
        except Exception as e:
            error_details = traceback.format_exc()
            # En caso de error, imprime el error para diagnóstico
            self.mostrar_mensaje(f"Error al crear la tabla {nombre_tabla}: {str(e)}\nDetalles:\n{error_details}")
            print(f"Error al crear la tabla {nombre_tabla}: {error_details}")
            return False

    def borrar_tabla_objeto_en_esquema(self, nombre_esquema, tabla_seleccionada):
        try:
            # 1. Obtener todas las restricciones de clave externa que hacen referencia a la tabla objetivo
            sql_constraints = f"""
            SELECT CONSTRAINT_NAME, TABLE_NAME 
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_NAME = '{tabla_seleccionada}'
            AND REFERENCED_TABLE_SCHEMA = '{nombre_esquema}';"""

            self.cursor.execute(sql_constraints)
            constraints = self.cursor.fetchall()

            # 2. Eliminar todas las restricciones de clave externa encontradas
            for constraint in constraints:
                constraint_name = constraint[0]
                referencing_table = constraint[1]
                sql_drop_fk = f"ALTER TABLE `{nombre_esquema}`.`{referencing_table}` DROP FOREIGN KEY `{constraint_name}`;"
                self.cursor.execute(sql_drop_fk)

            # 3. Una vez que todas las restricciones se eliminan, se puede eliminar la tabla
            sql_drop_table = f"DROP TABLE `{nombre_esquema}`.`{tabla_seleccionada}`;"

            self.cursor.execute(sql_drop_table)
            self.conn.commit()

        except Exception as e:
            error_details = traceback.format_exc()
            self.mostrar_mensaje(f"Error al intentar eliminar la tabla {tabla_seleccionada}: {error_details}")

    def borrar_columna_LDD(self, nombre_del_esquema, tabla_seleccionada, columna_seleccionada):
        try:
            # 1. Obtener todas las restricciones de clave externa que hacen referencia a la tabla objetivo
            sql_constraints = f"""
                                   SELECT CONSTRAINT_NAME, TABLE_NAME
                                   FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                                   WHERE REFERENCED_TABLE_NAME = '{tabla_seleccionada}'
                                   AND REFERENCED_TABLE_SCHEMA = '{nombre_del_esquema}';
                                   """
            self.cursor.execute(sql_constraints)
            constraints = self.cursor.fetchall()
            constraints = list(constraints)

            # 2. Eliminar todas las restricciones de clave externa encontradas
            for constraint in constraints:
                constraint_name = constraint[0]
                referencing_table = constraint[1]
                sql_drop_fk = f"ALTER TABLE `{nombre_del_esquema}`.`{referencing_table}` DROP FOREIGN KEY `{constraint_name}`;"
                self.cursor.execute(sql_drop_fk)

            self.cursor.execute(f"USE `{nombre_del_esquema}`;")
            sql_drop_column = f"ALTER TABLE `{tabla_seleccionada}` DROP COLUMN `{columna_seleccionada}`;"
            self.cursor.execute(sql_drop_column)
            self.conn.commit()

        except Exception as e:
            error_details = traceback.format_exc()
            self.mostrar_mensaje(f"Error al intentar eliminar la columna {columna_seleccionada}: {error_details}")

    def mostrar_mensaje(self, mensaje):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(mensaje)
        msg.setWindowTitle("Mensaje")
        msg.exec_()

class EsquemaBaseDatos:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.sentencias_sql = SentenciasSQL(self.conn, None, self.cursor, None)

    def obtener_esquemas(self):
        self.cursor.execute(self.sentencias_sql.mostrar_esquemas())
        return [row[0] for row in self.cursor.fetchall()]

class VentanaCrearEsquema(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crear Esquema")

        self.label_nombre_esquema = QLabel("Nombre del Esquema:")
        self.le_nombre_esquema = QLineEdit()

        self.label_characterset = QLabel("Character Set:")
        self.cb_characterset = QComboBox()
        self.cb_characterset.setEditable(True)  # Permite la edición del ComboBox

        self.btn_crear = QPushButton("Crear")
        self.btn_cancelar = QPushButton("Cancelar")

        layout = QVBoxLayout()
        layout.addWidget(self.label_nombre_esquema)
        layout.addWidget(self.le_nombre_esquema)
        layout.addWidget(self.label_characterset)
        layout.addWidget(self.cb_characterset)
        layout.addWidget(self.btn_crear)
        layout.addWidget(self.btn_cancelar)

        self.charsets_comunes = [
            "armscii8",
            "ascii",
            "big5",
            "binary",
            "cp850",
            "cp1250",
            "dec8",
            "eucjpms",
            "euckr",
            "gb2312",
            "gbk",
            "geostd8",
            "greek",
            "hebrew",
            "hp8",
            "keybcs2",
            "koi8r",
            "koi8u",
            "macce",
            "macroman",
            "sjis",
            "utf8mb3",
            "utf8",
            "utf16",
            "latin1",
            # Agrega más charsets según tus necesidades
        ]

        for charset in self.charsets_comunes:
            self.cb_characterset.addItem(charset)
        self.setLayout(layout)

        self.btn_crear.clicked.connect(self.crear_esquema)
        self.btn_cancelar.clicked.connect(self.close)

    def crear_esquema(self):
        nombre_esquema = self.le_nombre_esquema.text()
        characterset = self.cb_characterset.currentText()  # Obtiene el texto actual del ComboBox

        # Realiza la operación de creación del esquema en la base de datos aquí
        # Debes utilizar la información ingresada (nombre_esquema y characterset) para crear el esquema

        # Cierra la ventana emergente después de crear el esquema
        self.accept()

class TablasEsquema:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.sentencias_sql = SentenciasSQL(self.conn, None, self.cursor, None)

    def obtener_tablas_de_esquema(self, esquema):
        query = self.sentencias_sql.mostrar_tablas_de_esquema(esquema)
        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]

class VentanaCrearTabla(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crear Tabla")

        self.label_nombre_tabla = QLabel("Nombre de la Tabla:")
        self.le_nombre_tabla = QLineEdit()

        self.label_comentario_tabla = QLabel("Comentario de la Tabla (Opcional):")
        self.le_comentario_tabla = QLineEdit()

        self.btn_crear = QPushButton("Crear")
        self.btn_cancelar = QPushButton("Cancelar")

        layout = QVBoxLayout()
        layout.addWidget(self.label_nombre_tabla)
        layout.addWidget(self.le_nombre_tabla)
        layout.addWidget(self.label_comentario_tabla)
        layout.addWidget(self.le_comentario_tabla)
        layout.addWidget(self.btn_crear)
        layout.addWidget(self.btn_cancelar)

        self.setLayout(layout)

        self.btn_crear.clicked.connect(self.crear_tabla)
        self.btn_cancelar.clicked.connect(self.close)

    def crear_tabla(self):
        nombre_tabla = self.le_nombre_tabla.text()
        comentario_tabla = self.le_comentario_tabla.text()

        # Configura los valores en la ventana InsertadoEnTabla
        insertar_en_tabla = InsertadoEnTabla(nombre_tabla, comentario_tabla)
        insertar_en_tabla.exec_()  # Utiliza exec_() en lugar de show()

    def mostrar_ventana_crear_tabla(self):
        # Esta función se llama cuando se cierra la ventana InsertadoEnTabla
        self.show()  # Vuelve a mostrar la ventana VentanaCrearTabla

class InsertadoEnTabla(QDialog):
    def __init__(self, nombre_tabla, comentario_tabla):
        super().__init__()
        self.nombre_tabla = nombre_tabla
        self.comentario_tabla = comentario_tabla
        self.columnas = []
        self.fila_actual = 0

        # Establece el tamaño de la ventana según las dimensiones del archivo .ui
        self.setGeometry(0, 0, 698, 447)

        self.initUI()

    def initUI(self):
        self.setWindowTitle("DISEÑO DE NUEVO ATRIBUTO (COLUMNA)")
        layout = QVBoxLayout()

        self.tab_AniadirColumna = QTableWidget()
        self.tab_AniadirColumna.setColumnCount(6)
        self.tab_AniadirColumna.setHorizontalHeaderLabels(
            ["Nombre", "Tipo", "Tamaño", "Not Null", "Llave", "Comentario"]
        )

        self.btn_aniadir_fila = QPushButton("AÑADIR FILA")
        self.btn_insertar_campo = QPushButton("INSERTAR CAMPO")
        self.btn_borrar_fila = QPushButton("BORRAR CAMPO")
        self.btn_guardar = QPushButton("GUARDAR")
        self.btn_salir = QPushButton("CANCELAR")

        layout.addWidget(self.tab_AniadirColumna)
        layout.addWidget(self.btn_aniadir_fila)
        layout.addWidget(self.btn_insertar_campo)
        layout.addWidget(self.btn_borrar_fila)
        layout.addWidget(self.btn_guardar)
        layout.addWidget(self.btn_salir)

        # AGREGAR LLAVE FORANEA
        self.label_22 = QLabel("añadir la llave primaria de la tabla:")
        self.comboBox_TablasLlaves = QComboBox()
        self.comboBox_TablasLlaves.addItems([" "])  # Ejemplo de elementos
        self.btn_aniadir_llave = QPushButton("AÑADIR LLAVE A LA TABLA")

        layout.addWidget(self.label_22)
        layout.addWidget(self.comboBox_TablasLlaves)
        layout.addWidget(self.btn_aniadir_llave)

        self.setLayout(layout)

        self.btn_aniadir_fila.clicked.connect(self.btn_aniadir_fila_clicked)
        self.btn_insertar_campo.clicked.connect(self.btn_insertar_campo_clicked)
        self.btn_borrar_fila.clicked.connect(self.btn_borrar_fila_clicked)
        self.btn_guardar.clicked.connect(self.btn_guardar_clicked)


    def btn_aniadir_fila_clicked(self):
        self.tab_AniadirColumna.insertRow(self.fila_actual)
        self.fila_actual += 1

        for columna in range(6):
            if columna == 1:  # Tipo de dato (combobox)
                combo = QComboBox()
                combo.addItems(["INT", "VARCHAR", "DATE", "FLOAT", "BOOLEAN"])
                self.tab_AniadirColumna.setCellWidget(self.fila_actual - 1, columna, combo)
            elif columna == 2:  # Tamaño (combobox editable)
                combo = QComboBox()
                combo.setEditable(True)
                combo.addItems(["", "10", "20", "30", "50"])
                self.tab_AniadirColumna.setCellWidget(self.fila_actual - 1, columna, combo)
            elif columna == 3 or columna == 4:  # Not Null y Llave (checkbox)
                checkbox = QCheckBox()
                self.tab_AniadirColumna.setCellWidget(self.fila_actual - 1, columna, checkbox)
            else:
                item = QTableWidgetItem()
                self.tab_AniadirColumna.setItem(self.fila_actual - 1, columna, item)

    def btn_insertar_campo_clicked(self):
        nombre_columna = self.tab_AniadirColumna.item(self.fila_actual - 1, 0).text()
        tipo_columna = self.tab_AniadirColumna.cellWidget(self.fila_actual - 1, 1).currentText()
        tamano_columna = self.tab_AniadirColumna.cellWidget(self.fila_actual - 1, 2).currentText()
        not_null = self.tab_AniadirColumna.cellWidget(self.fila_actual - 1, 3).isChecked()
        llave = "(PK)" if self.tab_AniadirColumna.cellWidget(self.fila_actual - 1, 4).isChecked() else ""
        comentario_columna = self.tab_AniadirColumna.item(self.fila_actual - 1, 5).text()

        columna_sql = f"{nombre_columna} {tipo_columna}"
        if tamano_columna:
            columna_sql += f"({tamano_columna})"
        if not_null:
            columna_sql += " NOT NULL"
        if llave:
            columna_sql += f" {llave}"
        if comentario_columna:
            columna_sql += f" COMMENT '{comentario_columna}'"

        self.columnas.append(columna_sql)

    def btn_borrar_fila_clicked(self):
        if self.fila_actual > 0:
            self.tab_AniadirColumna.removeRow(self.fila_actual - 1)
            self.columnas.pop()
            self.fila_actual -= 1

    def btn_guardar_clicked(self):
        self.guardar_columnas()
        self.accept()

    def guardar_columnas(self):
        self.columnas = []
        for fila in range(self.tab_AniadirColumna.rowCount()):
            nombre_columna = self.tab_AniadirColumna.item(fila, 0).text()
            tipo_columna = self.tab_AniadirColumna.cellWidget(fila, 1).currentText()
            tamano_columna = self.tab_AniadirColumna.cellWidget(fila, 2).currentText()
            not_null = self.tab_AniadirColumna.cellWidget(fila, 3).isChecked()
            llave = "(PK)" if self.tab_AniadirColumna.cellWidget(fila, 4).isChecked() else ""
            comentario_columna = self.tab_AniadirColumna.item(fila, 5).text()

            columna_sql = f"{nombre_columna} {tipo_columna}"
            if tamano_columna:
                columna_sql += f"({tamano_columna})"
            if not_null:
                columna_sql += " NOT NULL"
            if llave:
                columna_sql += f" {llave}"
            if comentario_columna:
                columna_sql += f" COMMENT '{comentario_columna}'"

            self.columnas.append(columna_sql)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InicioSesion()
    window.show()
    sys.exit(app.exec_())
