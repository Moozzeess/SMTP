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
servidor_smtp = 'smtp.office365.com'
puerto_smtp = 587
Remitente = 'servicio.sistemas@papalote.org.mx'
contraseña_remitente = 'Servicio_ss25'

# Variables de configuración del script
LIMITE_CORREOS_POR_EJECUCION = 20 # Cantidad máxima de correos a intentar enviar por cada ejecución del script
LIMITE_DIARIO_CORREOS = 5000 # Límite diario de correos para evitar alertas de spam
MAX_INTENTOS_CONEXION_SMTP = 3 # Intentos para restablecer la conexión SMTP

# Rutas de archivos
ARCHIVO_CONTEO_DIARIO = '/home/ss/Correos/conteo_correos_diario.json'
ARCHIVO_FECHA_ULTIMO_ENVIO = '/home/ss/Correos/fecha_ultimo_envio.json' # Archivo para registrar la fecha del último envío procesado
RUTA_CUERPO_HTML = '/home/ss/Correos/pruebas.html' # Ruta del archivo HTML del cuerpo del correo

# Configuración de conexión a la base de datos MySQL
DB_CONFIG = {
    "host": "192.168.56.1",
    "user": "ss",
    "password": "Papalote24",
    "database": "pruebas"
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

# Funciones para la fecha del último envío (para la validación "ayer se envió")
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
    
    # Cargar el cuerpo HTML
    cuerpo_html = cargar_cuerpo_html(RUTA_CUERPO_HTML)
    if cuerpo_html is None:
        exit(1)

    # Determinar las fechas (hoy y ayer)
    hoy_dt = datetime.now()
    hoy_str = hoy_dt.strftime('%d/%m/%Y')
    
    ayer_dt = hoy_dt - timedelta(days=1)
    ayer_str = ayer_dt.strftime('%d/%m/%Y')

    # Cargar el conteo diario y verificar si es un nuevo día
    ultima_fecha_conteo, conteo_actual_diario = cargar_conteo_diario()
    
    # La comparación de fecha para el conteo diario se basa en la fecha real del sistema
    fecha_actual_sistema_para_conteo = hoy_dt.strftime('%Y-%m-%d') # Formato YYYY-MM-DD
    if ultima_fecha_conteo != fecha_actual_sistema_para_conteo:
        print(f"Nuevo día del sistema detectado para el conteo diario. (Anterior: {ultima_fecha_conteo}, Hoy: {fecha_actual_sistema_para_conteo})")
        conteo_actual_diario = 0
        guardar_conteo_diario(fecha_actual_sistema_para_conteo, conteo_actual_diario)
    else:
        print(f"Conteo diario actual (basado en la fecha del sistema): {conteo_actual_diario} de {LIMITE_DIARIO_CORREOS} permitidos.")

    # Verificar si el límite diario ha sido alcanzado
    if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
        print(f"Límite diario de correos ({LIMITE_DIARIO_CORREOS}) alcanzado.")
        exit(0) 

    # Conexión a la base de datos
    conexion_base = conectar_bd()
    if conexion_base is None:
        exit(1)

    cursor = conexion_base.cursor(dictionary=True)

    try:
        # Validar si se enviaron correos el día anterior
        ultima_fecha_envio_registrada = cargar_fecha_ultimo_envio()
        
        # Si no se registró un envío exitoso para ayer, el script no procederá hoy.
        if ultima_fecha_envio_registrada != ayer_str and ultima_fecha_envio_registrada != '':
            print(f"No se detectaron envíos exitosos para la fecha {ayer_str}. Los correos para {hoy_str} no serán enviados.")
            print("Por favor, asegúrate de que los correos del día anterior se procesaron correctamente.")
            exit(0)
        
        # Obtener correos pendientes para hoy
        correos_restantes_hoy = LIMITE_DIARIO_CORREOS - conteo_actual_diario
        limite_esta_ejecucion = min(LIMITE_CORREOS_POR_EJECUCION, correos_restantes_hoy)

        if limite_esta_ejecucion <= 0:
            print("Se ha superado el límite de correos por día o no hay correos restantes para enviar en esta ejecución.")
            cursor.close()
            conexion_base.close()
            exit(0)

        # Consulta SQL para obtener correos de la fecha de hoy
        sql_query = """
        SELECT
            t1.email,
            t1.fecha_visita,
            t1.Ds_Merchant_Order,
            t2.Ds_Order,
            t2.Ds_ErrorCode,
            t2.Ds_ErrorMessage
        FROM
            order_data AS t1
        INNER JOIN
            order_data_online AS t2 ON t1.Ds_Merchant_Order = t2.Ds_Order
        WHERE
            t1.fecha_visita = %s
            AND t2.Ds_ErrorCode = '00'
            AND t2.Ds_ErrorMessage = 'completed'
        LIMIT %s
        """
        cursor.execute(sql_query, (hoy_str, limite_esta_ejecucion))
        pendientes = cursor.fetchall()
        print(f"Se han encontrado {len(pendientes)} correos pendientes para hoy ({hoy_str}).\n")

        if not pendientes:
            print(f"No hay correos nuevos por enviar en este momento para la fecha de hoy ({hoy_str}).")
            exit(0)

        # Conexión al servidor SMTP
        server_smtp = conectar_servidor_smtp()
        if server_smtp is None:
            exit(1) 

        # Enviar correos
        contador_correos_enviados_esta_ejecucion = 0
        for row in pendientes:
            if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
                print(f"Límite diario de correos ({LIMITE_DIARIO_CORREOS}) alcanzado durante la ejecución.")
                break

            correo_destino = row['email'] 
            correo_id = row['Ds_Merchant_Order'] 

            mensaje = MIMEMultipart('alternative')
            mensaje['From'] = Remitente
            mensaje['To'] = correo_destino
            mensaje['Subject'] = "¡Opinemos en Papalote!"

            mensaje.attach(MIMEText(cuerpo_html, 'html'))

            try:
                print(f'Enviando... (fecha: {hoy_str})')
                server_smtp.sendmail(Remitente, correo_destino, mensaje.as_string())
                print(f"Mensaje enviado correctamente a {correo_destino}.\n")

                # Actualizar el conteo diario y la fecha de último envío procesado
                contador_correos_enviados_esta_ejecucion += 1
                conteo_actual_diario += 1
                # Siempre guarda el conteo diario con la fecha REAL del sistema
                guardar_conteo_diario(fecha_actual_sistema_para_conteo, conteo_actual_diario) 
                # Guarda la fecha de HOY (calculada automáticamente) como la última fecha de envío
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

                print(f"El correo a {correo_destino} no se pudo enviar en este intento. Se intentará en la siguiente ejecución.")
                pass 

            except Exception as e:
                print(f"Error Inesperado al enviar correo a {correo_destino}: {e}\n")
                pass 

    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        exit(1)

    finally:
        # Cerrar conexiones de forma segura
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
    print(f"Total de correos enviados hoy: {conteo_actual_diario}.\n")

if __name__ == "__main__":
    main()
