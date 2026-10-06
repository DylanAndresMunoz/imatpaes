import hashlib
import json
import random
import re
import time

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys

import config
from bot import aviso, ia
from bot.datos import a_numero, normalizar, registrar
from bot.navegador import ElementoNoEncontrado, solo_bmp
from bot.textos import TEXTOS

BANDEJAS = [config.URL_FACEBOOK + "/marketplace/inbox/", config.URL_FACEBOOK + "/messages/t/"]

JS_LISTAR_CHATS = r"""
const vistos = new Set();
const urls = [];
for (const a of document.querySelectorAll('a[href*="/t/"]')) {
	const href = a.href.split('?')[0].replace(/\/$/, '');
	if (!/\/t\/[^\/]+$/.test(href) || vistos.has(href)) continue;
	vistos.add(href);
	urls.push(href);
}
return urls;
"""

# Lee los mensajes del chat abierto. Un mensaje es "mío" si Facebook lo marca como enviado
# por mí (texto oculto para lectores de pantalla) o, si no, si la burbuja está a la derecha.
JS_LEER_CHAT = r"""
const marcadores = arguments[0];
const main = document.querySelector('[role="main"]');
if (!main) return null;
const caja = main.getBoundingClientRect();
const centro = caja.left + caja.width / 2;
const mensajes = [];
for (const fila of main.querySelectorAll('[role="row"]')) {
	const hojas = Array.from(fila.querySelectorAll('div[dir="auto"]')).filter(e => !e.querySelector('div[dir="auto"]'));
	const partes = [...new Set(hojas.map(e => e.innerText.trim()).filter(Boolean))];
	if (!partes.length) continue;
	const etiquetas = Array.from(fila.querySelectorAll('h4, h5, h6, [aria-hidden="false"]')).map(e => e.innerText.trim());
	let mio = etiquetas.some(t => marcadores.some(m => t.startsWith(m)));
	if (!mio) {
		const r = hojas[0].getBoundingClientRect();
		mio = (r.left + r.width / 2) > centro;
	}
	mensajes.push({texto: partes.join('\n'), mio: mio});
}
return {cabecera: main.innerText.slice(0, 800), texto: main.innerText.slice(0, 20000), mensajes: mensajes};
"""


