import telebot
import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from flask import Flask
from threading import Thread

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
# 4. COMANDOS DEL BOT (VERSIÓN INTERACTIVA)
# ==========================================
@bot.message_handler(commands=["start"])
def enviar_bienvenida(mensaje):
    texto = (
        "¡Hola! Tu sistema financiero está listo ☁️💸\n\n"
        "Comandos disponibles:\n"
        "🟢 /ingreso (Sumar dinero)\n"
        "🔴 /gasto (Restar dinero)\n"
        "🔄 /traspaso (Mover dinero)\n"
        "📊 /saldos (Ver tu dinero)\n"
        "⚙️ /retiro (Ajustar saldo)\n"
        "🎯 /meta (Fijar objetivo)\n"
        "⚖️ /cierre (Vaciado semanal)"
    )
    bot.reply_to(mensaje, texto)

# --- COMANDO: GASTO ---
@bot.message_handler(commands=['gasto'])
def preguntar_metodo_gasto(mensaje):
    teclado = telebot.types.InlineKeyboardMarkup()
    teclado.row(telebot.types.InlineKeyboardButton("💵 Efectivo", callback_data="gasto_efectivo_si"),
                telebot.types.InlineKeyboardButton("💳 Tarjeta/Banco", callback_data="gasto_efectivo_no"))
    bot.reply_to(mensaje, "👇 ¿Cómo has pagado este gasto?", reply_markup=teclado)

@bot.callback_query_handler(func=lambda call: call.data.startswith('gasto_efectivo_'))
def preguntar_datos_gasto(call):
    es_efectivo = "Si" if call.data == "gasto_efectivo_si" else "No"
    texto_elegido = "💵 Efectivo" if es_efectivo == "Si" else "💳 Tarjeta/Banco"
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=f"✅ Método: **{texto_elegido}**\n\n✍️ Escribe CANTIDAD y CONCEPTO.\n*(Ejemplo: 20 compra mercadona)*", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, guardar_gasto_final, es_efectivo)

def guardar_gasto_final(mensaje, es_efectivo):
    trozos = mensaje.text.split(" ", 1) 
    if len(trozos) < 2:
        bot.reply_to(mensaje, "⚠️ Error. Debes poner cantidad y concepto (Ej: 20 comida). Usa /gasto de nuevo.")
        return
    
    cantidad, concepto = trozos[0], trozos[1]
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        cantidad_num = float(cantidad.replace(",", ".")) 
        saldos = obtener_saldos()
        dinero_total_previo = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        
        if saldos["Cartera"] <= 0:
            cuenta_afectada, aviso = "Banco", "\n⚠️ *Atención:* Sacado del Banco porque la Cartera está a 0."
        else:
            cuenta_afectada, aviso = "Cartera", ""
            
        nuevo_saldo_total = dinero_total_previo - cantidad_num
        hoja_registro.append_row([fecha_actual, "Gasto", cuenta_afectada, cantidad_num, concepto, nuevo_saldo_total, es_efectivo])
        saldos_nuevos = obtener_saldos()
        
        mensaje_final = f"📉 🔴 **¡Gasto apuntado!**\nHas gastado {formato_eur(cantidad_num)}€ en: *{concepto}*{aviso}\n\n"
        mensaje_final += f"🏦 **Banco:** {formato_eur(saldos_nuevos['Banco'])}€\n👛 **Cartera:** {formato_eur(saldos_nuevos['Cartera'])}€\n🐷 **Hucha:** {formato_eur(saldos_nuevos['Hucha'])}€\n➡️ **DINERO GLOBAL:** {formato_eur(nuevo_saldo_total)}€"
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error numérico. Usa /gasto de nuevo.")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Error: {e}")

# --- COMANDO: INGRESO ---
@bot.message_handler(commands=['ingreso'])
def preguntar_metodo_ingreso(mensaje):
    teclado = telebot.types.InlineKeyboardMarkup()
    teclado.row(telebot.types.InlineKeyboardButton("💵 Efectivo", callback_data="ingreso_efectivo_si"),
                telebot.types.InlineKeyboardButton("💳 Tarjeta/Banco", callback_data="ingreso_efectivo_no"))
    bot.reply_to(mensaje, "👇 ¿Cómo ha entrado este dinero?", reply_markup=teclado)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ingreso_efectivo_'))
def preguntar_datos_ingreso(call):
    es_efectivo = "Si" if call.data == "ingreso_efectivo_si" else "No"
    texto_elegido = "💵 Efectivo" if es_efectivo == "Si" else "💳 Tarjeta/Banco"
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=f"✅ Método: **{texto_elegido}**\n\n✍️ Escribe CANTIDAD y CONCEPTO.\n*(Ejemplo: 50 regalo abuela)*", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, guardar_ingreso_final, es_efectivo)

