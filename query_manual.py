import html
import smtplib
import mysql.connector
import time
import os
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTPServerDisconnected

# Configuración del servidor SMTP
servidor_smtp = 'smtp.dominio.com'
puerto_smtp = 123456789
Remitente = 'correo@example.org.mx'
contraseña_remitente = '123456789'

# Variables de configuración del script
# LIMITE_CORREOS_POR_EJECUCION = 100 # Esta variable ya no se usará como límite directo en la consulta
LIMITE_DIARIO_CORREOS = 5000 # Límite diario de correos para evitar alertas de spam
MAX_INTENTOS_CONEXION_SMTP = 3 # Intentos para restablecer la conexión SMTP

# Rutas de archivos
ARCHIVO_CONTEO_DIARIO = '/ruta/de/Correos/conteo_correos_diario.json'
ARCHIVO_FECHA_ULTIMO_ENVIO = '/ruta/de/Correos/fecha_ultimo_envio.json'
RUTA_CUERPO_HTML = '/ruta/de/Correos/archivo_como_cuerpo.html'
ARCHIVO_CORREOS_ENVIADOS_DIA = '/ruta/de/Correos/correos_enviados_dia.json' # Nuevo archivo para registrar IDs de correos enviados

# Configuración de conexión a la base de datos MySQL
DB_CONFIG = {
    "host": "ipdelservidor",
    "user": "nombre_usuario",
    "password": "contraseña usuario",
    "database": "nombre de la base"
}

# Conexión a la base de datos MySQL
def conectar_bd():
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        print('Conexión establecida con la base de datos.\n')
        return conexion
    except Exception as e:
        print(f"No se ha podido establecer la conexión con la BD: {e}")
        return None

# Conexión servidor SMTP
def conectar_servidor_smtp():
    for intento in range(MAX_INTENTOS_CONEXION_SMTP):
        try:
            server = smtplib.SMTP(servidor_smtp, puerto_smtp)
            server.starttls()
            server.login(Remitente, contraseña_remitente)
            print('Se ha iniciado sesión correctamente con el servidor SMTP.\n')
            return server
        except Exception as e:
            print(f"Fallo al conectar con el servidor SMTP: {e}")
            time.sleep(5) # Esperar antes de reintentar
    print("No se pudo conectar al servidor SMTP después de varios intentos.")
    return None

# Cargar el cuerpo del mensaje HTML
def cargar_cuerpo_html(ruta_archivo):
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo_html:
            cuerpo = archivo_html.read()
            print('Se ha cargado correctamente el archivo HTML.')
            return cuerpo
    except Exception as e:
        print(f'No se ha podido cargar el cuerpo del mensaje: {e}')
        return None

# Función para el conteo diario de correos enviados
def cargar_conteo_diario():
    try:
        if os.path.exists(ARCHIVO_CONTEO_DIARIO):
            with open(ARCHIVO_CONTEO_DIARIO, 'r') as f:
                data = json.load(f)
                return data.get('fecha', ''), data.get('conteo', 0)
        return '', 0
    except json.JSONDecodeError as e:
        print(f"Archivo de conteo diario corrupto o vacío. {e}")
        return '', 0
    except Exception as e:
        print(f"Error al cargar el conteo diario. {e}")
        return '', 0

def guardar_conteo_diario(fecha_str, conteo):
    try:
        with open(ARCHIVO_CONTEO_DIARIO, 'w') as f:
            json.dump({'fecha': fecha_str, 'conteo': conteo}, f)
    except Exception as e:
        print(f"No se pudo guardar el conteo diario: {e}")

# Funciones para la fecha del último envío
def cargar_fecha_ultimo_envio():
    try:
        if os.path.exists(ARCHIVO_FECHA_ULTIMO_ENVIO):
            with open(ARCHIVO_FECHA_ULTIMO_ENVIO, 'r') as f:
                data = json.load(f)
                return data.get('ultima_fecha_envio', '')
        return ''
    except json.JSONDecodeError as e:
        print(f"Archivo de fecha de último envío corrupto o vacío. {e}")
        return ''
    except Exception as e:
        print(f"Error al cargar la fecha del último envío. {e}")
        return ''

