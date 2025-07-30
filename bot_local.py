from telegram import Update
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import ContextTypes
from telegram.ext import filters
from telegram.ext import CallbackQueryHandler

import csv
from datetime import datetime
from os.path import exists

CSV_FILE = "gastos.csv"

if not exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["data", "categoria", "valor"])


# Comando /start
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


# Manipula os botões do menu
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
            with open(CSV_FILE, "r", encoding="utf-8") as f:
                linhas = f.readlines()

            if not linhas:
                await query.edit_message_text("⚠️ Nenhum gasto registrado ainda.")
                return

            # Remove a última linha
            ultimo = linhas.pop()
            #linhas = linhas[:-1]

            with open(CSV_FILE, "w", encoding="utf-8") as f:
                f.writelines(linhas)

            await query.edit_message_text(f"✅ Último gasto, no valor de R$ {ultimo.strip().split(',')[-1]}, removido com sucesso.")
        
        except FileNotFoundError:
            await query.edit_message_text("⚠️ Arquivo de registro não encontrado.")

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


# Responder qualquer texto enviado
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    texto = update.message.text

    if context.user_data.get("modo") == "gasto_uber":
        try:
            valor = float(texto.replace(",", "."))
            data = datetime.now().strftime("%d/%m/%Y")

            # Salva no csv
            with open(file=CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([data, "Uber", f'{valor:.2f}'])

            await update.message.reply_text(f"✅ Você registrou R$ {valor:.2f}".replace('.', ','))
            
            # Limpa o estado
            context.user_data["modo"] = None

        except ValueError:
            await update.message.reply_text("❌ Por favor, digite um valor numérico. Ex: 23.50 ou 23,50")
    else:
        await update.message.reply_text("ℹ️ Para registrar um gasto, clique primeiro no menu /iniciar.")


# Inicialização do bot
if __name__ == '__main__':

    with open("token.txt") as tofenfile:
        token = tofenfile.read()

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("iniciar", start))
    app.add_handler(CallbackQueryHandler(menu_handler)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("Bot iniciado...")
    app.run_polling()