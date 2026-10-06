import os
import random
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, InvalidArgumentException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ElementoNoEncontrado(Exception):
	pass


class Navegador:
	# Tiempo máximo que esperamos a que cargue un elemento
	espera_elemento = 30

	def __init__(self, carpeta_perfil):
		# Usamos un perfil de Chrome propio: la sesión de Facebook se mantiene entre ejecuciones
		opciones = Options()
		opciones.add_argument("--user-data-dir=" + os.path.abspath(carpeta_perfil))
		opciones.add_argument("--disable-blink-features=AutomationControlled")
		opciones.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
		opciones.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})

		# Selenium 4.11+ descarga el driver de Chrome automáticamente
		self.driver = webdriver.Chrome(options=opciones)
		self.driver.maximize_window()

	def cerrar(self):
		try:
			self.driver.quit()
		except Exception:
			pass

	# --- Sesión ---

	def asegurar_sesion(self, url):
		self.ir(url)
		if self.sesion_iniciada(8):
			return

		print("Inicia sesión en Facebook en la ventana de Chrome. Tienes 5 minutos.")
		if not self.sesion_iniciada(300):
			raise SystemExit("No se inició sesión a tiempo.")
		print("Sesión iniciada. La próxima vez entrarás automáticamente.")

	def sesion_iniciada(self, segundos):
		# Con sesión iniciada no hay formulario de contraseña y aparece la barra superior
		fin = time.time() + segundos
		while time.time() < fin:
			hay_login = self.driver.find_elements(By.CSS_SELECTOR, 'input[name="pass"]')
			hay_barra = self.driver.find_elements(By.CSS_SELECTOR, '[role="banner"]')
			if hay_barra and not hay_login:
				return True
			time.sleep(1)
		return False

	# --- Utilidades ---

	def pausa(self, minimo=0.2, maximo=1.2):
		time.sleep(round(random.uniform(minimo, maximo), 2))

	def ir(self, url):
		self.pausa()
		self.driver.get(url)

	def buscar(self, xpath, obligatorio=True, segundos=None):
		if segundos is None:
			segundos = self.espera_elemento
		try:
			return WebDriverWait(self.driver, segundos).until(EC.element_to_be_clickable((By.XPATH, xpath)))
		except Exception:
			if obligatorio:
				raise ElementoNoEncontrado('No se encontró el elemento: ' + xpath)
			return None

	def _clic_elemento(self, elemento):
		try:
			elemento.click()
		except ElementClickInterceptedException:
			self.driver.execute_script("arguments[0].click();", elemento)

	def clic(self, xpath, obligatorio=True, segundos=None):
		self.pausa()
		elemento = self.buscar(xpath, obligatorio, segundos)
		if elemento is not None:
			self._clic_elemento(elemento)
		return elemento

	def escribir(self, xpath, texto, obligatorio=True, segundos=None):
		self.pausa()
		elemento = self.buscar(xpath, obligatorio, segundos)
		if elemento is None:
			return None
		self._clic_elemento(elemento)
		elemento.send_keys(solo_bmp(texto))
		return elemento

	def borrar_texto(self, xpath):
		self.pausa()
		elemento = self.buscar(xpath)
		tecla = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
		elemento.send_keys(tecla + "a")
		elemento.send_keys(Keys.BACK_SPACE)

	def esperar_invisible(self, xpath, segundos=None):
		if segundos is None:
			segundos = self.espera_elemento
		try:
			WebDriverWait(self.driver, segundos).until(EC.invisibility_of_element_located((By.XPATH, xpath)))
		except Exception:
			print("Aviso: el elemento sigue visible: " + xpath)

	def desplazar_a(self, xpath):
		elemento = self.buscar(xpath)
		self.driver.execute_script("arguments[0].scrollIntoView(true);", elemento)

	def subir_archivos(self, selector_css, rutas):
		try:
			entrada = WebDriverWait(self.driver, self.espera_elemento).until(
				EC.presence_of_element_located((By.CSS_SELECTOR, selector_css)))
		except Exception:
			raise ElementoNoEncontrado("No se encontró el campo para subir fotos")
		self.pausa()
		try:
			entrada.send_keys("\n".join(rutas))
		except InvalidArgumentException:
			raise ElementoNoEncontrado("Revisa las rutas de las fotos:\n" + "\n".join(rutas))


def solo_bmp(texto):
	# ChromeDriver no puede escribir emojis ni otros caracteres fuera del plano básico
	return "".join(c for c in texto if ord(c) <= 0xFFFF)