class Negociador:
	def __init__(self, nav, anuncios, estado, real):
		self.nav = nav
		self.estado = estado
		self.real = real
		self.anuncios = anuncios
		# Todos los títulos con los que se puede reconocer cada anuncio en un chat
		self.titulos = []
		for anuncio in anuncios:
			posibles = {anuncio.titulo, anuncio["Titulo"]}
			anterior = estado.publicado(anuncio.tipo, anuncio.id)
			if anterior:
				posibles.add(anterior["titulo"])
			for titulo in posibles:
				if titulo and len(titulo) >= 4:
					self.titulos.append((normalizar(titulo), anuncio))
		# Primero los títulos más largos para no confundir "iPhone 12" con "iPhone 12 Pro"
		self.titulos.sort(key=lambda par: len(par[0]), reverse=True)

	# --- Bucle principal ---

	def bucle(self):
		modo = "REAL: los mensajes se envían" if self.real else "PRUEBA: no se envía nada"
		print(f"Negociando en modo {modo}. Pulsa Ctrl+C para parar.")
		while True:
			self.revisar()
			minutos = config.INTERVALO_REVISION_MIN * random.uniform(0.8, 1.3)
			print(f"Próxima revisión en {minutos:.0f} min.")
			time.sleep(minutos * 60)

	def revisar(self):
		for url in self.listar_chats()[:config.MAX_CONVERSACIONES_POR_REVISION]:
			try:
				self.procesar(url)
			except (ElementoNoEncontrado, WebDriverException) as error:
				registrar("error", url, str(error).splitlines()[0])
			self.nav.pausa(2, 6)

	def listar_chats(self):
		urls = []
		for bandeja in BANDEJAS:
			self.nav.ir(bandeja)
			time.sleep(5)
			for url in self.nav.driver.execute_script(JS_LISTAR_CHATS):
				if url not in urls:
					urls.append(url)
		return urls

	def leer_chat(self, url):
		self.nav.ir(url)
		self.nav.buscar('//div[@role="main"]', segundos=20)
		time.sleep(3)  # Dar tiempo a que carguen los mensajes
		return self.nav.driver.execute_script(JS_LEER_CHAT, TEXTOS["marcador_mio"])

	def identificar_anuncio(self, datos):
		# Facebook muestra el título del anuncio arriba del chat de Marketplace
		for zona in (datos["cabecera"], datos["texto"]):
			zona = normalizar(zona)
			for titulo, anuncio in self.titulos:
				if titulo in zona:
					return anuncio
		return None

	# --- Una conversación ---

	def procesar(self, url, reintento=False):
		datos = self.leer_chat(url)
		if not datos:
			return
		anuncio = self.identificar_anuncio(datos)
		if anuncio is None:
			return  # Chat personal o de un anuncio que no está en tus CSV: no se toca

		mensajes = datos["mensajes"][-30:]
		if not mensajes or mensajes[-1]["mio"]:
			return  # Nada nuevo del comprador

		conversacion = self.estado.conversacion(self._clave(url))
		firma = hashlib.sha1(json.dumps(mensajes[-3:], ensure_ascii=False).encode()).hexdigest()
		if conversacion["ultimo_procesado"] == firma:
			return

		pendiente = conversacion.get("pendiente")
		if pendiente and pendiente["firma"] == firma:
			decision = ia.Decision.model_validate(pendiente["decision"])
		else:
			if self.real and self.estado.envios_ultima_hora() >= config.MAX_MENSAJES_POR_HORA:
				print("Límite de mensajes por hora alcanzado; se responderá en la próxima revisión.")
				return
			decision = salvaguardas(ia.decidir_respuesta(anuncio, mensajes, conversacion), anuncio, conversacion)

		self.ejecutar(url, anuncio, mensajes, conversacion, firma, decision, reintento)
		self.estado.guardar()

	def ejecutar(self, url, anuncio, mensajes, conversacion, firma, decision, reintento):
		titulo = anuncio.titulo
		prefijo = "" if self.real else "[PRUEBA] "

		if decision.accion == "no_responder":
			registrar("sin respuesta", titulo, decision.resumen)

		elif decision.accion == "responder":
			self.enviar(decision.mensaje, titulo, decision.resumen)

		elif decision.accion == "proponer_trato":
			trato = describir_trato(decision)
			eleccion, texto = aviso.preguntar(
				f"{prefijo}¿Aceptar {trato}?",
				explicar(anuncio, mensajes, decision),
				decision.mensaje,
				[("aceptar", "✅ Aceptar y enviar"), ("rechazar", "❌ Rechazar"), ("despues", "⏸ Decidir más tarde")],
				config.AVISO_TIMEOUT_MIN,
			)
			if eleccion == "despues":
				return self._dejar_pendiente(conversacion, firma, decision)
			if eleccion == "aceptar":
				self.enviar(texto, titulo, f"aceptaste {trato}")
				conversacion["estado"] = "cerrado"
				conversacion["precio_acordado"] = decision.precio_acordado
			else:
				if decision.permuta:
					conversacion.setdefault("permutas_rechazadas", []).append(decision.permuta)
				else:
					conversacion["rechazados"].append(decision.precio_acordado)
				conversacion["pendiente"] = None
				registrar("trato rechazado", titulo, trato)
				self.estado.guardar()
				if not reintento:
					# Volvemos a preguntar a la IA para que haga una contraoferta
					return self.procesar(url, reintento=True)
				return

		elif not config.AVISAR_OTRAS_PREGUNTAS:
			registrar("para ti", titulo, "pregunta que respondes tú: " + decision.resumen)

		else:  # pedir_ayuda
			eleccion, texto = aviso.preguntar(
				f"{prefijo}Un comprador necesita tu respuesta",
				explicar(anuncio, mensajes, decision),
				decision.mensaje,
				[("enviar", "📨 Enviar este mensaje"), ("manual", "Lo respondo yo en Facebook"), ("despues", "⏸ Más tarde")],
				config.AVISO_TIMEOUT_MIN,
			)
			if eleccion == "despues":
				return self._dejar_pendiente(conversacion, firma, decision)
			if eleccion == "enviar" and texto:
				self.enviar(texto, titulo, "respuesta escrita/aprobada por ti")
			else:
				registrar("ayuda", titulo, "lo respondes tú: " + decision.resumen)

		conversacion["ultimo_procesado"] = firma
		conversacion["pendiente"] = None

	def _dejar_pendiente(self, conversacion, firma, decision):
		conversacion["pendiente"] = {"firma": firma, "decision": decision.model_dump()}
		self.estado.guardar()

	def _clave(self, url):
		# En modo prueba se guarda aparte para no marcar chats como respondidos de verdad
		return url if self.real else "prueba:" + url

	def enviar(self, texto, titulo, motivo):
		texto = solo_bmp(texto).strip()
		if not texto:
			return
		if not self.real:
			registrar("[PRUEBA] respondería", titulo, texto)
			return

		caja = self.nav.buscar('//div[@role="main"]//div[@role="textbox" and @contenteditable="true"]', obligatorio=False, segundos=10)
		if caja is None:
			caja = self.nav.buscar('//div[@role="textbox" and @contenteditable="true"]', segundos=10)
		caja.click()
		lineas = texto.split("\n")
		for numero, linea in enumerate(lineas):
			for trozo in re.findall(r".{1,25}", linea) or [""]:
				caja.send_keys(trozo)
				self.nav.pausa(0.05, 0.3)
			if numero < len(lineas) - 1:
				caja.send_keys(Keys.SHIFT, Keys.ENTER)
		self.nav.pausa(0.5, 1.5)
		caja.send_keys(Keys.ENTER)
		self.estado.registrar_envio()
		registrar("enviado", titulo, f"{texto} ({motivo})")

	# --- Diagnóstico ---

	def diagnostico(self, cuantos=5):
		urls = self.listar_chats()
		print(f"Encontrados {len(urls)} chats. Mostrando los {min(cuantos, len(urls))} primeros:\n")
		for url in urls[:cuantos]:
			datos = self.leer_chat(url)
			if not datos:
				print(url, "-> no se pudo leer\n")
				continue
			anuncio = self.identificar_anuncio(datos)
			print("=" * 70)
			print(url)
			print("Anuncio reconocido:", anuncio.titulo if anuncio else "ninguno (el bot ignorará este chat)")
			for mensaje in datos["mensajes"][-6:]:
				print(("  YO        " if mensaje["mio"] else "  COMPRADOR ") + mensaje["texto"].replace("\n", " / ")[:120])
			print()


