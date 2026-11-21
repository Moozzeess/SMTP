# SMTP
Enviar de forma masiva correos electrónicos, por proceso deamon y manual. En el proceso deamon se conecta con una base de datos en mysql, y genera un archivo jason para su control. 
Por otro lado, el envío de forma manual se lleva acabo mediante una base de datos de un archivo excel y este requiere tener control humano.

## Considerar
Tener todos los archivos en la misma carperta, salvo el timer y service comunmente se guardan en /etc/systemd/system.
Los archivos son: cuerpo del mensaje (plantilla HTML o texto plano), destinatarios (correos.xsl), script_de_python.py

## excel.py
Script simple para ejecutar el envío de correos mediante archivo de Excel donde almacena los correos a enviar mediante una plantilla HTML o texto plano. El archivo debe tener los encabezados mínimos para su lectura: Nombre, Correo/email.

## query_manual.py
El script funciona con conexión a una base de datos, con la posibilidad de agregar la fecha de envío mediante la consola o terminal de ejecución.

## deamon_correo.py
Se ejecuta sin restricciones en la base de datos, por decir, se puede agregar una columna de Estatus, manipuilar sentencias, etc.

## query_automatizado.py
Lleva un manejo más complicado, utiliza archivos JSON para cuando hay restricciones en la base de datos con ciertos filtros para contabilizar los ID, los días que se enviaron y un conteo de cuantos se enviaron al día. Este script maneja banderas ante fallas como en la base de datos, perdida de conexión, interrupción del sistema , limite excedido de correos enviados.

# Para ejecutar como deamon (query_automatizado.py o deamon_correos.py) se requiere 
1. Conexión con mysql
2. Linux
3. python (instalar libreria import mysql.connector)


# Comandos en linux para ejecutarse el deamon

### 1. Recargar los deamon
``` 
sudo systemctl daemon-reload
```

### 2. Habilitar service y timer
```
 sudo systemctl enable signal_correos.timer
 sudo systemctl enable signal_correos.service
```

### 3. Iniciar deamon
```
sudo systemctl start signal_correos.timer
sudo systemctl start signal_correos.service // solo si no requiere timer
```
### 4. Mostrar estatus de deamon
```
sudo systemctl status signal_correos.timer
sudo systemctl status signal_correos.service
```
### 5. Comprobar errores del service
```
journalctl -u signal_correos.service -f
```

### 6. Detener deamon. Recomendación detener timer si se activo este.
```
sudo systemctl stop signal_correos.timer
sudo systemctl stop signal_correos.service
```

### Deshabilitar procesos deamon
```
sudo systemctl disable signal_correos.timer
sudo systemctl disable signal_correos.service
```

### Verificar el archivo de conteo diario
```
cat /home/Correos/conteo_correos_diario.json
cat /home/Correos/fecha_ultimo_envio.json
```
### Ver el contenido de un archivo, en este caso las interaciónes que ha tenido como prints y errores
```
tail -f /var/log/signal_correos.log
```
