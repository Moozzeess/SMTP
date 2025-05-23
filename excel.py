import html
import smtplib
import pandas as pd
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTPServerDisconnected

#Configuración del servidor
servidor_smtp = 'smtp.dominio.com'
puerto_smtp = 123
Remitente = 'correo@dominio.org.mx' 
contraseña_remitente = '123456789' 

#Variables globales
LIMITE_Correo=400 #Limite de correos a enviar por ejecución de script
reconexion=100 #Intervalos para que se reconecte el servidor
Max_intentos=3 #Intentos para restablecer la conexion
contador_correos=0 #Contabiliza el número de correos enviados
reintentos_de_conexion=0 #Contabiliza los reintentos

#lectura de la base de datos
df = pd.read_excel('correos.xlsx')
pendientes = df[df['Estatus'] !='Si'] #Comprueba si el correo ha sido enviado dentro de la BD en la columna Estatus

#Abrir el archivo del mensaje directamente
try: #cambiar imagen por mensaje
    with open('nombre_archivo.html', 'r', encoding='utf-8') as archivo_html:
        cuerpo=archivo_html.read()
        print('Se ha cargado correctamente el archivo html')
except Exception as e:
     print('No se ha podido cargar el cuerpo del mensaje')
     exit()   
         
#Autenticación con servidor SMTP
def conexion_servidor():
     try:
        server=smtplib.SMTP(servidor_smtp, puerto_smtp)
        server.starttls()
        server.login(Remitente, contraseña_remitente)
        print('Se ha iniciado sesión correctamente con el servidor\n')
        return server
     except Exception as e:
          print(f"Error al conectar con el servidor: {e}")
          return None

#Inicio del servidor
server=conexion_servidor()
if server is None:
     exit()

#Ciclo para obtener los correos desde el archivo de excel
for index, row in pendientes.tail(LIMITE_Correo).iterrows(): #Cambiar head por tail si se quieren enviar los últimos de la columna
        if contador_correos>=LIMITE_Correo:#condición para no superar los limtes
             print("Se ha alcanzado el limte de correos permitidos por día de la cuenta.")
             break

        correo=row['Correo'] #Valida la columna de correos
        
        #Estructura del mensaje
        mensaje=MIMEMultipart('alternative')
        mensaje['From'] = Remitente
        mensaje['To'] = correo
        mensaje['Subject'] = "Festival del maestro 2025" #CAMBIAR regularmente el asunto para evitar spam

        #Cuerpo del mensaje
        mensaje.attach(MIMEText(cuerpo, 'html'))

        while reintentos_de_conexion<Max_intentos:
            try: #Verificar el envio del mensaje
                print('Enviando ...')
                server.sendmail(Remitente,correo, mensaje.as_string())
                print(f"[{contador_correos+1}]Se ha enviado el mensaje correctamente a {correo}\n")

                df.loc[index, 'Estatus']= 'Si' #Actualiza el valor del Estatus en la DB
                contador_correos += 1
                break
            
            except SMTPServerDisconnected as e: #ERROR DE reconexion
                print(f"Error de conexión SMTP\n Reintentando...")
                server=conexion_servidor()
                if server is None:
                    print('No se a podido reconectar al servidor')
                    break
                reintentos_de_conexion+=1
                time.sleep(5) #Pausa de espera de REconexion
                
            except Exception as e: #Manda el tipo de error en la DB
                print(f"Error al enviar el correo al destinatario {correo} {e}\n")
                df.loc[index, 'Estatus']= 'Error: Correo no válido'
                break

        if server is None:
            break
        
        time.sleep(1.25) #Pausa de 1.5 segundos al enviar un correo

        #Reconexion periodica
        if contador_correos % reconexion ==0 and contador_correos>0:
             print(f"Reconectando servidor. Correos enviados:{contador_correos}")
             try:
                server.quit()
             except Exception:
                 pass
             server=conexion_servidor()
             if server is None: #En caso de no reconectarse termina el programa
                 break

#Cerrar sesión con el servidor
if server:
    try:
        server.quit()
        print('Se ha cerrado sesión del servidor')
    except Exception as e:
        print(f"Error. No se ha podido cerrar la conexión del servidor. {e}")

df.to_excel('correos.xlsx', index=False) #Actualiza el estado del archivo de los correos
print(f"Se han enviado {contador_correos} correos en esta ejecución\n")
