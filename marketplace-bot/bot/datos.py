import csv
import json
import os
import re
import shutil
import unicodedata
from datetime import datetime

CARPETA_CSVS = "csvs"
CARPETA_DATOS = "datos"
ARCHIVO_ESTADO = os.path.join(CARPETA_DATOS, "estado.json")
ARCHIVO_REGISTRO = os.path.join(CARPETA_DATOS, "registro.csv")

ARCHIVOS = {"articulo": "articulos.csv", "vehiculo": "vehiculos.csv"}

COLUMNAS_OBLIGATORIAS = {
	"articulo": ["ID", "Titulo", "Precio", "Precio minimo", "Categoria", "Estado", "Descripcion", "Ubicacion", "Carpeta fotos", "Fotos"],
	"vehiculo": ["ID", "Tipo de vehiculo", "Año", "Marca", "Modelo", "Kilometraje", "Combustible", "Precio", "Precio minimo", "Descripcion", "Ubicacion", "Carpeta fotos", "Fotos"],
}


def normalizar(texto):
	# "Precio mínimo " -> "precio minimo" para que las mayúsculas y tildes no importen
	texto = unicodedata.normalize("NFKD", texto.strip().lower())
	return "".join(c for c in texto if not unicodedata.combining(c))


class Anuncio:
	"""Una fila del CSV. Se accede a las columnas sin importar tildes ni mayúsculas."""

	def __init__(self, tipo, fila):
		self.tipo = tipo
		self.fila = fila
		self._claves = {normalizar(k): k for k in fila if k is not None}

	def __getitem__(self, columna):
		clave = self._claves.get(normalizar(columna))
		valor = self.fila.get(clave) if clave else None
		return (valor or "").strip()

	def __setitem__(self, columna, valor):
		clave = self._claves.get(normalizar(columna))
		if clave is None:
			clave = columna
			self._claves[normalizar(columna)] = clave
		self.fila[clave] = valor

	@property
	def id(self):
		return self["ID"]

	@property
	def titulo(self):
		"""Título con el que se publica en Facebook."""
		if self.tipo == "vehiculo":
			# Facebook genera el título de los vehículos con año, marca y modelo
			return " ".join(p for p in [self["Año"], self["Marca"], self["Modelo"]] if p)
		return self["Titulo mejorado"] or self["Titulo"]

	@property
	def descripcion(self):
		return self["Descripcion mejorada"] or self["Descripcion"]

	@property
	def precio(self):
		return a_numero(self["Precio"])

	@property
	def precio_minimo(self):
		return a_numero(self["Precio minimo"])

	@property
	def grupos(self):
		return separar(self["Grupos"])

	@property
	def rutas_fotos(self):
		carpeta = os.path.expanduser(self["Carpeta fotos"])
		return [os.path.abspath(os.path.join(carpeta, foto)) for foto in separar(self["Fotos"])]


def separar(texto):
	return [p.strip() for p in re.split(r"[;|]", texto or "") if p.strip()]


def a_numero(texto):
	"""'25.000' -> 25000, '1,250.50' -> 1250.5, '' -> None"""
	if texto is None:
		return None
	limpio = re.sub(r"[^\d.,]", "", str(texto))
	if not limpio:
		return None
	# Puntos o comas seguidos de 3 dígitos son separadores de miles
	limpio = re.sub(r"[.,](?=\d{3}(\D|$))", "", limpio)
	limpio = limpio.replace(",", ".")
	try:
		valor = float(limpio)
	except ValueError:
		return None
	return int(valor) if valor.is_integer() else valor


# --- Lectura y escritura de CSV ---

def _leer_texto(ruta):
	# Excel en español suele guardar en cp1252; probamos UTF-8 primero
	for codificacion in ("utf-8-sig", "cp1252"):
		try:
			with open(ruta, encoding=codificacion) as archivo:
				return archivo.read()
		except UnicodeDecodeError:
			continue
	raise ValueError("No se pudo leer " + ruta)


def _separador(texto):
	# Excel en español separa con ";" en vez de ","
	primera_linea = texto.splitlines()[0] if texto else ""
	return ";" if primera_linea.count(";") > primera_linea.count(",") else ","


def leer_anuncios(tipo):
	ruta = os.path.join(CARPETA_CSVS, ARCHIVOS[tipo])
	if not os.path.exists(ruta):
		return [], ruta, ","
	texto = _leer_texto(ruta)
	separador = _separador(texto)
	filas = csv.DictReader(texto.splitlines(), delimiter=separador)
	anuncios = [Anuncio(tipo, fila) for fila in filas if any((v or "").strip() for v in fila.values() if isinstance(v, str))]
	return anuncios, ruta, separador


def guardar_anuncios(tipo, anuncios, ruta, separador):
	# Copia de seguridad antes de sobrescribir
	if os.path.exists(ruta):
		shutil.copyfile(ruta, ruta + ".bak")

	columnas = []
	for anuncio in anuncios:
		for columna in anuncio.fila:
			if columna is not None and columna not in columnas:
				columnas.append(columna)

	with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
		escritor = csv.DictWriter(archivo, fieldnames=columnas, delimiter=separador, extrasaction="ignore")
		escritor.writeheader()
		for anuncio in anuncios:
			escritor.writerow({c: anuncio.fila.get(c, "") for c in columnas})


