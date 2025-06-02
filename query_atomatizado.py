"""              CONTEMPLAR ANTES DE EJECUTAR:
                              Considerar colocar los datos reales en la configuración de la BASE DE DATOS EN LA QUE SE VA A TRABAJAR
                              COLOCAR LA CONFIGURACIÓN DEL SERVIDOR DE CORREO ya sea MICRSOFT, GMAIL, ETC.
                              Las rutas de trabajo es el directorio donde se va a trabajar o donde está guaradao el script. Mantener en la misma carpeta todos los archivos.
                              Colocar el nombre de archivo html que se va a trabajar (linea 34)
                              Cambiar el asunto del correo (línea 288) 
                              Si se va a filtrar el query de la base de datos (línea 229 y 237) primero probarlo en MySQL"""
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

# Configuración del servidor SMTP Cambiar por el servidor de preferencia
servidor_smtp = 'smtp.dominio.com'
puerto_smtp = 123
Remitente = 'correo_remitente@dominio.com'                                            
contraseña_remitente = 'contraseña_correo_remitente'                                    

# Variables de configuración del script
LIMITE_DIARIO_CORREOS = 5000                                                    #Límite diario de correos para evitar alertas de spam
MAX_INTENTOS_CONEXION_SMTP = 3                                                  #Intentos para restablecer la conexión SMTP
LIMITE_CORREOS_POR_EJECUCION = 200                                              #Límite de correos por ejecución del demonio activado en ese momento

# Rutas de archivos deonde se va a trabajar
ARCHIVO_CONTEO_DIARIO = '/ruta_de_trabajo/conteo_correos_diario.json'           #Archivo para contabilizar los correos que se han enviado diario
ARCHIVO_FECHA_ULTIMO_ENVIO = '/ruta_de_trabajo/fecha_ultimo_envio.json'         #Archivo para registrar la última fecha en que se envío
RUTA_CUERPO_HTML = '/ruta_de_trabajo/Correos/archivo.html'                      #Archivo HTML del cuerpo del mensaje
ARCHIVO_CORREOS_ENVIADOS_DIA = '/ruta_de_trabajo/correos_enviados_dia.json'     #Archivo para registrar IDs de correos enviados

# Configuración de conexión a la base de datos MySQL                            
DB_CONFIG = {
    "host": "IP donde esta la base",
    "user": "nombre de usuario de la base de datos",
    "password": "contraseña_bd",
    "database": "nombre de la base de datos a trabajar"
}
def conectar_bd():
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        print('Conexión establecida con la base de datos.\n')
        return conexion
    except Exception as e:
        print(f"No se ha podido establecer la conexión con la BD: {e}")
        return None

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

def cargar_cuerpo_html(ruta_archivo):
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo_html:
            cuerpo_html = archivo_html.read()
            print('Se ha cargado correctamente el archivo HTML.')
            return cuerpo_html
    except Exception as e:
        print(f'No se ha podido cargar el cuerpo del mensaje: {e}')
        return None

#Carga los conteos de correos enviados por fecha desde un archivo JSON.
def cargar_conteo_diario():
    try:
        if os.path.exists(ARCHIVO_CONTEO_DIARIO):
            with open(ARCHIVO_CONTEO_DIARIO, 'r') as f:
                data = json.load(f)
                return data
        return {}
    except json.JSONDecodeError as e:
        print(f"Archivo de conteo diario corrupto o vacío. {e}")
        return {}
    except Exception as e:
        print(f"Error al cargar el conteo diario. {e}")
        return {}

#    Guarda los conteos de correos enviados por fecha en un archivo JSON.
def guardar_conteo_diario(conteos_por_fecha):
    try:
        with open(ARCHIVO_CONTEO_DIARIO, 'w') as f:
            json.dump(conteos_por_fecha, f, indent=4)
    except Exception as e:
        print(f"No se pudo guardar el conteo diario: {e}")

#Carga la fecha del último día completamente procesado.
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

