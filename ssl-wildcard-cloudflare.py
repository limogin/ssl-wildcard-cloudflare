#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import yaml
import time
import subprocess
import argparse
import os

# ====================================================================
# Script para generar certificados SSL wildcard usando Let's Encrypt
# con autenticación DNS a través de Cloudflare
#
# Requisitos:
#  - sudo apt-get install certbot
#  - pip install requests pyyaml certbot-dns-cloudflare
#
# Configuración:
#  1. Crea un token de API en Cloudflare con permisos de Zona:DNS:Edit
#     en https://dash.cloudflare.com/profile/api-tokens
#  2. Crea un archivo config.yml con la siguiente estructura:
#     cloudflare:
#       api_token: tu_token_api_cloudflare
#     email: tu_email@ejemplo.com
#     domains:
#       - example.com
#       - otro-dominio.com
#     dest_path: /ruta/para/certificados
#     output_dir: /ruta/salida
#
# Uso:
#  - Generar archivo de configuración: python ssl-wildcard-cloudflare.py --init
#  - Instalar certbot y plugin: python ssl-wildcard-cloudflare.py --install
#  - Generar certificados: python ssl-wildcard-cloudflare.py --generate
#  - Copiar certificados: python ssl-wildcard-cloudflare.py --copy
#  - Renovar certificados: python ssl-wildcard-cloudflare.py --renew
# ====================================================================

