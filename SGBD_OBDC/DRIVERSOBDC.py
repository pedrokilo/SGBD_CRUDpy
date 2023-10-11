import pyodbc

drivers = [driver for driver in pyodbc.drivers()]
print(drivers)