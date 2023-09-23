import sys
import pyodbc
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, \
    QAbstractItemView, QMessageBox
from PyQt5.uic import loadUi
import sqlite3

# Definir la clase principal
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("interfaz_sgbd.ui", self)  # Carga el archivo de diseño

        # Crear un diccionario para almacenar las tablas y sus datos
        self.tablas = {}
        # Inicializar el diccionario de filas agregadas
        self.filas_agregadas = {}
        # Agregar esto al inicio de la clase MainWindow
        self.cambios_por_pestana = {}
        # Configurar la pestaña/tabla inicial
        self.cargar_tablas_desde_db()
        self.tabWidget.currentChanged.connect(self.cambiar_tabla_actual)

        # Configurar la selección de filas completas
        for nombre_tabla in self.tablas:
            tabla_widget = self.tablas[nombre_tabla]["tabla_widget"]
            tabla_widget.setEditTriggers(QTableWidget.NoEditTriggers)
            tabla_widget.setSelectionBehavior(QTableWidget.SelectRows)
            tabla_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        # Variable para rastrear si la edición está habilitada
        self.modificar_habilitado = False

        self.conectar_senales()

        # Conectar la señal currentChanged del QTabWidget a la función actualizar_vista_tabla_actual
        self.tabWidget.currentChanged.connect(self.actualizar_vista_tabla_actual)

    def conectar_senales(self):
        self.AGREGARbtn.clicked.connect(self.gestionar_registro_crear)
        self.MODIFICARbtn.clicked.connect(self.habilitar_modificacion)
        self.ELIMINARbtn.clicked.connect(self.gestionar_registro_eliminar)
        self.CANCELARbtn.clicked.connect(self.cancelar_modificacion)
        self.ACEPTARbtn.clicked.connect(self.aceptar_modificacion)

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

    # Modificar la función aceptar_modificacion para registrar los cambios
    # Modificar la función aceptar_modificacion para registrar los cambios
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

    def actualizar_fila_en_bd(self, nombre_tabla, fila_data, id_fila):
        columnas = self.tablas[nombre_tabla]["columnas"]
        set_clause = ", ".join([f"{col} = ?" for col in columnas])

        self.conectar_bd()
        query = f"UPDATE {nombre_tabla} SET {set_clause} WHERE {columnas[0]} = ?"
        self.cursor.execute(query, (*fila_data, id_fila))
        self.desconectar_bd()

    def insertar_fila_en_bd(self, nombre_tabla, fila_data):
        columnas = self.tablas[nombre_tabla]["columnas"]
        placeholders = ", ".join(["?" for _ in columnas])

        self.conectar_bd()
        query = f"INSERT INTO {nombre_tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
        self.cursor.execute(query, fila_data)
        self.desconectar_bd()


    def verificar_duplicados(self, nombre_tabla, nuevos_datos):
        # Verificar si existen duplicados en la tabla antes de realizar la actualización
        self.conectar_bd()
        cursor = self.cursor

        tabla_info = self.tablas[nombre_tabla]  # Obtener información de la tabla actual

        for nueva_fila in nuevos_datos:
            id_fila = nueva_fila[0]
            self.cursor.execute(f"SELECT COUNT(*) FROM {nombre_tabla} WHERE {tabla_info['columnas'][0]}=?", (id_fila,))
            count = cursor.fetchone()[0]
            if count > 1:
                self.desconectar_bd()
                return True

        self.desconectar_bd()
        return False

    def actualizar_vista_tabla_actual(self):
        index = self.tabWidget.currentIndex()
        nombre_tabla_actual = self.tabWidget.tabText(index)
        if nombre_tabla_actual:
            self.mostrar_datos_tabla(nombre_tabla_actual)

    def desactivar_edicion_celdas(self):
        # Esta función desactiva la edición en todas las tablas
        for nombre_tabla in self.tablas:
            tabla_widget = self.tablas[nombre_tabla]["tabla_widget"]
            tabla_widget.setEditTriggers(QTableWidget.NoEditTriggers)

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

    def mostrar_mensaje_emergente(self, mensaje):
        # Muestra un mensaje emergente con el mensaje dado
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(mensaje)
        msg.setWindowTitle("Mensaje")
        msg.exec_()

    def conectar_bd(self):
        # Abre la conexión a la base de datos si no está abierta
        if not hasattr(self, 'conn') or self.conn is None:
            self.conn = sqlite3.connect("biblioteca_bd.db")
                    #biblioteca_bd.db
                    # sistema.s3db
            self.cursor = self.conn.cursor()

    def desconectar_bd(self):
        # Cierra la conexión a la base de datos si está abierta
        if hasattr(self, 'conn') and self.conn is not None:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    def cargar_tablas_desde_db(self):
        self.conectar_bd()
        cursor = self.cursor

        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = cursor.fetchall()

        while self.tabWidget.count() > 0:
            self.tabWidget.removeTab(0)

        for tabla in tablas:
            nombre_tabla = tabla[0]
            self.agregar_tabla(nombre_tabla)

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
        self.conectar_bd()
        cursor = self.cursor

        self.cursor.execute(f"PRAGMA table_info({nombre_tabla})")
        columnas = cursor.fetchall()
        nombres_columnas = [columna[1] for columna in columnas]

        self.tablas[nombre_tabla] = {
            "tabla_widget": tabla_widget,
            "datos": [],
            "columnas": nombres_columnas
        }

        self.mostrar_datos_tabla(nombre_tabla)
        self.desconectar_bd()

    # Modificar la función mostrar_datos_tabla para aplicar los cambios pendientes
    # Modificar la función mostrar_datos_tabla para cargar datos y aplicar cambios pendientes
    def mostrar_datos_tabla(self, nombre_tabla):
        self.conectar_bd()
        cursor = self.cursor
        print(nombre_tabla)  # Aquí imprimirás el valor de 'nombre_tabla'
        cursor.execute(f"SELECT * FROM `{nombre_tabla}`")
        datos = cursor.fetchall()

        self.cursor.execute(f"PRAGMA table_info({nombre_tabla})")
        columnas = cursor.fetchall()
        nombres_columnas = [columna[1] for columna in columnas]

        tabla_info = self.tablas[nombre_tabla]
        tabla_widget = tabla_info["tabla_widget"]
        tabla_widget.setColumnCount(len(nombres_columnas))
        tabla_widget.setHorizontalHeaderLabels(nombres_columnas)
        print(f"Nombre de tabla: {nombre_tabla}")  # Imprimir el nombre de la tabla
        cursor.execute(f'SELECT * FROM "{nombre_tabla}"')
        # Aplicar cambios registrados si existen
        cambios_pendientes = self.cambios_por_pestana.get(nombre_tabla, [])
        for cambio in cambios_pendientes:
            tipo = cambio["tipo"]
            if tipo == "modificacion":
                nuevos_datos = cambio["datos"]
                for nueva_fila in nuevos_datos:
                    id_fila = nueva_fila[0]
                    valores_fila = nueva_fila[1:]
                    for fila_idx, fila in enumerate(datos):
                        if fila[0] == id_fila:
                            for columna_idx, valor in enumerate(valores_fila):
                                datos[fila_idx] = datos[fila_idx][:columna_idx + 1] + (valor,) + datos[fila_idx][
                                                                                                 columna_idx + 2:]

        tabla_info["datos"] = datos

        tabla_widget.setRowCount(len(datos))

        for fila_idx, fila in enumerate(datos):
            for columna_idx, valor in enumerate(fila):
                item = QTableWidgetItem(str(valor))
                tabla_widget.setItem(fila_idx, columna_idx, item)

        self.desconectar_bd()

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

    def eliminar_fila_en_bd(self, nombre_tabla, id_fila):
        columnas = self.tablas[nombre_tabla]["columnas"]
        self.conectar_bd()
        query = f"DELETE FROM {nombre_tabla} WHERE {columnas[0]} = ?"
        self.cursor.execute(query, (id_fila,))
        self.desconectar_bd()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())