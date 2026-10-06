# Ventana emergente en el ordenador para aprobar tratos o responder tú mismo.

try:
	import tkinter as tk
	from tkinter import scrolledtext
except ImportError:  # En Linux puede faltar: sudo apt install python3-tk
	tk = None


def preguntar(titulo, explicacion, borrador, botones, minutos_limite):
	"""
	Muestra una ventana con la explicación, un cuadro de texto editable con el borrador
	y un botón por cada opción. botones: lista de (valor, etiqueta).
	Devuelve (valor_elegido, texto_editado). Si pasa el tiempo límite devuelve ("despues", borrador).
	"""
	if tk is None:
		return _preguntar_consola(titulo, explicacion, borrador, botones)

	resultado = {"valor": "despues", "texto": borrador}

	ventana = tk.Tk()
	ventana.title(titulo)
	ventana.attributes("-topmost", True)
	ventana.geometry("620x560")
	ventana.bell()

	tk.Label(ventana, text=titulo, font=("Arial", 14, "bold"), wraplength=580, justify="left").pack(anchor="w", padx=16, pady=(16, 6))

	explicacion_box = scrolledtext.ScrolledText(ventana, height=12, wrap="word", font=("Arial", 10))
	explicacion_box.insert("1.0", explicacion)
	explicacion_box.configure(state="disabled")
	explicacion_box.pack(fill="both", expand=True, padx=16)

	tk.Label(ventana, text="Mensaje que se enviará (puedes editarlo):", font=("Arial", 10, "bold")).pack(anchor="w", padx=16, pady=(10, 2))
	texto_box = tk.Text(ventana, height=5, wrap="word", font=("Arial", 11))
	texto_box.insert("1.0", borrador)
	texto_box.pack(fill="x", padx=16)

	def elegir(valor):
		resultado["valor"] = valor
		resultado["texto"] = texto_box.get("1.0", "end").strip()
		ventana.destroy()

	fila = tk.Frame(ventana)
	fila.pack(pady=14)
	for valor, etiqueta in botones:
		tk.Button(fila, text=etiqueta, font=("Arial", 11), padx=10, pady=4, command=lambda v=valor: elegir(v)).pack(side="left", padx=6)

	ventana.protocol("WM_DELETE_WINDOW", lambda: elegir("despues"))
	ventana.after(int(minutos_limite * 60 * 1000), lambda: elegir("despues"))
	ventana.mainloop()

	return resultado["valor"], resultado["texto"]


def _preguntar_consola(titulo, explicacion, borrador, botones):
	print("\n" + "=" * 60 + "\n" + titulo + "\n" + "=" * 60)
	print(explicacion)
	print("\nMensaje propuesto:\n" + borrador + "\n")
	for numero, (_, etiqueta) in enumerate(botones, start=1):
		print(f"  {numero}) {etiqueta}")
	while True:
		opcion = input("Elige una opción: ").strip()
		if opcion.isdigit() and 1 <= int(opcion) <= len(botones):
			valor = botones[int(opcion) - 1][0]
			break
	texto = input("Escribe el mensaje a enviar (Enter para dejar el propuesto): ").strip() or borrador
	return valor, texto
