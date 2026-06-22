import telebot
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
@bot.message_handler(commands = ["start"])
def enviar_bienvenida(mensaje):
    bot.reply_to(mensaje, "Hola, vamos a controlar tus gastos")
print("Bot encendido")
bot.infinity_polling()

@bot.message_handler(commands = ['gasto'])
def registro_gasto(mensaje):
    trozos = mensaje.text.split("", 2)
    if len(trozos)<3:
        bot.reply_to(mensaje, "⚠️ Error. Úsalo así: /gasto [cantidad] [concepto]")
        return
    cantidad = trozos[1]
    concepto = trozos[2]
    bot.reply_to(mensaje, f"✅ ¡Apuntado! Has gastado {cantidad}€ en: {concepto}")