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
- [ ] Obtener el Token en BotFather (Telegram).
- [ ] Hola Mundo en Python conectando con la API.
- [ ] Lógica para guardar el primer gasto.
- [ ] Implementar sistema de "Barra de salud" y "Objetivos/Bote".