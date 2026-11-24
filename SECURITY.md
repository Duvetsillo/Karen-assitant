# Seguridad

No publiques vulnerabilidades con tokens o datos de conversaciones. Utiliza
GitHub Private Vulnerability Reporting cuando esté habilitado; si no está
disponible, contacta al mantenedor mediante los canales de su perfil sin adjuntar
secretos hasta acordar un canal privado.

El Gateway posee la capacidad de actuar sobre el sistema. Un usuario autenticado
en Karen puede conversar y ejecutar órdenes con los permisos de ese agente.
Despliega una instancia por grupo de confianza: no es un servicio multiusuario
con separación de agentes, cuentas o conversaciones.

El servidor exige un token de acceso independiente del token de OpenClaw, cookies
HttpOnly/SameSite=Strict, validación del origen y cabecera de cliente en las
mutaciones. En producción requiere HTTPS con un proxy de confianza. No publiques
directamente los puertos de OpenClaw ni desactives su autenticación.

El volumen de datos contiene la identidad privada cifrada y su clave. Cifra el
disco y protege el directorio y sus copias: quien lea todo el volumen también
puede leer la clave. El cifrado de un archivo no aísla al administrador del host.

No subas `.env`, `secrets/`, `data/`, archivos de OpenClaw, claves, audio, perfiles
de prueba ni credenciales cifradas. Si un secreto se publica, revócalo y rótalo;
borrarlo en un commit posterior no lo elimina del historial.
