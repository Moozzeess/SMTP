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
servidor_smtp = ''
puerto_smtp = 
Remitente = ''
contraseña_remitente = ''

# Variables de configuración del script
LIMITE_DIARIO_CORREOS = 10000 # Límite diario de correos para evitar alertas de spam
MAX_INTENTOS_CONEXION_SMTP = 3 # Intentos para restablecer la conexión SMTP

# Rutas de archivos
ARCHIVO_CONTEO_DIARIO = '/home/Correos/conteo_correos_diario.json'           #Archivo para contabilizar los correos que se han enviado diario
ARCHIVO_FECHA_ULTIMO_ENVIO = '/home/Correos/fecha_ultimo_envio.json'         #Archivo para registrar la última fecha en que se envío
RUTA_CUERPO_HTML = '/home/Correos/pruebas.html'                              #Archivo HTML del cuerpo del mensaje
ARCHIVO_CORREOS_ENVIADOS_DIA = '/home/Correos/correos_enviados_dia.json'     #Archivo para registrar IDs de correos enviados

# Configuración de conexión a la base de datos MySQL
DB_CONFIG = {
    "host": "",
    "user": "",
    "password": "",
    "database": ""
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
def cargar_correos_enviados_dia(fecha_a_procesar_str):
    try:
        if os.path.exists(ARCHIVO_CORREOS_ENVIADOS_DIA):
            with open(ARCHIVO_CORREOS_ENVIADOS_DIA, 'r') as f:
                all_data = json.load(f)
                # Retorna el set de IDs para la fecha_a_procesar_str, o un set vacío si la fecha no existe
                return set(all_data.get(fecha_a_procesar_str, []))
        return set() # Si el archivo no existe, no hay IDs enviados para ninguna fecha
    except json.JSONDecodeError as e:
        print(f"Archivo de correos enviados del día vacío o corrupto. Se inicializará. {e}")
        return set()
    except Exception as e:
        print(f"Error al cargar los correos enviados del día. {e}")
        return set()

def guardar_correos_enviados_dia(fecha_a_guardar_str, ids_enviados_para_fecha):
    try:
        all_data = {}
        if os.path.exists(ARCHIVO_CORREOS_ENVIADOS_DIA):
            try:
                with open(ARCHIVO_CORREOS_ENVIADOS_DIA, 'r') as f:
                    all_data = json.load(f)
            except json.JSONDecodeError:
                # Si el archivo está corrupto o vacío, se inicializa un directorio vacío
                all_data = {}

        # Actualizar los IDs para la fecha específica
        all_data[fecha_a_guardar_str] = sorted(list(ids_enviados_para_fecha))

        with open(ARCHIVO_CORREOS_ENVIADOS_DIA, 'w') as f:
            json.dump(all_data, f, indent=4) # Indentación para mejor legibilidad
    except Exception as e:
        print(f"No se pudo guardar los correos enviados del día: {e}")

def main():

    # Cargar el cuerpo como HTML
    cuerpo_html = cargar_cuerpo_html(RUTA_CUERPO_HTML)
    if cuerpo_html is None:
        exit(1)

    while True: #Introducimos la fecha en la consola para enviar correo a esos días
        fecha_manual_str = input("Fecha (dd/mm/aaaa): ")
        try:
            fecha_dt = datetime.strptime(fecha_manual_str, '%d/%m/%Y')
            break
        except ValueError:
            print("Formato de fecha incorrecto. Por favor, usa dd/mm/aaaa.")

    hoy_str = fecha_manual_str # La fecha manual es la que se introduce al query SQL para extrar esa fecha
    hoy_dt = fecha_dt #Indica la fecha que se está procesando

    ayer_dt = hoy_dt - timedelta(days=1)
    ayer_str = ayer_dt.strftime('%d/%m/%Y') # Validación de fecha dd/mm/aaaa

    # Cargar el conteo diario y verificar la fecha
    ultima_fecha, conteo_actual_diario = cargar_conteo_diario()

    # La comparación de fecha para el conteo diario se basa en la fecha real del sistema
    fecha_actual_sistema = datetime.now().strftime('%Y-%m-%d')
    ultima_fecha, conteo_actual_diario = cargar_conteo_diario()
    
    if ultima_fecha != fecha_actual_sistema:
        # Reiniciar conteo diario si es un nuevo día de ejecución
        guardar_conteo_diario(fecha_actual_sistema, 0)
        conteo_actual_diario = 0
        print(f"Nuevo día detectado. Conteo diario reiniciado a 0 para {fecha_actual_sistema}.")
    else:
        print(f"Conteo diario actual: {conteo_actual_diario} de {LIMITE_DIARIO_CORREOS} permitidos para {fecha_actual_sistema}.")

    # Cargamos los IDs de correos ya enviados para la fecha actual del sistema
    ids_correos_enviados_para_esta_fecha = cargar_correos_enviados_dia(hoy_str)

    # Verificar si el límite diario ha sido alcanzado
    if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
        print(f"Se ha alcanzado el límite de correos permitidos por día ({LIMITE_DIARIO_CORREOS}) para la fecha del sistema {fecha_actual_sistema}.")
        exit(0)

    # Conexión a la base de datos
    conexion_base = conectar_bd()
    if conexion_base is None:
        exit(1)

    cursor = conexion_base.cursor(dictionary=True)

    try:
        # Validar si se enviaron correos el día anterior a la fecha manual
        ultima_fecha_envio_registrada = cargar_fecha_ultimo_envio()

        #Consulta para contar los correos que cumplen con la restricción y envíar esa cantidad
        sql_count_query = """ SELECT COUNT(*) AS total_registros FROM order_data AS t1
            INNER JOIN order_data_online AS t2 ON t1.Ds_Merchant_Order = t2.Ds_Order 
            WHERE t1.fecha_visita = %s 
                AND t2.Ds_ErrorCode = '00' 
                AND t2.Ds_ErrorMessage = 'completed' 
                AND email = 'alberto.silva@papalote.org.mx' """

        cursor.execute(sql_count_query, (hoy_str,))
        total_registros_bd = cursor.fetchone()['total_registros']
        print(f"La consulta SQL arrojó un total de {total_registros_bd} correos para la fecha {hoy_str}.\n")

        if total_registros_bd == 0:
            print(f"No hay correos nuevos por enviar en este momento para la fecha {hoy_str}.")
            exit()
        
        #Sentencia en SQL que perimte la restricción de si pago el usuario y el código en línea es 00
        sql_query = """ SELECT
                t1.email,
                t1.fecha_visita,
                t1.Ds_Merchant_Order,
                t2.Ds_Order,
                t2.Ds_ErrorCode,
                t2.Ds_ErrorMessage
            FROM order_data AS t1 INNER JOIN
                order_data_online AS t2 ON t1.Ds_Merchant_Order = t2.Ds_Order
            WHERE
                t1.fecha_visita = %s
                AND t2.Ds_ErrorCode = '00'
                AND t2.Ds_ErrorMessage = 'completed'
                AND email = 'alberto.silva@papalote.org.mx' """

        cursor.execute(sql_query, (hoy_str,))
        pendientes = cursor.fetchall()

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
            correo_id = row['Ds_Merchant_Order']

            # Saltar el correo si ya fue enviado en la fecha del sistema actual
            if correo_id in ids_correos_enviados_para_esta_fecha:
                print(f"El correo con ID {correo_id} ya fue enviado para la fecha {hoy_str}. Saltando.\n")
                continue

            if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
                print(f"Límite diario de correos ({LIMITE_DIARIO_CORREOS}) alcanzado.")
                break

            correo_destino = row['email']

            mensaje = MIMEMultipart('alternative')
            mensaje['From'] = Remitente
            mensaje['To'] = correo_destino
            mensaje['Subject'] = "Opinemos en papalote"

            mensaje.attach(MIMEText(cuerpo_html, 'html'))

            try:
                print(f'Enviando...')
                server_smtp.sendmail(Remitente, correo_destino, mensaje.as_string())
                print(f"[{contador_correos_enviados_esta_ejecucion+1}] Mensaje enviado correctamente a {correo_destino} (ID: {correo_id}).\n")

                # Actualizar el conteo diario (fecha del sistema)
                contador_correos_enviados_esta_ejecucion += 1
                conteo_actual_diario += 1
                guardar_conteo_diario(fecha_actual_sistema, conteo_actual_diario) #FECHA DEL SISTEMA

                # Actualizar el registro de IDs enviados (fecha manual)
                ids_correos_enviados_para_esta_fecha.add(correo_id)
                guardar_correos_enviados_dia(hoy_str, ids_correos_enviados_para_esta_fecha) #FECHA ingresada
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
    print(f"Total de correos enviados hoy: {conteo_actual_diario}.\n")

if __name__ == "__main__":
    main()
