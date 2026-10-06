# Configuración del bot. Cambia estos valores a tu gusto.

# --- IA (Claude) ---
# La clave se lee de la variable de entorno ANTHROPIC_API_KEY o del archivo clave_api.txt
MODELO_IA = "claude-opus-5-5"

# --- General ---
MONEDA = "$"  # Símbolo que usa la IA al hablar de precios
URL_FACEBOOK = "https://www.facebook.com"

# --- Publicar ---
MAX_ANUNCIOS_POR_EJECUCION = 10          # Máximo de anuncios que se republican cada vez
PAUSA_ENTRE_ANUNCIOS_SEG = (60, 180)     # Espera aleatoria entre anuncios (mín, máx)
DIAS_ENTRE_REPUBLICACIONES = 3           # No republica un anuncio si se publicó hace menos de estos días

# --- Negociar ---
# En modo prueba el bot NO envía nada: solo muestra lo que respondería.
# Para enviar de verdad usa: python main.py negociar --real
MODO_PRUEBA = True
INTERVALO_REVISION_MIN = 5               # Cada cuántos minutos revisa los mensajes
MAX_CONVERSACIONES_POR_REVISION = 15     # Cuántos chats recientes revisa en cada vuelta
MAX_MENSAJES_POR_HORA = 20               # Límite de mensajes enviados por hora
AVISO_TIMEOUT_MIN = 15                   # Si no respondes la ventana en este tiempo, te vuelve a preguntar más tarde
# El bot solo contesta "¿sigue disponible?", rebajas y permutas. Con True, cualquier otra pregunta
# te aparece en una ventana (recomendado: al abrir el chat, Facebook lo marca como leído y podrías no verlo).
# Con False, solo se anota en datos/registro.csv.
AVISAR_OTRAS_PREGUNTAS = True
