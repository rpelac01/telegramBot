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
        
        saldos = {
            "Banco": 0.0, "Cartera": 0.0, "Hucha": 0.0,
            "Total_Efectivo": 0.0, "Total_Tarjeta": 0.0
        }
        
        for fila in registros:
            if len(fila) < 4: 
                continue 
                
            tipo = fila[1]
            cuenta = fila[2]
            
            # Limpiamos y convertimos la cantidad (Columna D)
            texto_num = str(fila[3]).replace('€', '').replace(' ', '').replace(',', '.')
            cantidad = float(texto_num)
            
            # Limpiamos el texto de Efectivo (Columna G) a prueba de errores
            if len(fila) >= 7:
                # .strip() quita espacios fantasma y .lower() lo pasa a minúsculas
                es_efectivo = str(fila[6]).strip().lower()
            else:
                es_efectivo = "no"
                
            # 1. Sumamos/Restamos a las cuentas normales
            if tipo == 'Ingreso' and cuenta in saldos:
                saldos[cuenta] += cantidad
            elif tipo == 'Gasto' and cuenta in saldos:
                saldos[cuenta] -= cantidad
                
            # 2. Sumamos/Restamos a los globales (Efectivo vs Tarjeta)
            if es_efectivo != "-": 
                if tipo == 'Ingreso':
                    # Ahora da igual si pones "Si ", "SI", " sí " o "si"... lo va a detectar
                    if es_efectivo in ["si", "sí"]: 
                        saldos["Total_Efectivo"] += cantidad
                    else: 
                        saldos["Total_Tarjeta"] += cantidad
                elif tipo == 'Gasto':
                    if es_efectivo in ["si", "sí"]: 
                        saldos["Total_Efectivo"] -= cantidad
                    else: 
                        saldos["Total_Tarjeta"] -= cantidad
                
        return saldos
    except Exception as e:
        print(f"Error al calcular saldos: {e}")
        return {"Banco": 0.0, "Cartera": 0.0, "Hucha": 0.0, "Total_Efectivo": 0.0, "Total_Tarjeta": 0.0}
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
            
        hoja_registro.append_row([fecha_actual, "Gasto", cuenta_afectada, cantidad_num, concepto, nuevo_saldo_total, es_efectivo])
        
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
            
        hoja_registro.append_row([fecha_actual, "Ingreso", "Banco", cantidad_num, concepto, nuevo_saldo_total, "No"])
        
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
        hoja_registro.append_row([fecha_actual, "Gasto", origen, cantidad_num, f"🔄 A {destino}", dinero_total, "-"])
        hoja_registro.append_row([fecha_actual, "Ingreso", destino, cantidad_num, f"🔄 Desde {origen}", dinero_total, "-"])
        
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
        mensaje_final += f"🏦 **Banco:** {formato_eur(saldos['Banco'])}€\n"
        mensaje_final += f"👛 **Cartera:** {formato_eur(saldos['Cartera'])}€\n"
        mensaje_final += f"🐷 **Hucha:** {formato_eur(saldos['Hucha'])}€\n"
        mensaje_final += f"━━━━━━━━━━━━━━\n"
        mensaje_final += f"➡️ **DINERO GLOBAL:** {formato_eur(dinero_total)}€\n"
        mensaje_final += f"   💵 En Efectivo: {formato_eur(saldos['Total_Efectivo'])}€\n"
        mensaje_final += f"   💳 En Banco/Tarjeta: {formato_eur(saldos['Total_Tarjeta'])}€"
        
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Hubo un problema al leer los saldos: {e}")
@bot.message_handler(commands=['retiro'])
def registro_retiro(mensaje):
    # Separamos en 4 partes: comando, cantidad, cuenta, concepto
    trozos = mensaje.text.split(" ", 3) 
    
    if len(trozos) < 4:
        bot.reply_to(mensaje, "⚠️ Error. Úsalo así: /retiro [cantidad] [cuenta] [concepto]\nEjemplo: /retiro 50 Banco Error tecleo")
        return
    
    cantidad = trozos[1]
    cuenta_afectada = trozos[2].capitalize()
    concepto = trozos[3]
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cuentas_validas = ["Banco", "Cartera", "Hucha"]

    if cuenta_afectada not in cuentas_validas:
        bot.reply_to(mensaje, "⚠️ Error: Las cuentas deben ser Banco, Cartera o Hucha.")
        return

    try:
        cantidad_num = float(cantidad.replace(",", ".")) 
        
        saldos = obtener_saldos()
        dinero_total_previo = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        nuevo_saldo_total = dinero_total_previo - cantidad_num
            
        # Lo guardamos como un gasto específico en esa cuenta
        hoja_registro.append_row([fecha_actual, "Gasto", cuenta_afectada, cantidad_num, f"⚙️ {concepto}", nuevo_saldo_total, "-"])
        
        saldos_nuevos = obtener_saldos()
        
        mensaje_final = f"⚙️ 🔴 **¡Ajuste aplicado!**\n"
        mensaje_final += f"Has restado {formato_eur(cantidad_num)}€ de *{cuenta_afectada}* ({concepto})\n\n"
        mensaje_final += f"🏦 **Banco:** {formato_eur(saldos_nuevos['Banco'])}€\n"
        mensaje_final += f"👛 **Cartera:** {formato_eur(saldos_nuevos['Cartera'])}€\n"
        mensaje_final += f"🐷 **Hucha:** {formato_eur(saldos_nuevos['Hucha'])}€\n"
        
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
        
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error: La cantidad debe ser un número (ej: 15.50).")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Hubo un problema al hacer el ajuste: {e}")
# ==========================================
def formato_eur(numero):
    """Convierte 1250.5 a '1.250,50'"""
    texto = f"{numero:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return texto
