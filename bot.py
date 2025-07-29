from telegram import Update
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import ContextTypes
from telegram.ext import filters
from telegram.ext import CallbackQueryHandler


# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Cria os botões do menu
    keyboard = [
        [InlineKeyboardButton(text="Adicionar Gasto com Uber", callback_data="enviar_gasto_uber")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text="Olá! Eu sou seu assistente de finanças pessoas.\nComo posso ajudar?",
        reply_markup=reply_markup
        )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    query = update.callback_query
    # Confirma o clique (evita "loading...")
    await query.answer()

    # Marca que estamos esperando um valor de gasto
    context.user_data["modo"] = "gasto_uber"

    await query.edit_message_text("Você escolheu: Gasto com Uber.\nQual foi o valor (R$)?")


# Responder qualquer texto enviado
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    texto = update.message.text

    if context.user_data.get("modo") == "gasto_uber":
        try:
            valor = float(texto.replace(",", "."))
            await update.message.reply_text(f"✅ Você registrou R$ {valor:.2f}".replace('.', ','))
             # Limpa o estado
            context.user_data["modo"] = None

        except ValueError:
            await update.message.reply_text("❌ Por favor, digite um valor numérico. Ex: 23.50 ou 23,50")
    else:
        await update.message.reply_text("ℹ️ Para registrar um gasto, clique primeiro no menu /start.")


# Inicialização do bot
if __name__ == '__main__':

    with open("token.txt") as tofenfile:
        token = tofenfile.read()

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_handler)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("Bot iniciado...")
    app.run_polling()