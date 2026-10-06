import argparse
import os
import sys

# Todo funciona relativo a la carpeta del proyecto, se ejecute desde donde se ejecute
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import config
from bot.datos import Estado, leer_anuncios, validar

TIPOS = {"articulos": ["articulo"], "vehiculos": ["vehiculo"], "todo": ["articulo", "vehiculo"]}


def cargar(tipos):
	anuncios, errores = [], []
	for tipo in tipos:
		lista, ruta, _ = leer_anuncios(tipo)
		errores += validar(tipo, lista)
		anuncios += lista
	return anuncios, errores


def mostrar_errores(errores):
	print(f"Hay {len(errores)} problemas en tus CSV:")
	for error in errores:
		print("  - " + error)


def abrir_navegador():
	from bot.navegador import Navegador
	nav = Navegador("perfil_chrome")
	nav.asegurar_sesion(config.URL_FACEBOOK)
	return nav


def main():
	parser = argparse.ArgumentParser(description="Bot de Facebook Marketplace")
	sub = parser.add_subparsers(dest="comando", required=True)

	p = sub.add_parser("validar", help="Revisa los CSV sin abrir el navegador")
	p.add_argument("--solo", choices=TIPOS, default="todo")

	p = sub.add_parser("mejorar", help="La IA reescribe títulos y descripciones")
	p.add_argument("--solo", choices=TIPOS, default="todo")
	p.add_argument("--rehacer", action="store_true", help="Vuelve a mejorar aunque ya estén mejorados")

	p = sub.add_parser("publicar", help="Borra y vuelve a publicar los anuncios")
	p.add_argument("--solo", choices=TIPOS, default="todo")
	p.add_argument("--forzar", action="store_true", help="Republica aunque se haya publicado hace poco")

	p = sub.add_parser("negociar", help="Responde y negocia con los compradores")
	p.add_argument("--real", action="store_true", help="Envía los mensajes de verdad (sin esto es modo prueba)")

	sub.add_parser("diagnostico", help="Muestra cómo lee el bot tus chats, sin responder nada")

	args = parser.parse_args()
	tipos = TIPOS[getattr(args, "solo", "todo")]

	anuncios, errores = cargar(tipos)

	if args.comando == "validar":
		if errores:
			mostrar_errores(errores)
			sys.exit(1)
		print(f"Todo bien: {len(anuncios)} anuncios listos.")
		return

	if args.comando == "mejorar":
		from bot.mejorar import mejorar_todos
		mejorar_todos(tipos, args.rehacer)
		return

	# Publicar exige que todo esté correcto; negociar solo necesita leer los anuncios
	if args.comando == "publicar" and errores:
		mostrar_errores(errores)
		sys.exit(1)

	estado = Estado()
	nav = abrir_navegador()
	try:
		if args.comando == "publicar":
			from bot.publicar import actualizar_anuncios
			total = actualizar_anuncios(nav, anuncios, estado, args.forzar)
			print(f"Listo: {total} anuncios publicados.")
		else:
			from bot.negociar import Negociador
			real = args.real or (args.comando == "negociar" and not config.MODO_PRUEBA)
			negociador = Negociador(nav, anuncios, estado, real)
			if args.comando == "diagnostico":
				negociador.diagnostico()
			else:
				negociador.bucle()
	except KeyboardInterrupt:
		print("\nDetenido.")
	finally:
		nav.cerrar()


if __name__ == "__main__":
	main()
