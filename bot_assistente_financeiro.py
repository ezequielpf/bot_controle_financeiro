from flask import Flask, request
import os
import telebot
from telebot import types
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Autenticação com Google Sheets ===
escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credenciais = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", escopos)
cliente = gspread.authorize(credenciais)

# === Abre a planilha e seleciona a aba
planilha = cliente.open("Controle financeiro")
aba = planilha.worksheet("Auxiliar")

# === Lê as variáveis do arquivo .env --> APENA PARA TESTE LOCAL
#load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# === Inicia o bot
bot = telebot.TeleBot(TOKEN)

# === Configura o webhook
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL+"/webhook")

# === Dicionário global para armazenar o estado dos usuários
user_states = {}

# === Lista de usuários autorizados (coloque aqui os IDs permitidos) ===
USUARIOS_AUTORIZADOS = set(map(int, os.getenv("AUTHORIZED_USERS", "").split(",")))

# === Função para verificar se o usuário está listado
def usuario_autorizado(user_id: int) -> bool:
    return user_id in USUARIOS_AUTORIZADOS

# === Define o Flask app
app = Flask(__name__)

# Define a rota do webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid content type', 403


# === Mensagem inicial com botoes
@bot.message_handler(commands=['iniciar'])
def start(msg:telebot.types.Message):

    if not usuario_autorizado(msg.from_user.id):
        bot.send_message(msg.chat.id, "⛔ Você não está autorizado a usar este bot.")
        return
    
    # Cria os botões do menu
    keyboard = [
        [types.InlineKeyboardButton(text="➕ Adicionar novo gasto", callback_data="menu_adicionar")],
        [types.InlineKeyboardButton("➖ Remover último gasto", callback_data="menu_remover")], 
        [types.InlineKeyboardButton(text="📦 Outros", callback_data="menu_outros_n1")]
    ]

    markup = types.InlineKeyboardMarkup(keyboard)

    bot.send_message(
        chat_id=msg.chat.id,
        text="Olá! Eu sou seu assistente de finanças pessoas.\nComo posso ajudar?",
        reply_markup=markup
        )


# === Escutando o usuário
@bot.callback_query_handler()
def menu_handler(call:types.CallbackQuery):

    if not usuario_autorizado(call.from_user.id):
        bot.send_message(call.message.chat.id, "⛔ Você não está autorizado a usar este bot.")
        return

    query = call.data
    
    # Nível 1
    if query == "menu_adicionar":

        keyboard = [
            [types.InlineKeyboardButton(text="🚗 Uber", callback_data="gasto_uber")],
            [types.InlineKeyboardButton(text="📦 Outros", callback_data="menu_outros_n2")]
        ]

        reply_markup = types.InlineKeyboardMarkup(keyboard)

        bot.send_message(
            chat_id=call.message.chat.id,
            text="Escolha a categoria:",
            reply_markup=reply_markup
        )

    elif query == "menu_remover":

        try:
            registros = aba.get_all_values()

            if not registros or len(registros) == 0:
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text="⚠️ Nenhum gasto registrado ainda."
                )
                return
            
            # Garante que o cabeçalho não será removido
            elif len(registros) <= 1:
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text="⚠️ Nenhum gasto para remover."
                )
                return

            # Posição da última linha
            ultima_linha = len(registros)
            ultimo_valor = registros[-1][2]
            aba.delete_rows(ultima_linha)

            bot.send_message(
                    chat_id=call.message.chat.id,
                    text=f"✅ Último gasto, no valor de R$ {ultimo_valor}, removido com sucesso."
                )
        
        except Exception as e:
            bot.send_message(
                    chat_id=call.message.chat.id,
                    text=f"⚠️ Erro ao remover {e}."
                )

    elif query == "menu_outros_n1":

        bot.send_message(
            chat_id=call.message.chat.id,
            text="❌ Funcionalidade não disponível no momento."
        )

    # Nível 2
    elif query == "menu_outros_n2":

        bot.send_message(
            chat_id=call.message.chat.id,
            text="❌ Funcionalidade não disponível no momento."
        )

    elif query == "gasto_uber":

        user_states[call.from_user.id] = "waiting_uber_value"
        bot.send_message(
            chat_id=call.message.chat.id,
            text="Você escolheu: Gasto com Uber.\nQual foi o valor (R$)?"
        )



# === Respondendo ao usuário
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_uber_value")
def receber_valor_uber(message:telebot.types.Message):

    if not usuario_autorizado(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ Você não está autorizado a usar este bot.")
        return
    
    try:
        valor = float(message.text.replace(",", "."))
        data = datetime.now().strftime("%d/%m/%Y")
        # Escrever na aba do google sheets
        aba.append_row([data, "Uber", f"{valor:.2f}".replace(".", ",")])
        bot.send_message(
             chat_id=message.chat.id,
             text=(f"✅ Você registrou R$ {valor:.2f}".replace('.', ','))
         )
    except ValueError:
        bot.send_message(
             chat_id=message.chat.id,
             text=("❌ Por favor, digite um valor numérico. Ex: 23.50 ou 23,50")
         )
    
    # Limpa o estado do usuário
    user_states.pop(message.from_user.id, None)
           

# Opcional: rota para testar se o app está vivo
@app.route('/')
def index():
    return "Bot está rodando!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)