class SslWildcardCloudflare:
    
    def __init__(self):
        self.verbose = False

    def load_config(self, config_file):
        self.cfg = self.load_config_file(config_file)
        self.api_token = self.cfg['cloudflare']['api_token']
        self.output_dir = self.cfg['output_dir']
        self.email = self.cfg['email']
        self.domains = self.cfg['domains']
        
    def load_config_file(self, fn):
        with open(fn, 'r') as content:
            return yaml.safe_load(content)

    def save_cloudflare_ini(self):        
        """Genera el archivo de credenciales para el plugin dns-cloudflare de certbot"""
        dst_fn = 'cloudflare.ini' 
        with open(dst_fn, 'w') as f:
            f.write(f'dns_cloudflare_api_token = {self.api_token}\n')
        os.chmod(dst_fn, 0o600)  # Establecer permisos restrictivos por seguridad
        return dst_fn
    
    def install_certbot(self):
        """Instala certbot y el plugin para autenticación DNS con Cloudflare"""
        subprocess.run(["apt-get", "install", "certbot"])   
        subprocess.run(["pip", "install", "certbot-dns-cloudflare"])
    
    def generate_certs(self):
        """Genera certificados para todos los dominios configurados"""
        print("Iniciando generación de certificados...")
        cloudflare_ini = self.save_cloudflare_ini()
        print("Archivo de credenciales de Cloudflare creado")
        
        try:
            # Crear respaldo antes de generar nuevos certificados
            for domain in self.domains:
                print(f"Creando respaldo para {domain}")
                self.backup_certs(domain)
            print("Iniciando proceso de certificación con certbot...")
            self.certbot()
            print("Proceso de generación de certificados completado")
        finally:
            # Asegurarse de eliminar el archivo cloudflare.ini al finalizar
            if os.path.exists(cloudflare_ini):
                os.remove(cloudflare_ini)
                self.log("Archivo cloudflare.ini eliminado")

    def log(self, message):
        """Muestra mensajes solo si verbose está activo"""
        if self.verbose:
            print(message)

    def certbot(self):
        """Ejecuta certbot para obtener o renovar certificados"""
        for domain in self.domains:
            self.log(f"\nProcesando dominio: {domain}")
            # Verificar si el certificado existe
            self.log(f"Verificando certificado existente para {domain}")
            check_command = ["certbot", "certificates", "-d", domain]
            result = subprocess.run(check_command, capture_output=True, text=True)
            self.log(f"Salida de verificación: {result.stdout}")
            
            if "No certificates found" in result.stdout:
                print(f"No se encontró certificado para {domain}, solicitando uno nuevo...")
                # Si no existe el certificado, solicitar uno nuevo
                command = [
                    "certbot", "certonly",
                    "--preferred-challenges", "dns",
                    "--server", "https://acme-v02.api.letsencrypt.org/directory",
                    "--dns-cloudflare",
                    "--dns-cloudflare-credentials", "cloudflare.ini",
                    "--dns-cloudflare-propagation-seconds", "60",
                    "-d", domain, "-d", f"*.{domain}",
                    "--email", self.email, "--agree-tos", "--non-interactive"
                ]
                self.log(f"Ejecutando comando: {' '.join(command)}")
                subprocess.run(command)
                print(f"Proceso completado para {domain}")
            else:
                if not self.check_cert_expiry(domain):
                    print(f"Certificado encontrado para {domain}, verificando expiración...")
                    print(f"El certificado necesita renovación, procediendo...")
                    # Si existe el certificado, renovar usando certonly
                    command = [
                        "certbot", "certonly",
                        "--preferred-challenges", "dns",
                        "--server", "https://acme-v02.api.letsencrypt.org/directory",
                        "--dns-cloudflare",
                        "--dns-cloudflare-credentials", "cloudflare.ini",
                        "--dns-cloudflare-propagation-seconds", "60",
                        "-d", domain, "-d", f"*.{domain}",
                        "--force-renewal"
                    ]
                    self.log(f"Ejecutando comando: {' '.join(command)}")
                    subprocess.run(command)
                    print(f"Proceso completado para {domain}")
                else:
                    print(f"El certificado para {domain} aún no necesita renovación")

    def check_cert_expiry(self, domain):
        """Verifica si un certificado existente necesita renovación
        Retorna True si el certificado necesita ser renovado (menos de 30 días para expirar)"""
        self.log(f"Verificando fecha de expiración para {domain}")
        # Obtiene información del certificado usando certbot certificates
        command = ["certbot", "certificates", "-d", domain]
        result = subprocess.run(command, capture_output=True, text=True)
        self.log(f"Salida de verificación de expiración: {result.stdout}")
        
        if "No certificates found" in result.stdout:
            self.log(f"No se encontró certificado para {domain}")
            return False  # No necesita renovación si no existe certificado
            
        # Busca la fecha de expiración en la salida
        for line in result.stdout.split('\n'):
            if "Expiry Date:" in line:
                # Extrae la fecha en formato YYYY-MM-DD
                expiry_str = line.split("Expiry Date:")[1].strip().split(" ")[0]
                expiry_time = time.strptime(expiry_str, "%Y-%m-%d")
                current_time = time.localtime()
                
                # Calcula días hasta expiración
                days_until_expiry = (time.mktime(expiry_time) - time.mktime(current_time)) / (60 * 60 * 24)
                
                self.log(f"Días hasta expiración: {int(days_until_expiry)}")
                # Renueva si expira en menos de 30 días
                return days_until_expiry < 30
        
        self.log(f"No se pudo determinar la fecha de expiración para {domain}")
        return False  # No necesita renovación si no puede determinar la fecha

    def backup_certs(self, domain):
        """Crea un respaldo de los certificados existentes."""
        backup_dir = os.path.join(self.cfg['dest_path'], 'backups', time.strftime('%Y%m%d_%H%M%S'))
        try:
            os.makedirs(backup_dir, exist_ok=True)
            cert_files = [
                ('cert.pem', f'{domain}.cert.pem'),
                ('chain.pem', f'{domain}.chain.pem'),
                ('fullchain.pem', f'{domain}.fullchain.pem'),
                ('privkey.pem', f'{domain}.key')
            ]
            
            for src_name, dst_name in cert_files:
                src_path = f"/etc/letsencrypt/live/{domain}/{src_name}"
                dst_path = os.path.join(backup_dir, dst_name)
                
                if os.path.exists(src_path):
                    subprocess.run(['cp', '-L', src_path, dst_path], check=True)
                    self.log(f"Respaldo creado: {dst_path}")
            return True
        except Exception as e:
            print(f"Error creando respaldo para {domain}: {str(e)}")
            return False

    def renew_certs(self):
        """Renueva certificados que están próximos a expirar"""
        cloudflare_ini = self.save_cloudflare_ini()
        try:
            for domain in self.domains:
                if self.check_cert_expiry(domain):
                    print(f"Renovando certificado para {domain}")
                    # Crear respaldo antes de renovar
                    if self.backup_certs(domain):
                        command = [
                            "certbot", "certonly",
                            "--preferred-challenges", "dns",
                            "--server", "https://acme-v02.api.letsencrypt.org/directory",
                            "--dns-cloudflare",
                            "--dns-cloudflare-credentials", "cloudflare.ini",
                            "--dns-cloudflare-propagation-seconds", "60",
                            "-d", domain, "-d", f"*.{domain}",
                            "--force-renewal"
                        ]
                        try:
                            self.log(f"Ejecutando comando: {' '.join(command)}")
                            subprocess.run(command, check=True)
                            print(f"Certificado renovado exitosamente para {domain}")
                        except subprocess.CalledProcessError as e:
                            print(f"Error renovando certificado para {domain}: {str(e)}")
                    else:
                        print(f"No se pudo crear respaldo para {domain}, saltando renovación")
                else:
                    print(f"El certificado para {domain} aún no necesita renovación")
        finally:
            # Asegurarse de eliminar el archivo cloudflare.ini al finalizar
            if os.path.exists(cloudflare_ini):
                os.remove(cloudflare_ini)
                self.log("Archivo cloudflare.ini eliminado")

    def init_config_file(self): 
        """Genera un archivo config.yml de ejemplo"""                 
        with open('config.yml', 'w') as f:
            f.write(f'cloudflare:\n')
            f.write(f'  api_token: tu_api_token_de_cloudflare\n')
            f.write(f'email: tu_email@example.com\n')
            f.write(f'domains:\n')
            f.write(f'  - example.com\n')
            f.write(f'  - otro-dominio.com\n')
            f.write(f'dest_path: /ruta/para/guardar/certificados\n')
            f.write(f'output_dir: /ruta/de/salida\n')

    def copy_certs(self):
        """Copia los certificados generados a la ruta de destino configurada"""
        if not os.path.exists(self.cfg['dest_path']):
            os.makedirs(self.cfg['dest_path'])
            
        for domain in self.domains:
            try:
                # Usar los enlaces simbólicos en /etc/letsencrypt/live/
                cmds = [ 
                    f"cp -L /etc/letsencrypt/live/{domain}/cert.pem {self.cfg['dest_path']}/{domain}.cert.pem",
                    f"cp -L /etc/letsencrypt/live/{domain}/chain.pem {self.cfg['dest_path']}/{domain}.chain.pem",
                    f"cp -L /etc/letsencrypt/live/{domain}/fullchain.pem {self.cfg['dest_path']}/{domain}.fullchain.pem",
                    f"cp -L /etc/letsencrypt/live/{domain}/privkey.pem {self.cfg['dest_path']}/{domain}.key"
                ]
                for cmd in cmds:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"Error copiando certificados para {domain}: {result.stderr}")
                    else:
                        self.log(f"Certificado copiado exitosamente: {cmd.split()[-1]}")
            except Exception as e:
                print(f"Error procesando certificados para {domain}: {str(e)}")
    
    @staticmethod
    def parse_arguments():
        """Analiza los argumentos de línea de comandos"""
        parser = argparse.ArgumentParser(description="Generador de certificados SSL wildcard usando Let's Encrypt con autenticación DNS a través de Cloudflare")
        parser.add_argument("--config", 
                        help="Ruta al archivo de configuración YAML", 
                        default="config.yml")
        parser.add_argument("--install", 
                        help="Instala certbot y el plugin de Cloudflare", 
                        action="store_true")
        parser.add_argument("--generate", 
                        help="Genera los certificados", 
                        action="store_true")
        parser.add_argument("--copy", 
                        help="Copia los certificados", 
                        action="store_true")
        parser.add_argument("--renew", 
                        help="Renueva los certificados", 
                        action="store_true")
        parser.add_argument("--init", 
                        help="Genera un archivo config.yml de ejemplo", 
                        action="store_true")
        parser.add_argument("--verbose", 
                        help="Muestra información detallada de la ejecución", 
                        action="store_true")
        return parser.parse_args()
    
    def run(self):
        """Ejecuta las acciones según los argumentos proporcionados"""
        args = self.parse_arguments()
        
        # Si no hay argumentos o se usa --help, mostrar ayuda
        if len(vars(args)) == 1:
            self.parse_arguments().print_help()
            return
        
        self.verbose = args.verbose
        config_file = args.config
        self.load_config(config_file)
            
        if args.install:
            self.install_certbot()
        if args.generate:
            self.generate_certs()
        if args.copy:
            self.copy_certs()  
        if args.renew:
            self.renew_certs()
        if args.init:
            self.init_config_file()


if __name__ == "__main__":
    ssl = SslWildcardCloudflare()
    ssl.run()