#Guarda la fecha del último día completamente procesado.
def guardar_fecha_ultimo_envio(fecha_str):
    try:
        with open(ARCHIVO_FECHA_ULTIMO_ENVIO, 'w') as f:
            json.dump({'ultima_fecha_envio': fecha_str}, f)
    except Exception as e:
        print(f"No se pudo guardar la fecha del último envío: {e}")

#Carga los IDs de correos ya enviados para una fecha específica.
def cargar_correos_enviados_dia(fecha_a_procesar_str):
    try:
        if os.path.exists(ARCHIVO_CORREOS_ENVIADOS_DIA):
            with open(ARCHIVO_CORREOS_ENVIADOS_DIA, 'r') as f:
                all_data = json.load(f)
                # Retorna el set de IDs para la fecha_a_procesar_str, o un set vacío si la fecha no existe
                return set(all_data.get(fecha_a_procesar_str, []))
        return set() # Si el archivo no existe, no hay IDs enviados para ninguna fecha
    except json.JSONDecodeError as e:
        print(f"Archivo de correos enviados del día vacío o corrupto. {e}")
        return set()
    except Exception as e:
        print(f"Error al cargar los correos enviados del día. {e}")
        return set()

#Guarda los IDs de correos enviados para una fecha específica.
def guardar_correos_enviados_dia(fecha_a_guardar_str, ids_enviados_para_fecha):
    try:
        all_data = {}
        if os.path.exists(ARCHIVO_CORREOS_ENVIADOS_DIA):
            try:
                with open(ARCHIVO_CORREOS_ENVIADOS_DIA, 'r') as f:
                    all_data = json.load(f)
            except json.JSONDecodeError:
                # Si el archivo está corrupto o vacío, se inicializa un diccionario vacío
                all_data = {}

        # Actualizar los IDs para la fecha específica
        all_data[fecha_a_guardar_str] = sorted(list(ids_enviados_para_fecha))

        with open(ARCHIVO_CORREOS_ENVIADOS_DIA, 'w') as f:
            json.dump(all_data, f, indent=4)
    except Exception as e:
        print(f"No se pudo guardar los correos enviados del día: {e}")

