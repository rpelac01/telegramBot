import telebot
import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 1. Cargar variables de entorno (tu token de Telegram)
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# 2. CONFIGURACIÓN DE GOOGLE SHEETS
NOMBRE_HOJA = "Mis Finanzas Cloud" # Pon aquí el nombre exacto de tu Excel en Google Drive

# Configurar el acceso con tu archivo JSON
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credenciales = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
cliente_google = gspread.authorize(credenciales)

# 3. Conectar con la hoja al iniciar el bot
try:
    hoja_calculo = cliente_google.open(NOMBRE_HOJA)
    hoja_registro = hoja_calculo.sheet1  # Primera pestaña de la hoja
    print(f"✅ Conectado con éxito a la hoja de Google: {NOMBRE_HOJA}")
except Exception as e:
    print(f"❌ Error al conectar con Google Sheets: {e}")
    print("⚠️ Revisa que la hoja se llame igual y esté compartida con el correo del bot.")

# 4. COMANDOS DEL BOT
@bot.message_handler(commands=["start"])
def enviar_bienvenida(mensaje):
    bot.reply_to(mensaje, "Hola, vamos a controlar tus gastos en la nube ☁️💸\nEscribe /gasto [cantidad] [concepto]")

@bot.message_handler(commands=['gasto'])
def registro_gasto(mensaje):
    trozos = mensaje.text.split(" ", 2)
    
    if len(trozos) < 3:
        bot.reply_to(mensaje, "⚠️ Error. Úsalo así: /gasto [cantidad] [concepto]")
        return
    
    cantidad = trozos[1]
    concepto = trozos[2]
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        # Reemplazamos coma por punto por si escribes "10,50" en vez de "10.50"
        cantidad_num = float(cantidad.replace(",", ".")) 
        
        # Insertar los datos en Google Sheets en la siguiente fila vacía
        hoja_registro.append_row([fecha_actual, "Gasto", cantidad_num, concepto])
        
        bot.reply_to(mensaje, f"☁️ ✅ ¡Guardado en la nube! Has gastado {cantidad_num}€ en: {concepto}")
        
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error: La cantidad debe ser un número (ej: 15.50).")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Hubo un problema al guardar en Google Sheets: {e}")
@bot.message_handler(commands=['ingreso'])
def registro_ingreso(mensaje):
    trozos = mensaje.text.split(" ", 2)
    
    if len(trozos) < 3:
        bot.reply_to(mensaje, "⚠️ Error. Úsalo así: /ingreso [cantidad] [concepto]")
        return
    
    cantidad = trozos[1]
    concepto = trozos[2]
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        cantidad_num = float(cantidad.replace(",", ".")) 
        
        # Guardamos en Sheets con la etiqueta "Ingreso"
        hoja_registro.append_row([fecha_actual, "Ingreso", cantidad_num, concepto])
        
        bot.reply_to(mensaje, f"☁️ 📈 ¡Ingreso guardado! Has sumado {cantidad_num}€ de: {concepto}")
        
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error: La cantidad debe ser un número (ej: 15.50).")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Hubo un problema al guardar en Google Sheets: {e}")
# 5. MANTENER EL BOT ESCUCHANDO (¡Siempre al final!)
print("🤖 Bot encendido y esperando mensajes... 🚀")
bot.infinity_polling()