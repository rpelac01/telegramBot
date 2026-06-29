import telebot
import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y TELEGRAM
# ==========================================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ==========================================
# 2. CONFIGURACIÓN DE GOOGLE SHEETS
# ==========================================
NOMBRE_HOJA = "Mis Finanzas Cloud"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credenciales = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
cliente_google = gspread.authorize(credenciales)

try:
    hoja_calculo = cliente_google.open(NOMBRE_HOJA)
    hoja_registro = hoja_calculo.sheet1
    print(f"✅ Conectado con éxito a la hoja de Google: {NOMBRE_HOJA}")
except Exception as e:
    print(f"❌ Error al conectar con Google Sheets: {e}")

# ==========================================
# 3. LÓGICA DE CÁLCULO DE SALDOS
# ==========================================
def obtener_saldos():
    try:
        registros = hoja_registro.get_all_values()[1:] 
        
        saldos = {"Banco": 0.0, "Cartera": 0.0, "Hucha": 0.0}
        
        for fila in registros:
            if len(fila) < 5: 
                continue 
                
            tipo = fila[1]
            cuenta = fila[2]
            
            texto_num = str(fila[3]).replace('€', '').replace(' ', '').replace(',', '.')
            cantidad = float(texto_num)
            
            if tipo == 'Ingreso' and cuenta in saldos:
                saldos[cuenta] += cantidad
            elif tipo == 'Gasto' and cuenta in saldos:
                saldos[cuenta] -= cantidad
                
        return saldos
    except Exception as e:
        print(f"Error al calcular saldos: {e}")
        return {"Banco": 0.0, "Cartera": 0.0, "Hucha": 0.0}

# ==========================================
# 4. COMANDOS DEL BOT
# ==========================================
@bot.message_handler(commands=["start"])
def enviar_bienvenida(mensaje):
    texto = (
        "¡Hola! Tu sistema financiero está listo ☁️💸\n\n"
        "Comandos disponibles:\n"
        "🟢 /ingreso [cantidad] [concepto]\n"
        "🔴 /gasto [cantidad] [concepto]\n"
        "🔄 /traspaso [cantidad] [origen] [destino]\n"
        "📊 /saldos (para ver tu dinero actual)"
    )
    bot.reply_to(mensaje, texto)

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
        cantidad_num = float(cantidad.replace(",", ".")) 
        
        saldos = obtener_saldos()
        dinero_total_previo = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        
        # REGLA: Si no hay en Cartera, sale del Banco
        if saldos["Cartera"] <= 0:
            cuenta_afectada = "Banco"
            aviso = "\n⚠️ *Atención:* Sacado del Banco porque la Cartera está a 0."
        else:
            cuenta_afectada = "Cartera"
            aviso = ""
            
        nuevo_saldo_total = dinero_total_previo - cantidad_num
            
        hoja_registro.append_row([fecha_actual, "Gasto", cuenta_afectada, cantidad_num, concepto, nuevo_saldo_total])
        
        saldos_nuevos = obtener_saldos()
        
        mensaje_final = f"📉 🔴 **¡Gasto apuntado!**\n"
        mensaje_final += f"Has gastado {cantidad_num}€ en: *{concepto}*{aviso}\n\n"
        mensaje_final += f"🏦 **Banco:** {saldos_nuevos['Banco']:.2f}€\n"
        mensaje_final += f"👛 **Cartera:** {saldos_nuevos['Cartera']:.2f}€\n"
        mensaje_final += f"🐷 **Hucha:** {saldos_nuevos['Hucha']:.2f}€\n"
        mensaje_final += f"➡️ **DINERO GLOBAL:** {nuevo_saldo_total:.2f}€"
        
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
        
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error: La cantidad debe ser un número (ej: 15.50).")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Hubo un problema: {e}")

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
        
        saldos = obtener_saldos()
        dinero_total_previo = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        nuevo_saldo_total = dinero_total_previo + cantidad_num
            
        hoja_registro.append_row([fecha_actual, "Ingreso", "Banco", cantidad_num, concepto, nuevo_saldo_total])
        
        saldos_nuevos = obtener_saldos()
        
        mensaje_final = f"📈 🟢 **¡Ingreso apuntado!**\n"
        mensaje_final += f"Has sumado {cantidad_num}€ de: *{concepto}*\n\n"
        mensaje_final += f"🏦 **Banco:** {saldos_nuevos['Banco']:.2f}€\n"
        mensaje_final += f"👛 **Cartera:** {saldos_nuevos['Cartera']:.2f}€\n"
        mensaje_final += f"🐷 **Hucha:** {saldos_nuevos['Hucha']:.2f}€\n"
        mensaje_final += f"➡️ **DINERO GLOBAL:** {nuevo_saldo_total:.2f}€"
        
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
        
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error: La cantidad debe ser un número (ej: 15.50).")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Hubo un problema: {e}")

@bot.message_handler(commands=['traspaso'])
def registro_traspaso(mensaje):
    trozos = mensaje.text.split(" ")
    
    if len(trozos) < 4:
        bot.reply_to(mensaje, "⚠️ Error. Úsalo así: /traspaso [cantidad] [origen] [destino]\nEjemplo: /traspaso 50 banco cartera")
        return
    
    cantidad = trozos[1]
    origen = trozos[2].capitalize()
    destino = trozos[3].capitalize()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cuentas_validas = ["Banco", "Cartera", "Hucha"]

    if origen not in cuentas_validas or destino not in cuentas_validas:
        bot.reply_to(mensaje, "⚠️ Error: Las cuentas deben ser Banco, Cartera o Hucha.")
        return

    try:
        cantidad_num = float(cantidad.replace(",", ".")) 
        
        saldos = obtener_saldos()
        dinero_total = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        
        # Guardamos las dos operaciones
        hoja_registro.append_row([fecha_actual, "Gasto", origen, cantidad_num, f"🔄 Traspaso a {destino}", dinero_total])
        hoja_registro.append_row([fecha_actual, "Ingreso", destino, cantidad_num, f"🔄 Traspaso desde {origen}", dinero_total])
        
        saldos_nuevos = obtener_saldos()
        
        mensaje_final = f"🔄 **¡Traspaso completado!**\n"
        mensaje_final += f"Has movido {cantidad_num}€ de *{origen}* a *{destino}*\n\n"
        mensaje_final += f"🏦 **Banco:** {saldos_nuevos['Banco']:.2f}€\n"
        mensaje_final += f"👛 **Cartera:** {saldos_nuevos['Cartera']:.2f}€\n"
        mensaje_final += f"🐷 **Hucha:** {saldos_nuevos['Hucha']:.2f}€\n"
        
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
        
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error: La cantidad debe ser un número (ej: 15.50).")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Hubo un problema al hacer el traspaso: {e}")

@bot.message_handler(commands=['saldos'])
def ver_saldos(mensaje):
    try:
        saldos = obtener_saldos()
        dinero_total = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        
        mensaje_final = f"📊 **RESUMEN DE TUS CUENTAS**\n\n"
        mensaje_final += f"🏦 **Banco:** {saldos['Banco']:.2f}€\n"
        mensaje_final += f"👛 **Cartera:** {saldos['Cartera']:.2f}€\n"
        mensaje_final += f"🐷 **Hucha:** {saldos['Hucha']:.2f}€\n"
        mensaje_final += f"➡️ **DINERO GLOBAL:** {dinero_total:.2f}€"
        
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Hubo un problema al leer los saldos: {e}")

# ==========================================
# 5. INICIAR EL BOT (Siempre al final)
# ==========================================
print("🤖 Bot encendido y esperando mensajes... 🚀")
bot.infinity_polling()