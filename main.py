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