def guardar_ingreso_final(mensaje, es_efectivo):
    trozos = mensaje.text.split(" ", 1)
    if len(trozos) < 2:
        bot.reply_to(mensaje, "⚠️ Error. Faltan datos. Usa /ingreso de nuevo.")
        return
    
    cantidad, concepto = trozos[0], trozos[1]
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        cantidad_num = float(cantidad.replace(",", ".")) 
        saldos = obtener_saldos()
        nuevo_saldo_total = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"] + cantidad_num
        
        hoja_registro.append_row([fecha_actual, "Ingreso", "Banco", cantidad_num, concepto, nuevo_saldo_total, es_efectivo])
        saldos_nuevos = obtener_saldos()
        
        mensaje_final = f"📈 🟢 **¡Ingreso apuntado!**\nHas sumado {formato_eur(cantidad_num)}€ en *Banco* de: *{concepto}*\n\n"
        mensaje_final += f"🏦 **Banco:** {formato_eur(saldos_nuevos['Banco'])}€\n👛 **Cartera:** {formato_eur(saldos_nuevos['Cartera'])}€\n🐷 **Hucha:** {formato_eur(saldos_nuevos['Hucha'])}€\n━━━━━━━━━━━━━━\n➡️ **DINERO GLOBAL:** {formato_eur(nuevo_saldo_total)}€\n"
        mensaje_final += f"   💵 En Efectivo: {formato_eur(saldos_nuevos['Total_Efectivo'])}€\n   💳 En Banco/Tarjeta: {formato_eur(saldos_nuevos['Total_Tarjeta'])}€"
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error numérico. Usa /ingreso de nuevo.")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Error: {e}")

# --- COMANDO: RETIRO ---
@bot.message_handler(commands=['retiro'])
def preguntar_cuenta_retiro(mensaje):
    teclado = telebot.types.InlineKeyboardMarkup()
    teclado.row(telebot.types.InlineKeyboardButton("🏦 Banco", callback_data="retiro_cuenta_Banco"),
                telebot.types.InlineKeyboardButton("👛 Cartera", callback_data="retiro_cuenta_Cartera"),
                telebot.types.InlineKeyboardButton("🐷 Hucha", callback_data="retiro_cuenta_Hucha"))
    bot.reply_to(mensaje, "👇 ¿De qué cuenta vas a retirar?", reply_markup=teclado)

@bot.callback_query_handler(func=lambda call: call.data.startswith('retiro_cuenta_'))
def preguntar_datos_retiro(call):
    cuenta = call.data.split("_")[2]
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=f"✅ Cuenta: **{cuenta}**\n\n✍️ Escribe CANTIDAD y CONCEPTO.\n*(Ej: 20 ajuste error)*", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, guardar_retiro_final, cuenta)

def guardar_retiro_final(mensaje, cuenta_afectada):
    trozos = mensaje.text.split(" ", 1)
    if len(trozos) < 2:
        bot.reply_to(mensaje, "⚠️ Error. Faltan datos. Usa /retiro de nuevo.")
        return
    
    cantidad, concepto = trozos[0], trozos[1]
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    try:
        cantidad_num = float(cantidad.replace(",", ".")) 
        saldos = obtener_saldos()
        nuevo_saldo_total = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"] - cantidad_num
        
        efectivo_previo = saldos["Cartera"] + saldos["Hucha"]
        nuevo_efectivo = efectivo_previo - cantidad_num if cuenta_afectada in ["Cartera", "Hucha"] else efectivo_previo 

        hoja_registro.append_row([fecha_actual, "Retiro", cuenta_afectada, cantidad_num, f"⚙️ {concepto}", nuevo_saldo_total, nuevo_efectivo])
        saldos_nuevos = obtener_saldos()
        
        mensaje_final = f"⚙️ 🔴 **¡Ajuste aplicado!**\nHas restado {formato_eur(cantidad_num)}€ de *{cuenta_afectada}* ({concepto})\n\n"
        mensaje_final += f"🏦 **Banco:** {formato_eur(saldos_nuevos['Banco'])}€\n👛 **Cartera:** {formato_eur(saldos_nuevos['Cartera'])}€\n🐷 **Hucha:** {formato_eur(saldos_nuevos['Hucha'])}€"
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error numérico. Usa /retiro de nuevo.")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Error: {e}")

