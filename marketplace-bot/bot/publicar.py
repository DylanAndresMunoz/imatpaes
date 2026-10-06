import random
import time

import config
from bot.datos import registrar
from bot.navegador import ElementoNoEncontrado
from bot.textos import TEXTOS, literal, xp_atributo, xp_texto

URL_MIS_ANUNCIOS = config.URL_FACEBOOK + "/marketplace/you/selling"
URL_CREAR = config.URL_FACEBOOK + "/marketplace/create/"
CAMPO_FOTOS = 'input[accept="image/*,image/heif,image/heic"]'


def campo(clave, sufijo="/following-sibling::input[1]"):
	return f"//span[{xp_texto(clave)}]{sufijo}"


def opcion(texto):
	return f"//span[text()={literal(texto)}]"


def actualizar_anuncios(nav, anuncios, estado, forzar=False):
	"""Borra y vuelve a publicar cada anuncio. Devuelve cuántos se publicaron."""
	publicados = 0

	for anuncio in anuncios:
		if publicados >= config.MAX_ANUNCIOS_POR_EJECUCION:
			print(f"Límite de {config.MAX_ANUNCIOS_POR_EJECUCION} anuncios por ejecución alcanzado.")
			break

		dias = estado.dias_desde_publicacion(anuncio.tipo, anuncio.id)
		if not forzar and dias is not None and dias < config.DIAS_ENTRE_REPUBLICACIONES:
			print(f"Saltado '{anuncio.titulo}': se publicó hace {dias:.1f} días.")
			continue

		if publicados > 0:
			espera = random.randint(*config.PAUSA_ENTRE_ANUNCIOS_SEG)
			print(f"Esperando {espera} s antes del siguiente anuncio...")
			time.sleep(espera)

		try:
			# Puede estar publicado con el título anterior (antes de mejorarlo)
			anterior = estado.publicado(anuncio.tipo, anuncio.id)
			titulos = {anuncio.titulo, anuncio["Titulo"]} | ({anterior["titulo"]} if anterior else set())
			for titulo in titulos:
				if titulo and eliminar_anuncio(nav, titulo):
					registrar("eliminado", titulo, "anuncio anterior eliminado")

			if not publicar_anuncio(nav, anuncio):
				# A veces falla a la primera; un segundo intento suele bastar
				if not publicar_anuncio(nav, anuncio):
					raise ElementoNoEncontrado("Facebook no dejó publicar el anuncio")

			estado.marcar_publicado(anuncio.tipo, anuncio.id, anuncio.titulo)
			registrar("publicado", anuncio.titulo, f"precio {anuncio['Precio']}")
			publicados += 1
		except ElementoNoEncontrado as error:
			registrar("error", anuncio.titulo, str(error))

	return publicados


def buscar_en_mis_anuncios(nav, titulo):
	nav.ir(URL_MIS_ANUNCIOS)
	buscador = f"//input[{xp_atributo('placeholder', 'buscar_anuncios')}]"
	if nav.buscar(buscador, obligatorio=False, segundos=15) is None:
		return None
	nav.borrar_texto(buscador)
	nav.escribir(buscador, titulo)
	return nav.buscar(opcion(titulo), obligatorio=False, segundos=10)


def eliminar_anuncio(nav, titulo):
	elemento = buscar_en_mis_anuncios(nav, titulo)
	if elemento is None:
		return False

	elemento.click()
	nav.clic(f'//div[not(@role="gridcell")]/div[({xp_atributo("aria-label", "eliminar")}) and @tabindex="0"]')
	nav.clic(f'//div[{xp_atributo("aria-label", "eliminar_anuncio")}]//div[({xp_atributo("aria-label", "eliminar")}) and @tabindex="0"]')
	nav.esperar_invisible(f'//div[{xp_atributo("aria-label", "tu_anuncio")}]')
	return True


