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
servidor_smtp = 'smtp.domino.com'
puerto_smtp = 123
Remitente = 'correo_remitente@example.com'
contraseña_remitente = 'contraseña_de_correo_remitente'

# Variables de configuración del script
LIMITE_DIARIO_CORREOS = 5000 # Límite diario de correos para evitar alertas de spam
MAX_INTENTOS_CONEXION_SMTP = 3 # Intentos para restablecer la conexión SMTP
LIMITE_CORREOS_POR_EJECUCION = 200 # Límite de correos por ejecución del demonio activado en ese momento

# Rutas de archivos
ARCHIVO_CONTEO_DIARIO = '/ruta_donde_se_va_trabajar/conteo_correos_diario.json'           #Archivo para contabilizar los correos que se han enviado diario
ARCHIVO_FECHA_ULTIMO_ENVIO = '/ruta_donde_se_va_trabajar/fecha_ultimo_envio.json'         #Archivo para registrar la última fecha en que se envío
RUTA_CUERPO_HTML = '/ruta_donde_se_va_trabajar/archivo.html'                              #Archivo HTML del cuerpo del mensaje
ARCHIVO_CORREOS_ENVIADOS_DIA = '/ruta_donde_se_va_trabajar/correos_enviados_dia.json'     #Archivo para registrar IDs de correos enviados

