from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# === Autorização ===
USUARIOS_AUTORIZADOS = set(map(int, os.getenv("AUTHORIZED_USERS", "").split(",")))

# === Google Sheets ===
escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credenciais = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", escopos)
cliente = gspread.authorize(credenciais)
planilha = cliente.open("Controle financeiro")
aba = planilha.worksheet("Auxiliar")

def usuario_autorizado(update: Update) -> bool:
    user_id = update.effective_user.id
    return user_id in USUARIOS_AUTORIZADOS

# === Handlers síncronos ===
def start(update: Update, context):
    if not usuario_autorizado(update):
        update.message.reply_text("❌ Acesso negado.")
        return

    keyboard = [
        [InlineKeyboardButton(text="➕ Adicionar novo gasto", callback_data="menu_adicionar")],
        [InlineKeyboardButton("➖ Remover último gasto", callback_data="menu_remover")],
        [InlineKeyboardButton(text="📦 Outros", callback_data="menu_outros_n1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        text="Olá! Eu sou seu assistente de finanças pessoas.\nComo posso ajudar?",
        reply_markup=reply_markup
    )

def menu_handler(update: Update, context):
    query = update.callback_query
    if not usuario_autorizado(update):
        query.answer("❌ Acesso negado.", show_alert=True)
        return

    query.answer()
    data = query.data

    if data == "menu_adicionar":
        keyboard = [
            [InlineKeyboardButton(text="🚗 Uber", callback_data="gasto_uber")],
            [InlineKeyboardButton(text="📦 Outros", callback_data="menu_outros_n2")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("Escolha a categoria:", reply_markup=reply_markup)

    elif data == "menu_remover":
        try:
            registros = aba.get_all_values()
            if not registros:
                query.edit_message_text("⚠️ Nenhum gasto registrado ainda.")
                return

            ultima_linha = len(registros)
            ultimo_valor = registros[-1][2]
            aba.delete_rows(ultima_linha)
            query.edit_message_text(f"✅ Último gasto, no valor de R$ {ultimo_valor}, removido com sucesso.")
        except Exception as e:
            query.edit_message_text(f"⚠️ Erro ao remover {e}.")

    elif data == "menu_outros_n1" or data == "menu_outros_n2":
        query.edit_message_text("❌ Funcionalidade não disponível no momento.")

    elif data == "gasto_uber":
        context.user_data["modo"] = "gasto_uber"
        query.edit_message_text("Você escolheu: Gasto com Uber.\nQual foi o valor (R$)?")

def responder(update: Update, context):
    if not usuario_autorizado(update):
        update.message.reply_text("❌ Acesso negado.")
        return

    texto = update.message.text

    if context.user_data.get("modo") == "gasto_uber":
        try:
            valor = float(texto.replace(",", "."))
            data = datetime.now().strftime("%d/%m/%Y")
            aba.append_row([data, "Uber", f"{valor:.2f}".replace(".", ",")])
            update.message.reply_text(f"✅ Você registrou R$ {valor:.2f}".replace(".", ","))
            context.user_data["modo"] = None
        except ValueError:
            update.message.reply_text("❌ Por favor, digite um valor numérico. Ex: 23.50 ou 23,50")
    else:
        update.message.reply_text("ℹ️ Para registrar um gasto, clique primeiro no menu /iniciar.")

# === Flask App e Telegram App ===
app_flask = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")

application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("iniciar", start))
application.add_handler(CallbackQueryHandler(menu_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

# Webhook síncrono
@app_flask.route("/", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

@app_flask.route("/", methods=["GET"])
def index():
    return "Bot rodando com webhook!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app_flask.run(port=port, host="0.0.0.0")