# --- COMANDO: TRASPASO ---
@bot.message_handler(commands=['traspaso'])
def preguntar_origen_traspaso(mensaje):
    teclado = telebot.types.InlineKeyboardMarkup()
    teclado.row(telebot.types.InlineKeyboardButton("🏦 Banco", callback_data="trasp_orig_Banco"),
                telebot.types.InlineKeyboardButton("👛 Cartera", callback_data="trasp_orig_Cartera"),
                telebot.types.InlineKeyboardButton("🐷 Hucha", callback_data="trasp_orig_Hucha"))
    bot.reply_to(mensaje, "👇 ¿Desde dónde sale el dinero?", reply_markup=teclado)

@bot.callback_query_handler(func=lambda call: call.data.startswith('trasp_orig_'))
def preguntar_destino_traspaso(call):
    origen = call.data.split("_")[2]
    teclado = telebot.types.InlineKeyboardMarkup()
    for cuenta in ["Banco", "Cartera", "Hucha"]:
        if cuenta != origen:
            teclado.add(telebot.types.InlineKeyboardButton(f"➡️ Hacia {cuenta}", callback_data=f"trasp_dest_{origen}_{cuenta}"))
            
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=f"✅ Origen: **{origen}**\n👇 ¿A dónde va el dinero?", reply_markup=teclado)

@bot.callback_query_handler(func=lambda call: call.data.startswith('trasp_dest_'))
def preguntar_cantidad_traspaso(call):
    datos = call.data.split("_")
    origen, destino = datos[2], datos[3]
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=f"🔄 Traspaso: **{origen} ➡️ {destino}**\n\n✍️ Escribe solo la CANTIDAD.\n*(Ejemplo: 50)*", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, guardar_traspaso_final, origen, destino)

def guardar_traspaso_final(mensaje, origen, destino):
    try:
        cantidad_num = float(mensaje.text.replace(",", ".")) 
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
        saldos = obtener_saldos()
        dinero_total = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        
        hoja_registro.append_row([fecha_actual, "Gasto", origen, cantidad_num, f"🔄 A {destino}", dinero_total, "-"])
        hoja_registro.append_row([fecha_actual, "Ingreso", destino, cantidad_num, f"🔄 Desde {origen}", dinero_total, "-"])
        saldos_nuevos = obtener_saldos()
        
        mensaje_final = f"🔄 **¡Traspaso completado!**\nHas movido {formato_eur(cantidad_num)}€ de *{origen}* a *{destino}*\n\n"
        mensaje_final += f"🏦 **Banco:** {formato_eur(saldos_nuevos['Banco'])}€\n👛 **Cartera:** {formato_eur(saldos_nuevos['Cartera'])}€\n🐷 **Hucha:** {formato_eur(saldos_nuevos['Hucha'])}€"
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
    except ValueError:
         bot.reply_to(mensaje, "⚠️ Error. Debes escribir un número. Usa /traspaso de nuevo.")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Error: {e}")

# --- COMANDO: META ---
@bot.message_handler(commands=['meta'])
def preguntar_meta(mensaje):
    bot.reply_to(mensaje, "🎯 ¿Cuál es tu nuevo objetivo para la hucha?\n✍️ Escribe solo el número (Ej: 1500)")
    bot.register_next_step_handler(mensaje, guardar_meta_final)

def guardar_meta_final(mensaje):
    try:
        nueva_meta = float(mensaje.text.replace(",", "."))
        guardar_meta(nueva_meta)
        bot.reply_to(mensaje, f"🎯 ¡Meta actualizada! Tu nuevo objetivo es {formato_eur(nueva_meta)}€.")
    except ValueError:
        bot.reply_to(mensaje, "⚠️ Error. Debes escribir un número. Usa /meta de nuevo.")

# --- COMANDOS INSTANTÁNEOS (Sin botones) ---
@bot.message_handler(commands=['saldos'])
def ver_saldos(mensaje):
    try:
        saldos = obtener_saldos()
        dinero_total = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        meta_actual = obtener_meta()
        barra_hucha = barra_progreso(saldos['Hucha'], meta_actual)
        
        mensaje_final = f"📊 **RESUMEN DE TUS CUENTAS**\n\n"
        mensaje_final += f"🏦 **Banco:** {formato_eur(saldos['Banco'])}€\n"
        mensaje_final += f"👛 **Cartera:** {formato_eur(saldos['Cartera'])}€\n"
        mensaje_final += f"🐷 **Hucha:** {formato_eur(saldos['Hucha'])}€\n"
        mensaje_final += f"   🎯 Meta ({formato_eur(meta_actual)}€): {barra_hucha}\n"
        mensaje_final += f"━━━━━━━━━━━━━━\n"
        mensaje_final += f"➡️ **DINERO GLOBAL:** {formato_eur(dinero_total)}€\n"
        mensaje_final += f"   💵 En Efectivo: {formato_eur(saldos['Total_Efectivo'])}€\n"
        mensaje_final += f"   💳 En Banco/Tarjeta: {formato_eur(saldos['Total_Tarjeta'])}€"
        
        bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Error al leer los saldos: {e}")

