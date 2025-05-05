# Generador de Certificados SSL Let's Encrypt con Cloudflare

> **⚠️ AVISO IMPORTANTE**: Esta funcionalidad se encuentra todavía en versión alpha y no es estable para uso en producción. Se recomienda utilizar solo en entornos de prueba hasta que se publique una versión estable.

## Introducción

Los certificados SSL son esenciales para garantizar conexiones seguras en sitios web. Let's Encrypt ofrece certificados gratuitos, pero su renovación puede ser compleja, especialmente cuando se necesita validar múltiples dominios o subdominios.

La validación por desafío DNS es un método que permite verificar la propiedad de un dominio mediante la creación de registros TXT específicos en la configuración DNS. Este método es especialmente útil cuando:
- Necesitas certificados wildcard (*.tudominio.com)
- El servidor web no es accesible públicamente
- Tienes que validar múltiples dominios simultáneamente

### Ventajas de usar la API de Cloudflare

Cloudflare proporciona una API que permite automatizar completamente este proceso:
1. No requiere acceso manual al panel de control
2. Permite la creación y eliminación automática de registros DNS
3. Es ideal para scripts de renovación automática
4. Funciona con certificados wildcard y múltiples dominios

Este script simplifica todo el proceso utilizando la API de Cloudflare para:
- Gestionar automáticamente los registros DNS necesarios
- Generar y renovar certificados
- Mantener copias de seguridad
- Monitorizar fechas de expiración

## Instalación de los requerimientos 

```bash
sudo apt-get update
sudo apt-get install certbot
pip install certbot-dns-cloudflare
```

## Configuración de Cloudflare

1. Crear un token de API de Cloudflare:
   - Inicia sesión en tu [panel de Cloudflare](https://dash.cloudflare.com/)
   - Ve a "Mi Perfil" > "Tokens de API" > "Crear Token"
   - Selecciona "Plantilla de permisos específicos"
   - Agrega permisos "Zona:DNS:Edit"
   - Limita el acceso a las zonas específicas donde necesites los certificados
   - Crea el token y guárdalo de forma segura

2. Crear archivo de configuración `config.yml`:
```yaml
cloudflare:
  api_token: tu_token_api_cloudflare
email: tu_email@ejemplo.com
domains:
  - ejemplo1.com
  - ejemplo2.com
dest_path: /ruta/para/certificados
output_dir: /ruta/de/salida
```

## Ejecución individual de certbot con la API de Cloudflare 

```bash
certbot certonly \
  --authenticator dns-cloudflare \
  --dns-cloudflare-credentials cloudflare.ini \
  --dns-cloudflare-propagation-seconds 60 \
  -d example.com \
  -d *.example.com
```  

## Referencias 

- [Documentación oficial del plugin certbot-dns-cloudflare](https://certbot-dns-cloudflare.readthedocs.io/)
- [API de Cloudflare](https://developers.cloudflare.com/api/)
- [Creación de tokens de API en Cloudflare](https://developers.cloudflare.com/api/tokens/create/)

## Uso del Script ssl-wildcard-cloudflare.py

### Requisitos previos
```bash
sudo apt update
sudo apt install python3 python3-pip
```

### Instalación

1. Clonar el repositorio:
```bash
git clone <url-repositorio>
cd <directorio-repositorio>
```

2. Instalar dependencias:
```bash
pip install requests pyyaml certbot-dns-cloudflare
```

### Opciones del script

```bash
python ssl-wildcard-cloudflare.py --help
```

Muestra las siguientes opciones:
- `--init`: Genera un archivo config.yml de ejemplo
- `--install`: Instala certbot y el plugin de Cloudflare
- `--generate`: Genera los certificados
- `--copy`: Copia los certificados a la ruta de destino
- `--renew`: Renueva los certificados próximos a expirar
- `--config`: Especifica ruta al archivo de configuración YAML

### Configuración

El script requiere un archivo `config.yml` con la siguiente estructura:
```yaml
cloudflare:
  api_token: tu_token_api_cloudflare
email: tu_email@ejemplo.com
domains:
  - ejemplo1.com
  - ejemplo2.com
dest_path: /ruta/para/certificados
output_dir: /ruta/de/salida
```

### Uso del script

1. Crear un archivo de configuración de ejemplo:
```bash
python ssl-wildcard-cloudflare.py --init
```

2. Instalar certbot y el plugin de Cloudflare:
```bash
python ssl-wildcard-cloudflare.py --install
```

3. Generar nuevos certificados:
```bash
python ssl-wildcard-cloudflare.py --generate
```

4. Renovar certificados existentes:
```bash
python ssl-wildcard-cloudflare.py --renew
```

5. Usar un archivo de configuración específico:
```bash
python ssl-wildcard-cloudflare.py --config /ruta/a/config.yml --generate
```

6. Copiar certificados a la ruta de destino:
```bash
python ssl-wildcard-cloudflare.py --copy
```

### Sistema de Respaldo

El script incluye un sistema automático de respaldo que:
- Crea copias de seguridad antes de renovar o generar certificados
- Almacena los respaldos en `dest_path/backups/` con marca de tiempo
- Mantiene los permisos originales de los archivos

Estructura de directorios de respaldo:
```
/ruta/certificados/
    ├── backups/
    │   ├── 20240315_143022/
    │   │   ├── ejemplo1.com.cert.pem
    │   │   ├── ejemplo1.com.chain.pem
    │   │   ├── ejemplo1.com.fullchain.pem
    │   │   └── ejemplo1.com.key
    │   └── ...
    ├── ejemplo1.com.cert.pem
    ├── ejemplo1.com.chain.pem
    ├── ejemplo1.com.fullchain.pem
    └── ejemplo1.com.key
```