def guardar_fecha_ultimo_envio(fecha_str):
    try:
        with open(ARCHIVO_FECHA_ULTIMO_ENVIO, 'w') as f:
            json.dump({'ultima_fecha_envio': fecha_str}, f)
    except Exception as e:
        print(f"No se pudo guardar la fecha del último envío: {e}")

# Funciones para el registro de correos enviados por día
def cargar_correos_enviados_dia(fecha_actual_sistema):
    try:
        if os.path.exists(ARCHIVO_CORREOS_ENVIADOS_DIA):
            with open(ARCHIVO_CORREOS_ENVIADOS_DIA, 'r') as f:
                data = json.load(f)
                # Si la fecha en el archivo no coincide con la fecha actual del sistema, reiniciamos el registro
                if data.get('fecha') == fecha_actual_sistema:
                    return set(data.get('ids_enviados', []))
                else:
                    return set() # Nuevo día, resetear IDs
        return set()
    except json.JSONDecodeError as e:
        print(f"Archivo de correos enviados del día corrupto o vacío. {e}")
        return set()
    except Exception as e:
        print(f"Error al cargar los correos enviados del día. {e}")
        return set()

def guardar_correos_enviados_dia(fecha_actual_sistema, ids_enviados):
    try:
        with open(ARCHIVO_CORREOS_ENVIADOS_DIA, 'w') as f:
            json.dump({'fecha': fecha_actual_sistema, 'ids_enviados': list(ids_enviados)}, f)
    except Exception as e:
        print(f"No se pudo guardar los correos enviados del día: {e}")


def main():

    # Cargar el cuerpo como HTML
    cuerpo_html = cargar_cuerpo_html(RUTA_CUERPO_HTML)
    if cuerpo_html is None:
        exit(1)

    while True:
        fecha_manual_str = input("Fecha (dd/mm/aaaa): ")
        try:
            fecha_dt = datetime.strptime(fecha_manual_str, '%d/%m/%Y')
            break
        except ValueError:
            print("Formato de fecha incorrecto. Por favor, usa dd/mm/aaaa.")

    hoy_str = fecha_manual_str # La fecha manual es la 'hoy' para la consulta SQL
    hoy_dt = fecha_dt

    ayer_dt = hoy_dt - timedelta(days=1)
    ayer_str = ayer_dt.strftime('%d/%m/%Y') # Formato dd/mm/aaaa para la validación

    # Cargar el conteo diario y verificar la fecha
    ultima_fecha, conteo_actual_diario = cargar_conteo_diario()

    # La comparación de fecha para el conteo diario se basa en la fecha real del sistema
    fecha_actual_sistema = datetime.now().strftime('%Y-%m-%d')
    if ultima_fecha != fecha_actual_sistema:
        print(f"Nuevo día del sistema detectado para el conteo diario. (Anterior: {ultima_fecha}, Hoy: {fecha_actual_sistema})")
        conteo_actual_diario = 0
        guardar_conteo_diario(fecha_actual_sistema, conteo_actual_diario)
        # Si es un nuevo día, también reiniciamos el registro de IDs de correos enviados
        guardar_correos_enviados_dia(fecha_actual_sistema, set())
    else:
        print(f"Conteo diario actual: {conteo_actual_diario} de {LIMITE_DIARIO_CORREOS} permitidos.")

    # Cargar los IDs de correos ya enviados para la fecha actual del sistema
    ids_correos_enviados_hoy = cargar_correos_enviados_dia(fecha_actual_sistema)

    # Verificar si el límite diario ha sido alcanzado
    if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
        print(f"Se ha alcanzado el límite de correos permitidos por día. ({LIMITE_DIARIO_CORREOS})")
        exit(0)

    # Conexión a la base de datos
    conexion_base = conectar_bd()
    if conexion_base is None:
        exit(1)

    cursor = conexion_base.cursor(dictionary=True)

    try:
        # Validar si se enviaron correos el día anterior a la fecha manual
        ultima_fecha_envio_registrada = cargar_fecha_ultimo_envio()
        
        sql_count_query = """
        SELECT
            COUNT(*) AS total_registros
        FROM
            order_data AS t1
        INNER JOIN
            order_data_online AS t2 ON t1.Ds_Merchant_Order = t2.Ds_Order
        WHERE
            t1.fecha = %s
            AND t2.codigo = '00'
            AND t2.Message = 'completed'
        """
        cursor.execute(sql_count_query, (hoy_str,))
        total_registros_bd = cursor.fetchone()['total_registros']
        print(f"La consulta SQL arrojó un total de {total_registros_bd} correos para la fecha {hoy_str}.\n")

        if total_registros_bd == 0:
            print(f"No hay correos nuevos por enviar en este momento para la fecha {hoy_str}.")
            exit(0)