# Configuración de conexión a la base de datos MySQL
DB_CONFIG = {
    "host": "Ip o nombre",
    "user": "usuario",
    "password": "contraseña",
    "database": "nombre de la base de datos a trabajar"
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
def cuerpo_html(ruta_archivo):
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

    # Carga la última fecha que se procesó exitosamente
    ultima_fecha_procesada_str = cargar_fecha_ultimo_envio()

    if ultima_fecha_procesada_str:
        try:
            # Convierte la fecha registrada a datetime
            fecha_inicio_procesamiento = datetime.strptime(ultima_fecha_procesada_str, '%d/%m/%Y')
            print(f"Última fecha procesada registrada: {ultima_fecha_procesada_str}. Continuando desde el día siguiente.")
            # Si ya se procesó, el inicio para esta ejecución es el día siguiente
            fecha_inicio_procesamiento += timedelta(days=1)
        except ValueError:
            print("Formato de la última fecha procesada incorrecto. Iniciando desde una fecha manual.")
            fecha_inicio_procesamiento = None
    else:
        fecha_inicio_procesamiento = None # Si no hay fecha registrada, forza la entrada manual

    if fecha_inicio_procesamiento is None:
        while True:
            fecha_str_input = input("Fecha de INICIO para el procesamiento (dd/mm/aaaa): ")
            try:
                fecha_inicio_procesamiento = datetime.strptime(fecha_str_input, '%d/%m/%Y')
                break
            except ValueError:
                print("Formato de fecha incorrecto. usa dd/mm/aaaa.")

    # Fecha actual del sistema
    hoy_sistema_dt = datetime.now()

    ultima_fecha_conteo, conteo_actual_diario = cargar_conteo_diario()
    fecha_actual_sistema_str = hoy_sistema_dt.strftime('%Y-%m-%d')

    if ultima_fecha_conteo != fecha_actual_sistema_str:
        # Reinicia el conteo diario si es un nuevo día del sistema
        conteo_actual_diario = 0
        guardar_conteo_diario(fecha_actual_sistema_str, conteo_actual_diario)
    else:
        print(f"Conteo diario actual para {fecha_actual_sistema_str}: {conteo_actual_diario} de {LIMITE_DIARIO_CORREOS} permitidos.")

    current_date_to_process = fecha_inicio_procesamiento

    while current_date_to_process <= hoy_sistema_dt:
        hoy_str = current_date_to_process.strftime('%d/%m/%Y')

        # Verifica si el límite diario del sistema ha sido alcanzado
        if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
            print(f"Se ha alcanzado el límite de correos permitidos por día ({LIMITE_DIARIO_CORREOS}) para la fecha del sistema {fecha_actual_sistema_str}.")
            break 

        # Conexión a la base de datos
        conexion_base = conectar_bd()
        if conexion_base is None:
            print(f"No se pudo conectar a la base de datos para la fecha {hoy_str}. Saltando a la siguiente fecha.")
            current_date_to_process += timedelta(days=1)
            continue

        cursor = conexion_base.cursor(dictionary=True)

        try:
            # Cargamos los IDs de correos ya enviados para la fecha actual de procesamiento (hoy_str)
            ids_correos_enviados_para_esta_fecha = cargar_correos_enviados_dia(hoy_str)

            # Consulta para contar los correos que cumplen con la restricción
            sql_count_query = """ SELECT COUNT(*) AS total_registros FROM tabla_de_trabajo """

            cursor.execute(sql_count_query, (hoy_str,))
            total_registros_bd = cursor.fetchone()['total_registros']
            print(f"La consulta SQL arrojó un total de {total_registros_bd} correos para la fecha {hoy_str}.")

            if total_registros_bd == 0:
                print(f"No hay correos nuevos por enviar para la fecha {hoy_str}.")
                # Guardar la fecha de procesamiento aunque no se envíen correos, para que se avance
                guardar_fecha_ultimo_envio(hoy_str)
                current_date_to_process += timedelta(days=1)
                cursor.close()
                conexion_base.close()
                continue # Pasa al siguiente día

            #Sentencia en SQL que perimte la restricción de si pago el usuario y el código en línea es 00
            sql_query = """ SELECT tabla FROM base de datos"""


            cursor.execute(sql_query, (hoy_str,))
            pendientes = cursor.fetchall()

            if not pendientes:
                print(f"No hay correos nuevos por enviar en este momento para la fecha {hoy_str}.")
                guardar_fecha_ultimo_envio(hoy_str)
                current_date_to_process += timedelta(days=1)
                cursor.close()
                conexion_base.close()
                continue # Pasa al siguiente día

            # Conexión al servidor SMTP
            server_smtp = conectar_servidor_smtp()
            if server_smtp is None:
                print(f"No se pudo conectar al servidor SMTP. Deteniendo el procesamiento de fechas.")
                break # Sale del bucle diario si no se puede conectar al SMTP

            # Enviar correos
            contador_correos_enviados_esta_ejecucion = 0 # Reiniciar para cada fecha procesada
            for row in pendientes:
                correo_id = row['Ds_Merchant_Order']

                # Saltar el correo si ya fue enviado para la FECHA DE PROCESAMIENTO ACTUAL
                if correo_id in ids_correos_enviados_para_esta_fecha:
                    print(f"El correo con ID {correo_id} ya fue enviado para la fecha {hoy_str}. Saltando.")
                    continue

                # Verificar el límite diario del sistema antes de enviar
                if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
                    print(f"Límite diario de correos ({LIMITE_DIARIO_CORREOS}) alcanzado para la fecha del sistema {fecha_actual_sistema_str}.")
                    print("El script se detendrá para hoy. Continuará mañana.")
                    break # Salir del bucle de correos individuales
                
                 # Verificar el límite de correos por ejecución
                if contador_correos_enviados_esta_ejecucion >= LIMITE_CORREOS_POR_EJECUCION:
                    print(f"Se alcanzó el límite de {LIMITE_CORREOS_POR_EJECUCION} correos por esta ejecución. El demonio se reactivará.")
                    break # Salir del bucle de correos individuales para terminar la ejecución actual

                correo_destino = row['email']

                mensaje = MIMEMultipart('alternative')
                mensaje['From'] = Remitente
                mensaje['To'] = correo_destino
                mensaje['Subject'] = "Asunto del correo"
                mensaje.attach(MIMEText(cuerpo_html, 'html'))

                try:
                    print(f'Enviando correo (ID: {correo_id}) a {correo_destino}...')
                    server_smtp.sendmail(Remitente, correo_destino, mensaje.as_string())
                    print(f"[{contador_correos_enviados_esta_ejecucion+1}] Mensaje enviado correctamente a {correo_destino} (ID: {correo_id}).")

                    # Actualiza el conteo diario (basado en la fecha del SISTEMA)
                    contador_correos_enviados_esta_ejecucion += 1
                    conteo_actual_diario += 1
                    guardar_conteo_diario(fecha_actual_sistema_str, conteo_actual_diario)

                    # Actualiza el registro de IDs enviados
                    ids_correos_enviados_para_esta_fecha.add(correo_id)
                    guardar_correos_enviados_dia(hoy_str, ids_correos_enviados_para_esta_fecha)
                    guardar_fecha_ultimo_envio(hoy_str)

                    time.sleep(1) # Pausa después de enviar cada correo

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
                    print(f"El correo {correo_destino} (ID: {correo_id}) no se pudo enviar.")
                    pass # Continuar con el siguiente correo si hay conexión de nuevo
                except Exception as e:
                    print(f"Error Inesperado al enviar correo a {correo_destino} (ID: {correo_id}): {e}\n")
                    pass

            if server_smtp:
                try:
                    server_smtp.quit()
                    print('Sesión SMTP cerrada para la fecha actual de procesamiento.')
                except Exception as e:
                    print(f"Error al cerrar la sesión SMTP para la fecha {hoy_str}: {e}")

        except Exception as e:
            print(f"Error inesperado al procesar la fecha {hoy_str}: {e}")
            pass
        
        finally:
            if cursor:
                cursor.close()
            if conexion_base:
                conexion_base.close()
                print(f'Conexión a la base de datos cerrada para la fecha {hoy_str}.')

        # Si el límite diario se alcanzó en la última iteración
        if conteo_actual_diario < LIMITE_DIARIO_CORREOS:
            current_date_to_process += timedelta(days=1)
        else:
            break


    print(f"Última fecha procesada: {current_date_to_process - timedelta(days=1).strftime('%d/%m/%Y') if current_date_to_process > fecha_inicio_procesamiento else 'Ninguna fecha completa.'}")
    print(f"Total de correos enviados hoy: {fecha_actual_sistema_str}): {conteo_actual_diario}.")

if __name__ == "__main__":
    main()
