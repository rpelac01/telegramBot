# Bot de telegram para el control de gastos 💸

¡Proyecto de verano! 
## Problema que me resuelve:
La ambicion de crear una herramienta propia para, en este caso, controlar mis gastos y ganancias tanto de gastos bancarios tanto efectivo.
##  Arquitectura del Sistema
El proyecto funciona bajo un modelo de comunicación sencilla usando la API de Telegram:
1. **Cliente:** El usuario envía el comando desde la app de Telegram.
2. **API (Intermediario):** Telegram recibe el mensaje y lo pone a disposición del bot.
3. **Servidor (Python):** Un script en ejecución constante detecta el mensaje, extrae los datos (cantidad, categoría) y los procesa.
4. **Almacenamiento:** Los datos se guardan para calcular balances y progreso de objetivos.
##  Tecnologías Utilizadas
* **Lenguaje:** Python 3.x
* **Librerías:** `python-telegram-bot` (por definir)
* **Entorno:** Linux / VS Code
##  Roadmap y Diario de Desarrollo
Aquí iré documentando mi progreso en el proyecto:
- [x] Definir la idea y arquitectura básica del bot.
- [x] Configurar repositorio y claves SSH en GitHub.
- [x] Obtener el Token en BotFather (Telegram).
- [x] Hola Mundo en Python conectando con la API.
- [x] Lógica para guardar el primer gasto.
- [x] Implementar sistema de "Barra de salud" y "Objetivos/Bote".
## 🏗️ La Nueva Arquitectura de tus Cuentas
Tu sistema ahora se divide en tres bloques independientes:

🏦 Total (El Banco): Tu cuenta principal. Recibe tu nómina o ingresos principales.

👛 Cartera (La Semana): Tu saldo "líquido" para el día a día. Se alimenta del Banco. Aquí es donde registrarás los gastos de cafés, cenas, etc.

🐷 Hucha (Ahorro Intocable): Un agujero negro positivo. Lo que entra aquí, no sale para gastos corrientes.

## 🤖 Comandos del Bot

Aquí tienes la lista completa de comandos disponibles para gestionar las finanzas desde Telegram:

* **`/start`** - Muestra el mensaje de bienvenida y el resumen de los comandos básicos.
* **`/ingreso [cantidad] [concepto]`** - Añade dinero directamente a la cuenta principal (Banco). Por defecto, asume que es dinero digital (transferencia/tarjeta).
  * *Ejemplo:* `/ingreso 1200 Nómina mes de julio`
* **`/gasto [cantidad] [concepto] [si/no]`** - Registra un gasto. Si hay saldo en la *Cartera*, lo resta de ahí; si está a cero, lo resta del *Banco*. El último parámetro (opcional) indica si el pago fue en efectivo (`si`) o con tarjeta (`no`). Si se omite, asume que es tarjeta.
  * *Ejemplo:* `/gasto 2.50 Café si`
* **`/traspaso [cantidad] [origen] [destino]`** - Mueve fondos entre las tres cuentas disponibles (Banco, Cartera, Hucha) sin alterar el saldo global.
  * *Ejemplo:* `/traspaso 50 Banco Cartera`
* **`/retiro [cantidad] [cuenta] [concepto]`** - Fuerza la resta de una cantidad específica de una cuenta. Ideal para corregir errores manuales (ajustes).
  * *Ejemplo:* `/retiro 15 Banco Error al teclear gasto anterior`
* **`/saldos`** - Imprime un ticket virtual con el estado actual de todas las cuentas, el dinero global, un desglose exacto (Efectivo vs Tarjeta) y la barra de progreso de tu objetivo de ahorro.
* **`/meta [cantidad]`** - Establece tu objetivo económico para la Hucha. Modifica la barra de progreso visible en tus saldos.
  * *Ejemplo:* `/meta 1500`
* **`/cierre`** - Ejecuta la rutina de cierre semanal. Calcula cuánto dinero te ha sobrado en la *Cartera*, lo mueve automáticamente a la *Hucha* como recompensa de ahorro, y deja la Cartera a 0€ lista para la siguiente semana.