def salvaguardas(decision, anuncio, conversacion):
	"""Comprobaciones en código, por si la IA se equivoca con el precio mínimo."""
	minimo = anuncio.precio_minimo

	def ayuda(motivo):
		return ia.Decision(accion="pedir_ayuda", mensaje=decision.mensaje, precio_acordado=decision.precio_acordado,
			permuta=decision.permuta, resumen=f"{motivo} {decision.resumen}")

	if decision.accion == "proponer_trato":
		if conversacion["estado"] == "cerrado":
			return ayuda("El trato ya estaba cerrado y la IA propuso otro.")
		# En una permuta el valor lo decides tú en la ventana; en dinero no puede bajar del mínimo
		if not decision.permuta and (decision.precio_acordado is None or (minimo is not None and decision.precio_acordado < minimo)):
			return ayuda("La IA propuso un trato por debajo del mínimo.")

	if decision.accion == "responder":
		if not decision.mensaje.strip():
			return ayuda("La IA no escribió respuesta.")
		if minimo:
			for numero in numeros(decision.mensaje):
				if minimo * 0.4 <= numero < minimo:
					return ayuda(f"La IA iba a mencionar {config.MONEDA}{formato(numero)}, por debajo del mínimo.")

	return decision


MULTIPLICADORES = {"mil": 1000, "luca": 1000, "lucas": 1000, "k": 1000, "millon": 1000000, "millones": 1000000, "millón": 1000000}


def numeros(texto):
	"""Cifras del texto: '$165.000' -> 165000, '140 mil' / '140 lucas' -> 140000, '4,5 millones' -> 4500000."""
	resultado = []
	for cifra, palabra in re.findall(r"(\d[\d.,]*)\s*(mil|lucas?|k|millones|millón|millon)?\b", texto.lower()):
		if palabra:
			# En "4,5 millones" la coma es decimal
			valor = a_numero(cifra.replace(",", ".")) if re.fullmatch(r"\d+[.,]\d{1,2}", cifra) else a_numero(cifra)
			if valor is not None:
				resultado.append(valor * MULTIPLICADORES[palabra])
		else:
			valor = a_numero(cifra)
			if valor is not None:
				resultado.append(valor)
	return resultado


def formato(numero):
	if numero is None:
		return "?"
	if float(numero).is_integer():
		return f"{int(numero):,}".replace(",", ".")
	return str(numero)


def describir_trato(decision):
	if decision.permuta:
		extra = f" + {config.MONEDA}{formato(decision.precio_acordado)}" if decision.precio_acordado else ""
		return f"permuta por {decision.permuta}{extra}"
	return f"venta por {config.MONEDA}{formato(decision.precio_acordado)}"


def explicar(anuncio, mensajes, decision):
	ultimos = "\n".join(("Yo: " if m["mio"] else "Comprador: ") + m["texto"] for m in mensajes[-8:])
	return (
		f"Anuncio: {anuncio.titulo}\n"
		f"Precio publicado: {config.MONEDA}{formato(anuncio.precio)}   |   Tu mínimo: {config.MONEDA}{formato(anuncio.precio_minimo)}\n\n"
		+ (f"Permuta ofrecida: {decision.permuta}\n" if decision.permuta else "")
		+ f"Resumen de la IA: {decision.resumen}\n\n"
		f"Últimos mensajes:\n{ultimos}"
	)
