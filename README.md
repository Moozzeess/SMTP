# SMTP
Enviar de forma masiva correos electrónicos, por proceso deamon y manual. En el proceso deamon se conecta con una base de datos en mysql, y genera un archivo jason para su control. 
Por otro lado, el envío de forma manual se lleva acabo mediante una base de datos de un archivo excel y este requiere tener control humano.

Considerar
tenerlos todos los archivos en la misma carperta, salvo el timer y service comunmente se guardan en /etc/systemd/system

Para ejecutar como solo mandar archivos de excel (excel.py)
solo tenerlos en la misma carperta, y controlar manualmente los correos en archivo correos.xsl

Si se quiere ejecutar que el usuario ponga la fecha en la consola se ejecuta el script: query_manual.py

Hay una diferencia entre deamon_correos y query_automatizado: Uno se ejecuta sin restricciones en la base de datos, por decir, se puede agregar una columna de Estatus, manipuilar sentencias, etc.
El query_automatizado.py lleva un manejo más complicado, utilza archivos jason para cuando hay restricciones en la base de datos con ciertos filtros para contabilizar los ID, los días que se enviaron yun conteo de cuantos se envíaron. 

Para ejecutar como deamon (query_automatizado.py o deamon_correos.py) se requiere 
1. Conexión con mysql
2. Linux
3. python (instalar libreria import mysql.connector)


Comandos en linux para ejecutarse el deamon


//1. Sirve para recargar los deamon
sudo systemctl daemon-reload 

//2. Habilitar service y timer
sudo systemctl enable signal_correos.timer
sudo systemctl enable signal_correos.service

//3. iniciar deamon
sudo systemctl start signal_correos.timer
sudo systemctl start signal_correos.service // solo si no requiere timer

//4. Mostrar estatus de deamon
sudo systemctl status signal_correos.timer
sudo systemctl status signal_correos.service

//5. Comprobar errores del service
journalctl -u signal_correos.service -f

//6. Detener deamon. Recomendación detener timer si se activo este.
sudo systemctl stop signal_correos.timer
sudo systemctl stop signal_correos.service

//Deshabilitar procesos deamon
sudo systemctl disable signal_correos.timer
sudo systemctl disable signal_correos.service

//Verificar el archivo de conteo diario
cat /home/ss/Correos/conteo_correos_diario.json
cat /home/ss/Correos/fecha_ultimo_envio.json

//permite ver el contenido de un archivo, en este caso las interaciónes que ha tenido como prints y errores
tail -f /var/log/signal_correos.log