@bot.message_handler(commands=['cierre'])
def cierre_semanal(mensaje):
    try:
        saldos = obtener_saldos()
        saldo_cartera = saldos["Cartera"]
        dinero_total = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")

        if saldo_cartera > 0:
            # 1. Sacamos el sobrante de la Cartera
            hoja_registro.append_row([fecha_actual, "Gasto", "Cartera", saldo_cartera, "🏁 Cierre: Vaciado de Cartera", dinero_total, "-"])
            # 2. Lo metemos en la Hucha como premio
            hoja_registro.append_row([fecha_actual, "Ingreso", "Hucha", saldo_cartera, "🎉 Cierre: Ahorro semanal", dinero_total, "-"])
            
            saldos_nuevos = obtener_saldos()
            
            mensaje_final = f"🏆 **¡CIERRE SEMANAL SUPERADO!** 🏆\n\n"
            mensaje_final += f"¡Enhorabuena! Te han sobrado {formato_eur(saldo_cartera)}€ en tu presupuesto.\n"
            mensaje_final += f"Ese dinero se ha guardado automáticamente en tu **Hucha** 🐷.\n\n"
            mensaje_final += f"📊 **TUS NUEVOS SALDOS:**\n"
            mensaje_final += f"🏦 **Banco:** {formato_eur(saldos_nuevos['Banco'])}€\n"
            mensaje_final += f"👛 **Cartera:** {formato_eur(saldos_nuevos['Cartera'])}€ *(Lista para recargar)*\n"
            mensaje_final += f"🐷 **Hucha:** {formato_eur(saldos_nuevos['Hucha'])}€\n"
            
            bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")

        elif saldo_cartera == 0:
            mensaje_final = f"⚖️ **CIERRE SEMANAL** ⚖️\n\n"
            mensaje_final += "Has clavado el presupuesto exacto. Tu Cartera está a 0€.\n"
            mensaje_final += "No hay ahorros extra esta semana, pero al menos no has tenido que tirar del Banco. ¡Lista para la recarga! 🔋\n"
            
            bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
            
        else:
            mensaje_final = f"⚠️ **CIERRE SEMANAL: NÚMEROS ROJOS** ⚠️\n\n"
            mensaje_final += "Tu cartera está en negativo. Recuerda ajustar mejor el presupuesto la próxima semana para no tener que tirar de tus ahorros.\n"
            
            bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
            
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Hubo un problema al hacer el cierre: {e}")
# 5. INICIAR EL BOT (Siempre al final)
# ==========================================
print("🤖 Bot encendido y esperando mensajes... 🚀")
bot.infinity_polling()