def publicar_anuncio(nav, anuncio):
	nav.ir(URL_CREAR + ("vehicle" if anuncio.tipo == "vehiculo" else "item"))
	nav.subir_archivos(CAMPO_FOTOS, anuncio.rutas_fotos)

	if anuncio.tipo == "vehiculo":
		rellenar_vehiculo(nav, anuncio)
	else:
		rellenar_articulo(nav, anuncio)

	nav.escribir(campo("precio"), anuncio["Precio"])
	nav.escribir(campo("descripcion", "/following-sibling::div/textarea"), anuncio.descripcion)
	nav.escribir(campo("ubicacion"), anuncio["Ubicacion"])
	nav.clic('//ul[@role="listbox"]/li[1]/div')

	siguiente = f'//div[{xp_atributo("aria-label", "siguiente")}]/div'
	hay_siguiente = nav.buscar(siguiente, obligatorio=False, segundos=3) is not None
	if hay_siguiente:
		nav.clic(siguiente)
		marcar_grupos(nav, anuncio)

	# Si aparece "Cerrar" en este punto, Facebook mostró un error
	cerrar = f"//span[{xp_texto('cerrar')}]"
	if nav.buscar(cerrar, obligatorio=False, segundos=10) is not None:
		nav.clic(cerrar)
		return False

	nav.clic(f'//div[({xp_atributo("aria-label", "publicar")}) and not(@aria-disabled)]')

	salir = f'//div[@tabindex="0"]//span[{xp_texto("salir_pagina")}]'
	if nav.buscar(salir, obligatorio=False, segundos=15) is not None:
		nav.clic(salir)

	encabezado = "vehiculo_en_venta" if anuncio.tipo == "vehiculo" else "articulo_en_venta"
	nav.esperar_invisible(f"//h1[{xp_texto(encabezado)}]")

	if not hay_siguiente:
		compartir_en_grupos(nav, anuncio)
	return True


def rellenar_vehiculo(nav, anuncio):
	nav.clic(f"//span[{xp_texto('tipo_vehiculo')}]")
	nav.clic(opcion(anuncio["Tipo de vehiculo"]))

	nav.desplazar_a(f"//span[{xp_texto('anio')}]")
	nav.clic(f"//span[{xp_texto('anio')}]")
	nav.clic(opcion(anuncio["Año"]))

	nav.escribir(campo("fabricante"), anuncio["Marca"])
	nav.escribir(campo("modelo"), anuncio["Modelo"])

	nav.desplazar_a(campo("kilometraje"))
	nav.escribir(campo("kilometraje"), anuncio["Kilometraje"])

	nav.clic(f"//span[{xp_texto('combustible')}]")
	nav.clic(opcion(anuncio["Combustible"]))


def rellenar_articulo(nav, anuncio):
	nav.escribir(campo("titulo"), anuncio.titulo)

	nav.desplazar_a(f"//span[{xp_texto('categoria')}]")
	nav.clic(f"//span[{xp_texto('categoria')}]")
	nav.clic(opcion(anuncio["Categoria"]))

	nav.clic(f"//div/span[{xp_texto('estado')}]")
	nav.clic(f'//span[@dir="auto"][text()={literal(anuncio["Estado"])}]')

	# La marca solo aparece en algunas categorías
	if anuncio["Marca"]:
		nav.escribir(campo("marca"), anuncio["Marca"], obligatorio=False, segundos=3)


def marcar_grupos(nav, anuncio):
	for grupo in anuncio.grupos:
		nav.clic(opcion(grupo), obligatorio=False, segundos=10)


def compartir_en_grupos(nav, anuncio):
	if not anuncio.grupos:
		return
	if buscar_en_mis_anuncios(nav, anuncio.titulo) is None:
		return

	buscador = f'//*[{xp_atributo("aria-label", "buscar_grupos")}]'
	cuadro = f'//*[{xp_atributo("aria-label", "escribe_algo")}]'
	boton_compartir = " or ".join("contains(., " + literal(t) + ")" for t in TEXTOS["compartir"])

	for grupo in anuncio.grupos:
		try:
			nav.clic(f'//*[contains(@aria-label, {literal(anuncio.titulo)})]//span//span[{boton_compartir}]')
			nav.clic(f"//span[{xp_texto('grupo')}]")
			nav.borrar_texto(buscador)
			nav.escribir(buscador, grupo[:51])
			nav.clic(opcion(grupo))

			if nav.buscar(cuadro, obligatorio=False, segundos=3) is not None:
				nav.escribir(cuadro, anuncio.descripcion)

			nav.clic(f'//*[({xp_atributo("aria-label", "publicar_post")}) and not(@aria-disabled)]')
			nav.esperar_invisible('//*[@role="dialog"]')
			nav.buscar(f"//span[{xp_texto('compartido_grupo')}]", obligatorio=False, segundos=10)
			registrar("compartido", anuncio.titulo, f"en el grupo {grupo}")
		except ElementoNoEncontrado as error:
			registrar("error", anuncio.titulo, f"no se pudo compartir en {grupo}: {error}")
