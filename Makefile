# Variables
PYTHON = python3
PIP = pip3
PYINSTALLER = pyinstaller
APP_NAME = ssl-wildcard-cloudflare
MAIN_SCRIPT = ssl-wildcard-cloudflare.py
DIST_DIR = dist
BUILD_DIR = build

# Colores para mensajes
GREEN = \033[0;32m
NC = \033[0m  # No Color

.PHONY: all clean install build run requirements

all: clean requirements build

# Instalar dependencias
requirements:
	@echo "$(GREEN)Instalando dependencias...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install pyinstaller

# Construir el ejecutable
build:
	@echo "$(GREEN)Construyendo ejecutable...$(NC)"
	$(PYINSTALLER) --onefile \
		--name $(APP_NAME) \
		--clean \
		--add-data "config.yml:." \
		$(MAIN_SCRIPT)
	@echo "$(GREEN)Ejecutable creado en $(DIST_DIR)/$(APP_NAME)$(NC)"

# Construir en modo debug
build-debug:
	@echo "$(GREEN)Construyendo ejecutable en modo debug...$(NC)"
	$(PYINSTALLER) --onefile \
		--name $(APP_NAME) \
		--clean \
		--debug=all \
		--add-data "config.yml:." \
		$(MAIN_SCRIPT)

# Limpiar archivos generados
clean:
	@echo "$(GREEN)Limpiando archivos generados...$(NC)"
	rm -rf $(BUILD_DIR) $(DIST_DIR) *.spec

# Ejecutar el programa compilado
run:
	@echo "$(GREEN)Ejecutando $(APP_NAME)...$(NC)"
	./$(DIST_DIR)/$(APP_NAME)

# Instalar el ejecutable en el sistema (requiere sudo)
install:
	@echo "$(GREEN)Instalando $(APP_NAME) en el sistema...$(NC)"
	sudo cp $(DIST_DIR)/$(APP_NAME) /usr/local/bin/
	@echo "$(GREEN)Instalación completada$(NC)" 