def validar(tipo, anuncios):
	"""Devuelve una lista de errores legibles. Lista vacía = todo bien."""
	errores = []
	ids = set()

	if anuncios:
		columnas = {normalizar(c) for c in anuncios[0].fila if c}
		for columna in COLUMNAS_OBLIGATORIAS[tipo]:
			if normalizar(columna) not in columnas:
				errores.append(f"{ARCHIVOS[tipo]}: falta la columna '{columna}'")
		if errores:
			return errores

	for numero, anuncio in enumerate(anuncios, start=2):
		donde = f"{ARCHIVOS[tipo]} fila {numero}"

		if anuncio.fila.get(None):
			errores.append(f"{donde}: tiene más valores que columnas (¿una coma o ; de más?)")

		for columna in COLUMNAS_OBLIGATORIAS[tipo]:
			if not anuncio[columna]:
				errores.append(f"{donde}: '{columna}' está vacío")

		if anuncio.id:
			if anuncio.id in ids:
				errores.append(f"{donde}: el ID '{anuncio.id}' está repetido")
			ids.add(anuncio.id)

		precio, minimo = anuncio.precio, anuncio.precio_minimo
		if anuncio["Precio"] and precio is None:
			errores.append(f"{donde}: el precio '{anuncio['Precio']}' no es un número")
		if anuncio["Precio minimo"] and minimo is None:
			errores.append(f"{donde}: el precio mínimo '{anuncio['Precio minimo']}' no es un número")
		if precio is not None and minimo is not None and minimo > precio:
			errores.append(f"{donde}: el precio mínimo ({minimo}) es mayor que el precio ({precio})")

		if anuncio["Carpeta fotos"] and anuncio["Fotos"]:
			for ruta in anuncio.rutas_fotos:
				if not os.path.isfile(ruta):
					errores.append(f"{donde}: no existe la foto {ruta}")

		if tipo == "articulo" and len(anuncio.titulo) > 100:
			errores.append(f"{donde}: el título tiene más de 100 caracteres")

	return errores


# --- Estado (qué se publicó y en qué va cada conversación) ---

class Estado:
	def __init__(self):
		self.datos = {"publicados": {}, "conversaciones": {}, "envios": []}
		if os.path.exists(ARCHIVO_ESTADO):
			with open(ARCHIVO_ESTADO, encoding="utf-8") as archivo:
				self.datos.update(json.load(archivo))

	def guardar(self):
		os.makedirs(CARPETA_DATOS, exist_ok=True)
		temporal = ARCHIVO_ESTADO + ".tmp"
		with open(temporal, "w", encoding="utf-8") as archivo:
			json.dump(self.datos, archivo, ensure_ascii=False, indent=2)
		os.replace(temporal, ARCHIVO_ESTADO)

	# Publicaciones

	def publicado(self, tipo, id_anuncio):
		return self.datos["publicados"].get(f"{tipo}:{id_anuncio}")

	def marcar_publicado(self, tipo, id_anuncio, titulo):
		self.datos["publicados"][f"{tipo}:{id_anuncio}"] = {"titulo": titulo, "fecha": datetime.now().isoformat(timespec="seconds")}
		self.guardar()

	def dias_desde_publicacion(self, tipo, id_anuncio):
		info = self.publicado(tipo, id_anuncio)
		if not info:
			return None
		return (datetime.now() - datetime.fromisoformat(info["fecha"])).total_seconds() / 86400

	# Conversaciones

	def conversacion(self, url):
		return self.datos["conversaciones"].setdefault(url, {
			"estado": "negociando",  # negociando | cerrado
			"ultimo_procesado": None,
			"precio_acordado": None,
			"rechazados": [],
			"pendiente": None,
		})

	# Límite de envíos por hora

	def registrar_envio(self):
		self.datos["envios"].append(datetime.now().isoformat(timespec="seconds"))
		self.datos["envios"] = self.datos["envios"][-200:]
		self.guardar()

	def envios_ultima_hora(self):
		ahora = datetime.now()
		return sum(1 for f in self.datos["envios"] if (ahora - datetime.fromisoformat(f)).total_seconds() < 3600)


def registrar(accion, anuncio, detalle):
	"""Añade una línea a datos/registro.csv (se abre con Excel)."""
	os.makedirs(CARPETA_DATOS, exist_ok=True)
	nuevo = not os.path.exists(ARCHIVO_REGISTRO)
	with open(ARCHIVO_REGISTRO, "a", encoding="utf-8-sig", newline="") as archivo:
		escritor = csv.writer(archivo, delimiter=";")
		if nuevo:
			escritor.writerow(["Fecha", "Acción", "Anuncio", "Detalle"])
		escritor.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), accion, anuncio, detalle.replace("\n", " | ")])
	print(f"[{accion}] {anuncio}: {detalle}")
