import mysql.connector

try:
    conexion_base=mysql.connector.connect(
        host="",
        user="",
        password="",
        database="" 
    )
    cursor=conexion_base.cursor(dictionary=True)
    print('Conexión establecida con la base de datos')
    cursor.execute("show tables")
    for tabla in cursor:
        print(tabla)
    
    conexion_base.close()
    
except Exception as e:
    print(f'No se ha podido establecer la conexión con la BD. {e}')
    exit()