sql_query = """
        SELECT
            t1.email,
            t1.fecha,
            t1.id,
            t2.id_registrado,
            t2.codigo,
            t2.Message
        FROM
            order_data AS t1
        INNER JOIN
            order_data_online AS t2 ON t1.Ds_Merchant_Order = t2.Ds_Order
        WHERE
            t1.fecha = %s
            AND t2.codigo = '00'
            AND t2.Message = 'completed'
        """
        cursor.execute(sql_query, (hoy_str,))
        pendientes = cursor.fetchall()
        print(f"Se han cargado {len(pendientes)} correos de la base de datos para la fecha {hoy_str}.\n")

        if not pendientes:
            print(f"No hay correos nuevos por enviar en este momento.")
            exit(0)

        # Conexión al servidor SMTP
        server_smtp = conectar_servidor_smtp()
        if server_smtp is None:
            exit(1)

        # Enviar correos
        contador_correos_enviados_esta_ejecucion = 0
        for row in pendientes:
            correo_id = row['id']
            # Saltar el correo si ya fue enviado en la fecha del sistema actual
            if correo_id in ids_correos_enviados_hoy:
                print(f"El correo con ID {correo_id} ya fue enviado hoy. Saltando.")
                continue

            if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
                print(f"Límite diario de correos ({LIMITE_DIARIO_CORREOS}) alcanzado.")
                break

            correo_destino = row['email']

            mensaje = MIMEMultipart('alternative')
            mensaje['From'] = Remitente
            mensaje['To'] = correo_destino
            mensaje['Subject'] = "Correo de prueba"

            mensaje.attach(MIMEText(cuerpo_html, 'html'))

            try:
                print(f'Enviando correo con ID: {correo_id} a {correo_destino}...')
                server_smtp.sendmail(Remitente, correo_destino, mensaje.as_string())
                print(f"Mensaje enviado correctamente a {correo_destino}.\n")

                # Actualizar el conteo, el registro de IDs enviados y la fecha de último envío
                contador_correos_enviados_esta_ejecucion += 1
                conteo_actual_diario += 1
                ids_correos_enviados_hoy.add(correo_id) # Agregar el ID al set de enviados

                guardar_conteo_diario(fecha_actual_sistema, conteo_actual_diario)
                guardar_correos_enviados_dia(fecha_actual_sistema, ids_correos_enviados_hoy)
                guardar_fecha_ultimo_envio(hoy_str)
                time.sleep(1.25) # Pausa después de enviar cada correo

            except SMTPServerDisconnected as e:
                print(f"Desconexión SMTP al enviar a {correo_destino}. Reintentando conexión...")
                try:
                    server_smtp.quit()
                except Exception:
                    pass

                server_smtp = conectar_servidor_smtp()
                if server_smtp is None:
                    print("No se pudo reconectar al servidor SMTP. Deteniendo ejecución.")
                    break

                print(f"El correo {correo_destino} no se pudo enviar.")
                pass

            except Exception as e:
                print(f"Error Inesperado al enviar correo a {correo_destino}: {e}\n")
                pass

    except Exception as e:
        print(f"Error inesperado en el proceso principal: {e}")
        exit(1)

    finally:
        if server_smtp:
            try:
                server_smtp.quit()
                print('\nSesión SMTP cerrada.')
            except Exception as e:
                print(f"Error al cerrar la sesión SMTP: {e}")

        if cursor:
            cursor.close()
            print('Cursor de la base de datos cerrado.')
        if conexion_base:
            conexion_base.close()
            print('Conexión a la base de datos cerrada.')

    print(f"\nSe han enviado {contador_correos_enviados_esta_ejecucion} correos en esta ejecución.")
    print(f"Total de correos enviados hoy (acumulado): {conteo_actual_diario}.\n")

if __name__ == "__main__":
    main()
