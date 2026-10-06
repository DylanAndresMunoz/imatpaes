from bot import ia
from bot.datos import guardar_anuncios, leer_anuncios, registrar


def mejorar_todos(tipos, rehacer=False):
	"""Escribe títulos y descripciones mejorados en columnas nuevas. Tus textos originales no se tocan."""
	for tipo in tipos:
		anuncios, ruta, separador = leer_anuncios(tipo)
		cambios = 0

		for anuncio in anuncios:
			if anuncio["Descripcion mejorada"] and not rehacer:
				continue

			print(f"Mejorando '{anuncio.titulo}'...")
			mejora = ia.mejorar_anuncio(anuncio)
			if mejora is None:
				registrar("error", anuncio.titulo, "la IA no pudo mejorar este anuncio")
				continue

			if tipo == "articulo":
				anuncio["Titulo mejorado"] = mejora.titulo.strip()[:100]
			anuncio["Descripcion mejorada"] = mejora.descripcion.strip()
			cambios += 1

			print("-" * 60)
			if tipo == "articulo":
				print(f"Título:  {anuncio['Titulo']}\n   ->    {anuncio['Titulo mejorado']}")
			print(f"Descripción nueva:\n{anuncio['Descripcion mejorada']}")
			print(f"Qué cambió: {mejora.cambios}")
			print("-" * 60)

		if cambios:
			guardar_anuncios(tipo, anuncios, ruta, separador)
			registrar("mejorado", ruta, f"{cambios} anuncios mejorados (copia de seguridad en {ruta}.bak)")
