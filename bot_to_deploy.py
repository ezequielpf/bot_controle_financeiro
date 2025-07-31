from telegram import Update
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import ContextTypes
from telegram.ext import filters
from telegram.ext import CallbackQueryHandler

from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import os

# === Autenticação com Google Sheets ===
escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credenciais = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", escopos)
cliente = gspread.authorize(credenciais)


# === Abre a planilha e seleciona a aba
planilha = cliente.open("Controle financeiro")
aba = planilha.worksheet("Auxiliar")


# === Comando /iniciar
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Cria os botões do menu
    keyboard = [
        [InlineKeyboardButton(text="➕ Adicionar novo gasto", callback_data="menu_adicionar")],
        [InlineKeyboardButton("➖ Remover último gasto", callback_data="menu_remover")], 
        [InlineKeyboardButton(text="📦 Outros", callback_data="menu_outros_n1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text="Olá! Eu sou seu assistente de finanças pessoas.\nComo posso ajudar?",
        reply_markup=reply_markup
        )


# === Manipula os cliques nos botões
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    query = update.callback_query
    # Confirma o clique (evita "loading...")
    await query.answer()

    # Retorna qual o contexto estamos
    data = query.data

    # Nível 1: Adicionar
    if data == "menu_adicionar":

        keyboard = [
            [InlineKeyboardButton(text="🚗 Uber", callback_data="gasto_uber")],
            [InlineKeyboardButton(text="📦 Outros", callback_data="menu_outros_n2")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text="Escolha a categoria:", reply_markup=reply_markup)

    # Nível 1: Desfazer
    elif data == "menu_remover":
        try:
            registros = aba.get_all_values()

            if not registros or len(registros) == 0:
                await query.edit_message_text("⚠️ Nenhum gasto registrado ainda.")
                return

            # Posição da última linha
            ultima_linha = len(registros)
            ultimo_valor = registros[-1][2]
            aba.delete_rows(ultima_linha)
            
            await query.edit_message_text(f"✅ Último gasto, no valor de R$ {ultimo_valor}, removido com sucesso.")
        
        except Exception as e:
            await query.edit_message_text(f"⚠️ Erro ao remover {e}.")

    # Nível 1: Outros
    elif data == "menu_outros_n1":
        await query.edit_message_text("❌ Funcionalidade não disponível no momento.") 

    # Nível 2: Outros
    elif data == "menu_outros_n2":
        await query.edit_message_text("❌ Funcionalidade não disponível no momento.")

    # Nível 2: Uber
    elif data == "gasto_uber":
        context.user_data["modo"] = "gasto_uber"
        await query.edit_message_text("Você escolheu: Gasto com Uber.\nQual foi o valor (R$)?")


# === Responder qualquer texto enviado
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    texto = update.message.text

    if context.user_data.get("modo") == "gasto_uber":
        try:
            valor = float(texto.replace(",", "."))
            data = datetime.now().strftime("%d/%m/%Y")

            # Escrever na aba do google sheets
            aba.append_row([data, "Uber", f"{valor:.2f}".replace(".", ",")])

            await update.message.reply_text(f"✅ Você registrou R$ {valor:.2f}".replace('.', ','))
            
            # Limpa o estado
            context.user_data["modo"] = None

        except ValueError:
            await update.message.reply_text("❌ Por favor, digite um valor numérico. Ex: 23.50 ou 23,50")
    else:
        await update.message.reply_text("ℹ️ Para registrar um gasto, clique primeiro no menu /iniciar.")


# Inicialização do bot
if __name__ == '__main__':

    TOKEN = os.getenv("BOT_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("iniciar", start))
    app.add_handler(CallbackQueryHandler(menu_handler)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("Bot iniciado...")
    app.run_polling()