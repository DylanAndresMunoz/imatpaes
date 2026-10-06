# Bot de Facebook Marketplace (en español, con IA)

Basado en el proyecto de código abierto *facebook-marketplace-bot* (licencia GPLv3).

| Comando | Qué hace |
|---|---|
| `python main.py mejorar` | La IA reescribe tus títulos y descripciones para que aparezcan en más búsquedas. Tus textos originales no se tocan. |
| `python main.py publicar` | Borra tus anuncios y los vuelve a publicar para que salgan arriba (y los comparte en tus grupos). |
| `python main.py negociar` | Lee los mensajes de los compradores, responde y regatea sin bajar nunca de tu precio mínimo. **Antes de cerrar un trato te muestra una ventana para que lo apruebes.** |
| `python main.py diagnostico` | Muestra cómo lee el bot tus chats, sin responder nada. Úsalo la primera vez. |
| `python main.py validar` | Revisa tus CSV (columnas, precios, que existan las fotos). |

## Instalación (una sola vez)

1. Instala [Python 3.10 o superior](https://www.python.org/downloads/). En Windows marca la casilla **"Add Python to PATH"**.
2. Instala [Google Chrome](https://www.google.com/chrome/).
3. Abre una terminal en esta carpeta y ejecuta:
   ```
   pip install -r requirements.txt
   ```
   (En Mac usa `pip3` y `python3`. En Linux, si la ventana de aviso no aparece: `sudo apt install python3-tk`.)
4. Crea una clave de la API de Claude en [platform.claude.com](https://platform.claude.com/) y pégala en un archivo llamado `clave_api.txt` dentro de esta carpeta. Ese archivo no se sube a GitHub.
5. Pon **Facebook en español o inglés** (el bot reconoce los dos).

## Tus anuncios: `csvs/articulos.csv` y `csvs/vehiculos.csv`

Ábrelos con Excel, Google Sheets o LibreOffice. Cada fila es un anuncio.

| Columna | Qué poner |
|---|---|
| `ID` | Un código único que no cambie nunca (A1, A2, V1...). Así el bot reconoce el anuncio aunque cambies el título. |
| `Precio` | Precio publicado, solo números (`180000`). |
| `Precio minimo` | **Lo mínimo que aceptas.** Es secreto: la IA nunca lo dice y el código bloquea cualquier mensaje que lo rompa. |
| `Categoria`, `Estado`, `Tipo de vehiculo`, `Combustible` | El texto **exacto** de la opción como aparece en Facebook (por ejemplo `Usado: buen estado`). |
| `Carpeta fotos` | Carpeta donde están las fotos: `C:\Fotos\bici` (Windows) o `/Users/tu/Fotos/bici` (Mac). |
| `Fotos` | Nombres de las fotos separados por `;` → `foto1.jpg; foto2.jpg` |
| `Grupos` | Nombres exactos de grupos separados por `;` (opcional). |
| `Info extra` | **Muy importante para negociar:** dónde y cuándo entregas, formas de pago y defectos. La IA solo usa lo que pongas aquí y en la descripción; si le preguntan algo que no sabe, te pregunta a ti. |
| `Titulo mejorado`, `Descripcion mejorada` | Las rellena `mejorar`. Si existen, se publican en vez de las originales. Bórralas si no te gustan. |

No importa si Excel guarda el archivo con `,` o con `;`: el bot detecta los dos.

## Primer uso recomendado

```
python main.py validar          # 1. Corrige lo que te diga
python main.py mejorar          # 2. Revisa en el CSV los textos que propone la IA
python main.py publicar         # 3. La primera vez inicia sesión en Facebook en la ventana de Chrome
python main.py diagnostico      # 4. Comprueba que YO / COMPRADOR salen bien en tus chats
python main.py negociar         # 5. Modo prueba: muestra qué respondería, sin enviar nada
python main.py negociar --real  # 6. Cuando te convenza, en modo real
```

Deja la ventana de Chrome abierta mientras el bot trabaja. Para pararlo pulsa `Ctrl + C`.

## Cómo negocia

- Defiende el precio publicado y baja poco a poco, pidiendo algo a cambio (que retire hoy, pago al contado).
- **Nunca baja de tu `Precio minimo`.** Además de decírselo a la IA, el código revisa cada mensaje: si aparece una cifra por debajo de tu mínimo (también escrita como "140 mil", "140 lucas" o "4,5 millones"), no lo envía y te pregunta a ti.
- **No cierra tratos sola.** Cuando un comprador acepta un precio, te aparece una ventana con el resumen y el mensaje de confirmación:
  - **✅ Aceptar y enviar**: envía la confirmación (puedes editarla antes).
  - **❌ Rechazar este precio**: la IA hace una contraoferta y no vuelve a ofrecer ese precio.
  - **⏸ Decidir más tarde**: te vuelve a preguntar en la siguiente revisión.
- Te pide ayuda (con otra ventana) si le preguntan algo que no sabe, si piden envíos, pagos por adelantado o enlaces, o si algo parece una estafa.
- Solo toca los chats de anuncios que están en tus CSV. Tus chats personales se ignoran.
- Si un comprador pregunta si habla con un bot, no lo niega: dice que es un asistente y que tú confirmas los tratos.

## Ajustes (`config.py`)

| Ajuste | Por defecto | Para qué |
|---|---|---|
| `MONEDA` | `$` | Símbolo de los precios. |
| `MAX_ANUNCIOS_POR_EJECUCION` | 10 | Anuncios republicados como máximo cada vez. |
| `PAUSA_ENTRE_ANUNCIOS_SEG` | 60 a 180 | Espera entre anuncios. |
| `DIAS_ENTRE_REPUBLICACIONES` | 3 | No republica un anuncio publicado hace menos días (`--forzar` lo salta). |
| `INTERVALO_REVISION_MIN` | 5 | Cada cuánto revisa los mensajes. |
| `MAX_MENSAJES_POR_HORA` | 20 | Límite de mensajes enviados. |
| `AVISO_TIMEOUT_MIN` | 15 | Si no contestas la ventana en este tiempo, se cierra y te vuelve a preguntar después. |

Todo lo que hace el bot queda anotado en `datos/registro.csv`.

## Si algo falla

- **"No se encontró el elemento"**: Facebook cambió un texto o un botón. Abre `bot/textos.py` y añade la variante nueva a la lista correspondiente.
- **En el diagnóstico salen al revés YO y COMPRADOR**: avísame con lo que muestra el diagnóstico y lo ajusto.
- **Coste de la IA**: cada respuesta cuesta uno o dos centavos de dólar. Puedes ver el gasto en platform.claude.com.

## ⚠️ Riesgos

Las condiciones de Meta no permiten automatizar Facebook. Borrar y republicar muy seguido o enviar muchos mensajes puede provocar bloqueos temporales de Marketplace o restricciones de la cuenta. Los límites de `config.py` reducen ese riesgo, pero no lo eliminan. La carpeta `perfil_chrome/` contiene tu sesión de Facebook: no la compartas.
