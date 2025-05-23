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
LIMITE_CORREOS_POR_EJECUCION = 100 # Cantidad máxima de correos a intentar enviar por cada ejecución del script
LIMITE_DIARIO_CORREOS = 5000 # Límite diario de correos para evitar alertas de spam
MAX_INTENTOS_CONEXION_SMTP = 3 # Intentos para restablecer la conexión SMTP

# Rutas de archivos
ARCHIVO_CONTEO_DIARIO = '/ruta/de/Correos/conteo_correos_diario.json'
ARCHIVO_FECHA_ULTIMO_ENVIO = '/ruta/de/Correos/fecha_ultimo_envio.json' # Nuevo archivo para registrar la fecha del último envío
RUTA_CUERPO_HTML = '/ruta/de/Correos/archivo_como_cuerpo.html' # Ruta del archivo HTML del cuerpo del correo

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
        return '', 0 # Retorna fecha vacía y conteo 0 si el archivo no existe
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

# Funciones para la fecha del último envío (para la validación "ayer se envió"
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
    else:
        print(f"Conteo diario actual: {conteo_actual_diario} de {LIMITE_DIARIO_CORREOS} permitidos.")

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
        """
        # Si la fecha de envío registrada NO es el día anterior a la fecha manual, se detiene exit(0)
        if ultima_fecha_envio_registrada != ayer_str and ultima_fecha_envio_registrada != '':
            print(f"No se detectaron envíos para la fecha {ayer_str}. Los correos para {hoy_str} no serán enviados.")
            pass
        """
        # Obtener correos pendientes para la fecha manual
        correos_restantes_hoy = LIMITE_DIARIO_CORREOS - conteo_actual_diario
        limite_esta_ejecucion = min(LIMITE_CORREOS_POR_EJECUCION, correos_restantes_hoy)

        if limite_esta_ejecucion <= 0:
            print("Se ha superado el límite de correos por día o no hay correos restantes para enviar.")
            cursor.close()
            conexion_base.close()
            exit(0)

        # Consulta SQL
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
        LIMIT %s
        """
        cursor.execute(sql_query, (hoy_str, limite_esta_ejecucion))
        pendientes = cursor.fetchall()
        print(f"Se han encontrado {len(pendientes)} correos. {hoy_str}.\n")

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
            if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
                print(f"Límite diario de correos ({LIMITE_DIARIO_CORREOS}) alcanzado.")
                break

            correo_destino = row['email'] 
            correo_id = row['id'] 

            mensaje = MIMEMultipart('alternative')
            mensaje['From'] = Remitente
            mensaje['To'] = correo_destino
            mensaje['Subject'] = "Correo de prueba"

            mensaje.attach(MIMEText(cuerpo_html, 'html'))

            try:
                print(f'Enviando...')
                server_smtp.sendmail(Remitente, correo_destino, mensaje.as_string())
                print(f"Mensaje enviado correctamente a {correo_destino}.\n")

                # Actualizar el conteo y la fecha de último envío
                contador_correos_enviados_esta_ejecucion += 1
                conteo_actual_diario += 1
                guardar_conteo_diario(fecha_actual_sistema, conteo_actual_diario) # Guardar el conteo diario con la fecha REAL del sistema
                guardar_fecha_ultimo_envio(hoy_str) # Guardar la fecha de último envío como la fecha manual que se acaba de procesar
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

    print(f"\nSe han enviado {contador_correos_enviados_esta_ejecucion} correos.")
    print(f"Total de correos enviados: {conteo_actual_diario}.\n")

if __name__ == "__main__":
    main()