@bot.message_handler(commands=['cierre'])
def cierre_semanal(mensaje):
    try:
        saldos = obtener_saldos()
        saldo_cartera = saldos["Cartera"]
        dinero_total = saldos["Banco"] + saldos["Cartera"] + saldos["Hucha"]
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")

        if saldo_cartera > 0:
            hoja_registro.append_row([fecha_actual, "Gasto", "Cartera", saldo_cartera, "🏁 Cierre: Vaciado de Cartera", dinero_total, "-"])
            hoja_registro.append_row([fecha_actual, "Ingreso", "Hucha", saldo_cartera, "🎉 Cierre: Ahorro semanal", dinero_total, "-"])
            saldos_nuevos = obtener_saldos()
            
            mensaje_final = f"🏆 **¡CIERRE SEMANAL SUPERADO!** 🏆\n\nTe han sobrado {formato_eur(saldo_cartera)}€.\nSe han guardado en tu **Hucha** 🐷.\n\n"
            mensaje_final += f"🏦 **Banco:** {formato_eur(saldos_nuevos['Banco'])}€\n👛 **Cartera:** {formato_eur(saldos_nuevos['Cartera'])}€\n🐷 **Hucha:** {formato_eur(saldos_nuevos['Hucha'])}€"
            bot.reply_to(mensaje, mensaje_final, parse_mode="Markdown")
        elif saldo_cartera == 0:
            bot.reply_to(mensaje, "⚖️ **CIERRE SEMANAL**\nHas clavado el presupuesto exacto. Tu Cartera está a 0€.", parse_mode="Markdown")
        else:
            bot.reply_to(mensaje, "⚠️ **NÚMEROS ROJOS**\nTu cartera está en negativo.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(mensaje, f"❌ Error al hacer el cierre: {e}")
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
@bot.message_handler(commands=['meta'])
def cambiar_meta(mensaje):
    trozos = mensaje.text.split(" ")
    if len(trozos) < 2:
        bot.reply_to(mensaje, "⚠️ Úsalo así: /meta [cantidad]\nEjemplo: /meta 1500")
        return
    
    try:
        nueva_meta = float(trozos[1].replace(",", "."))
        guardar_meta(nueva_meta)
        bot.reply_to(mensaje, f"🎯 ¡Meta actualizada! Tu nuevo objetivo de la Hucha es {formato_eur(nueva_meta)}€.")
    except ValueError:
        bot.reply_to(mensaje, "⚠️ Error: La cantidad debe ser un número (ej: 1500).")

def obtener_meta():
    """Lee la meta directamente desde la celda J1 de Google Sheets"""
    try:
        # Busca el valor en la celda J1
        valor = hoja_registro.acell('J1').value
        if valor is None or str(valor).strip() == "":
            return 1000.0
        return float(str(valor).replace(",", "."))
    except Exception:
        return 1000.0  # Meta por defecto si hay algún error

def guardar_meta(nueva_meta):
    """Guarda la nueva meta en la celda J1"""
    hoja_registro.update_acell('J1', nueva_meta)

def barra_progreso(saldo, meta):
    """Crea una barra de progreso visual tipo: [████░░░░░░] 40.0%"""
    if meta <= 0: return ""
    
    porcentaje = (saldo / meta) * 100
    # Limitamos la barra visual a 100 para que no se desborde si te pasas
    porcentaje_visual = min(porcentaje, 100) 
    
    # Calculamos cuántos bloques de 10 están llenos
    bloques_llenos = int(porcentaje_visual // 10)
    bloques_vacios = 10 - bloques_llenos
    
    barra = "█" * bloques_llenos + "░" * bloques_vacios
    return f"`[{barra}]` **{porcentaje:.1f}%**"
# ==========================================
import threading # Nos aseguramos de que esto esté cargado

# ==========================================
# 5. SERVIDOR WEB (Para engañar a Render) Y ARRANQUE
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "¡El bot de finanzas está funcionando perfectamente! 🚀"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    # Apagamos los mensajes molestos de Flask para ver solo nuestro bot
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=port)

print("🤖 Arrancando servidor web en segundo plano...")
# daemon=True es la clave: si el bot muere, la web muere y Render nos avisa
hilo_web = threading.Thread(target=run_web, daemon=True)
hilo_web.start()

print("🤖 Arrancando el bot de Telegram...")
try:
    # Borramos cualquier posible atasco previo en Telegram
    bot.remove_webhook() 
    print("✅ ¡Bot listo y esperando mensajes!")
    bot.infinity_polling()
except Exception as e:
    print(f"❌ ERROR CRÍTICO AL ARRANCAR EL BOT: {e}")