def main():
    cuerpo_html = cargar_cuerpo_html(RUTA_CUERPO_HTML)
    if cuerpo_html is None:
        print("No se pudo cargar el cuerpo HTML. Saliendo del script.")
        return

    # Carga la última fecha que se procesó exitosamente
    ultima_fecha_completada_str = cargar_fecha_ultimo_envio()

    fecha_inicio_procesamiento = None

    if ultima_fecha_completada_str:
        try:
            # Convierte la fecha registrada a datetime
            fecha_inicio_procesamiento = datetime.strptime(ultima_fecha_completada_str, '%d/%m/%Y')
            print(f"Última fecha completada registrada: {ultima_fecha_completada_str}.\n")
            fecha_inicio_procesamiento += timedelta(days=1)
        except ValueError:
            print("Formato de la última fecha procesada incorrecto. Iniciando desde una fecha manual.")
            fecha_inicio_procesamiento = None
    else:
        fecha_inicio_procesamiento = None # Si no hay fecha registrada, fuerza la entrada manual

    if fecha_inicio_procesamiento is None:
        # Pide al usuario que ingrese una fecha de inicio si no hay una válida registrada
        while True:
            fecha_str_input = input("Fecha de INICIO para el procesamiento (dd/mm/aaaa): ")
            try:
                fecha_inicio_procesamiento = datetime.strptime(fecha_str_input, '%d/%m/%Y')
                break
            except ValueError:
                print("Formato de fecha incorrecto. Usa dd/mm/aaaa.")

    # Fecha actual del sistema
    hoy_sistema_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    conteos_diarios_historicos = cargar_conteo_diario()
    fecha_actual_sistema_str = datetime.now().strftime('%Y-%m-%d')

    conteo_actual_diario = conteos_diarios_historicos.get(fecha_actual_sistema_str, 0)

    print(f"Conteo diario actual para {fecha_actual_sistema_str}: {conteo_actual_diario} de {LIMITE_DIARIO_CORREOS} permitidos.\n")

    current_date_to_process = fecha_inicio_procesamiento

    interrupted_by_execution_limit = False

    while True:
        fecha_a_procesar_dt = current_date_to_process if current_date_to_process <= hoy_sistema_dt else hoy_sistema_dt
        hoy_str = fecha_a_procesar_dt.strftime('%d/%m/%Y')

        if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
            print(f"Se ha alcanzado el límite de correos permitidos por día ({LIMITE_DIARIO_CORREOS}) para la fecha del sistema {fecha_actual_sistema_str}.\n")
            print(f"El script se detendrá por hoy. Continuará mañana.\n")
            break

        # Conexión a la base de datos
        conexion_base = conectar_bd()
        if conexion_base is None:
            print(f"No se pudo conectar a la base de datos para la fecha {hoy_str}.")
            continue

        cursor = conexion_base.cursor(dictionary=True)

        try:
            # Cargamos los IDs de correos ya enviados para la fecha actual de procesamiento (hoy_str)
            ids_correos_enviados_para_esta_fecha = cargar_correos_enviados_dia(hoy_str)

            # Consulta para contar los correos que cumplen con la restricción
            sql_count_query = """
                SELECT COUNT(*) AS TABLA FROM BASE_DATOS """
            cursor.execute(sql_count_query, (hoy_str,))
            total_registros_bd = cursor.fetchone()['total_registros']
            print(f"La consulta SQL arrojó un total de {total_registros_bd} correos para la fecha {hoy_str}.")

            # Sentencia SQL para obtener los correos pendientes
            sql_query = """
                SELECT elemento de tabla FROM tabla WHERE condición """
            cursor.execute(sql_query, (hoy_str,))
            # Filtrar los ya enviados directamente desde la lista obtenida
            pendientes = [row for row in cursor.fetchall() if row['Ds_Merchant_Order'] not in ids_correos_enviados_para_esta_fecha]

            total_pendientes_reales = len(pendientes)
            if total_pendientes_reales == 0:
                print(f"No hay correos nuevos por enviar en este momento para la fecha {hoy_str}.")
                # Si no hay pendientes y la fecha es anterior al día actual del sistema, la marcamos como "completada"
                if fecha_a_procesar_dt < hoy_sistema_dt:
                    guardar_fecha_ultimo_envio(hoy_str)
                    current_date_to_process += timedelta(days=1)
                    continue
                else: # Es la fecha actual del sistema y no hay pendientes. El script debe terminar.
                    print(f"Todos los correos para el día actual ({hoy_str}) han sido procesados o no hay nuevos pendientes.")
                    print("El script se detendrá y esperará la próxima ejecución del daemon.\n")
                    cursor.close()
                    conexion_base.close()
                    break # SALIDA CRÍTICA: Sale del bucle principal para que el daemon lo reactive.

            # Conexión al servidor SMTP
            server_smtp = conectar_servidor_smtp()
            if server_smtp is None:
                print(f"No se pudo conectar al servidor SMTP. Deteniendo el procesamiento de fechas.")
                interrupted_by_execution_limit = True
                break

            # Enviar correos
            contador_correos_enviados_esta_ejecucion = 0
            for row in pendientes:
                correo_id = row['Ds_Merchant_Order']

                # Verificar el límite diario del sistema antes de enviar
                if conteo_actual_diario >= LIMITE_DIARIO_CORREOS:
                    print(f"Límite diario de correos ({LIMITE_DIARIO_CORREOS}) alcanzado para la fecha del sistema {fecha_actual_sistema_str}.\n")
                    print(f"El script se detendrá por hoy. Continuará mañana.")
                    if server_smtp: server_smtp.quit()
                    interrupted_by_execution_limit = True
                    break

                # Verificar el límite de correos por ejecución
                if contador_correos_enviados_esta_ejecucion >= LIMITE_CORREOS_POR_EJECUCION:
                    print(f"Se alcanzó el límite de {LIMITE_CORREOS_POR_EJECUCION} correos por esta ejecución para la fecha {hoy_str}.\n")
                    print("El demonio se reactivará para continuar con esta misma fecha.")
                    if server_smtp: server_smtp.quit()
                    interrupted_by_execution_limit = True # Marca que se interrumpió por este límite
                    break 

                correo_destino = row['email']

                mensaje = MIMEMultipart('alternative')
                mensaje['From'] = Remitente
                mensaje['To'] = correo_destino
                mensaje['Subject'] = "Asunto del correo a mandar"
                mensaje.attach(MIMEText(cuerpo_html, 'html'))

                try:
                    print(f'Enviando...')
                    server_smtp.sendmail(Remitente, correo_destino, mensaje.as_string())
                    print(f"[{contador_correos_enviados_esta_ejecucion+1}] Mensaje enviado correctamente a {correo_destino}, correo (ID: {correo_id}).\n")

                    # Actualiza el conteo diario (basado en la fecha del SISTEMA)
                    contador_correos_enviados_esta_ejecucion += 1
                    conteo_actual_diario += 1
                    conteos_diarios_historicos[fecha_actual_sistema_str] = conteo_actual_diario
                    guardar_conteo_diario(conteos_diarios_historicos)

                    # Actualiza el registro de IDs enviados para la fecha de procesamiento
                    ids_correos_enviados_para_esta_fecha.add(correo_id)
                    guardar_correos_enviados_dia(hoy_str, ids_correos_enviados_para_esta_fecha)

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
                        interrupted_by_execution_limit = True
                        break 
                    print(f"El correo {correo_destino} (ID: {correo_id}) no se pudo enviar.")
                    pass
                except Exception as e:
                    print(f"Error inesperado al enviar correo a {correo_destino} (ID: {correo_id}): {e}\n")
                    pass

            if server_smtp:
                try:
                    server_smtp.quit()
                    print('Sesión SMTP cerrada para la fecha actual de procesamiento.\n')
                except Exception as e:
                    print(f"Error al cerrar la sesión SMTP para la fecha {hoy_str}: {e}")

            if interrupted_by_execution_limit:
                print(f"El procesamiento para la fecha {hoy_str} se interrumpió. Se reintentará esta fecha en la próxima ejecución.")
                break

            if len(ids_correos_enviados_para_esta_fecha) == total_registros_bd:
                print(f"Todos los correos conocidos para la fecha {hoy_str} han sido procesados.")
                
                if fecha_a_procesar_dt < hoy_sistema_dt:
                    guardar_fecha_ultimo_envio(hoy_str) # Guarda la fecha SOLO si se completó un día ANTERIOR
                    current_date_to_process += timedelta(days=1) # Avanza a la siguiente fecha
                else:
                    print(f"Todos los correos para el día actual ({hoy_str}) han sido procesados. El script esperará nuevos registros.")
                    continue
            else:
                print(f"No se pudieron enviar todos los correos de la fecha {hoy_str}. Se reintentará esta fecha en la próxima ejecución.")
                break

        except Exception as e:
            print(f"Error inesperado al procesar la fecha {hoy_str}: {e}")
            interrupted_by_execution_limit = True
            break
        finally:
            if cursor:
                cursor.close()
            if conexion_base:
                conexion_base.close()
                print(f'Conexión a la base de datos cerrada para la fecha {hoy_str}.')

    print(f"Última fecha completada registrada: {cargar_fecha_ultimo_envio() if cargar_fecha_ultimo_envio() else 'Ninguna fecha completa.'}")
    print(f"Total de correos enviados hoy ({fecha_actual_sistema_str}): {conteos_diarios_historicos.get(fecha_actual_sistema_str, 0)}.\n\n")


if __name__ == "__main__":
    main()
