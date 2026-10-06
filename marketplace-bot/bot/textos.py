# Textos de la interfaz de Facebook en español e inglés.
# Si Facebook cambia algún texto y el bot no encuentra un botón o campo, añade aquí la variante nueva.

TEXTOS = {
	# Formulario de publicación
	"titulo": ["Título", "Title"],
	"precio": ["Precio", "Price"],
	"categoria": ["Categoría", "Category"],
	"estado": ["Estado", "Condition"],
	"descripcion": ["Descripción", "Description"],
	"ubicacion": ["Ubicación", "Location"],
	"marca": ["Marca", "Brand"],
	"tipo_vehiculo": ["Tipo de vehículo", "Vehicle type"],
	"anio": ["Año", "Year"],
	"fabricante": ["Marca", "Make"],
	"modelo": ["Modelo", "Model"],
	"kilometraje": ["Kilometraje", "Mileage"],
	"combustible": ["Tipo de combustible", "Fuel type"],
	"siguiente": ["Siguiente", "Next"],
	"publicar": ["Publicar", "Publish"],
	"cerrar": ["Cerrar", "Close"],
	"salir_pagina": ["Salir de la página", "Abandonar página", "Leave Page"],
	"articulo_en_venta": ["Artículo en venta", "Item for sale"],
	"vehiculo_en_venta": ["Vehículo en venta", "Vehicle for sale"],

	# Tus anuncios
	"buscar_anuncios": ["Busca tus anuncios", "Buscar en tus anuncios", "Search your listings"],
	"eliminar": ["Eliminar", "Delete"],
	"eliminar_anuncio": ["Eliminar anuncio", "Delete listing", "Delete Listing"],
	"tu_anuncio": ["Tu anuncio", "Your Listing"],

	# Compartir en grupos
	"compartir": ["Compartir", "Share"],
	"grupo": ["Grupo", "Group"],
	"buscar_grupos": ["Buscar grupos", "Search for groups"],
	"publicar_post": ["Publicar", "Post"],
	"escribe_algo": ["Crea una publicación pública…", "Escribe algo...", "Create a public post…", "Write something..."],
	"compartido_grupo": ["Se compartió en tu grupo.", "Compartido en tu grupo.", "Shared to your group."],

	# Messenger
	"mensaje": ["Mensaje", "Escribe un mensaje", "Message", "Aa"],
	"marcador_mio": ["Tú enviaste", "Enviaste", "You sent"],
}


def _comillas(texto):
	# XPath 1.0 no tiene escape: si el texto tiene comillas dobles usamos concat()
	if '"' not in texto:
		return '"' + texto + '"'
	partes = texto.split('"')
	return "concat(" + ", '\"', ".join('"' + p + '"' for p in partes) + ")"


def literal(texto):
	return _comillas(texto)


def xp_texto(clave):
	"""Condición XPath: text() igual a cualquiera de las variantes."""
	return " or ".join("text()=" + _comillas(t) for t in TEXTOS[clave])


def xp_atributo(atributo, clave):
	"""Condición XPath: @atributo igual a cualquiera de las variantes."""
	return " or ".join("@" + atributo + "=" + _comillas(t) for t in TEXTOS[clave])
