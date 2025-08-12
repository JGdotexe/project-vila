from datetime import datetime
from telegram import  constants, Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import logging
import os
import gspread
from google import genai
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USER_NAME = 'ai4vila_bot'

if not TOKEN:
    raise ValueError("Variável de ambiente TELEGRAM_TOKEN não encontrada!")
if not GEMINI_API_KEY:
    raise ValueError("Variável de ambiente GEMINI_API_KEY não encontrada!")

client = genai.Client(api_key=GEMINI_API_KEY)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

SHEETS_CREDENTIALS_FILE = "credentials.json"
SHEETS_FUNCIONARIOS = "Funcionarios_Bot"
SHEETS_LOG_NAME = "Log_Feedback_Bot"

try:
    print("A autenticar com a API do Google Sheets..")
    gc = gspread.service_account(filename=SHEETS_CREDENTIALS_FILE)
    users_sheet = gc.open(SHEETS_FUNCIONARIOS).sheet1
    log_sheet = gc.open(SHEETS_LOG_NAME).sheet1
    print("Conexão com Google Sheets bem sucedida")
except Exception as e:
    logging.error(f"Erro ao chamar a API do Sheets: {e}")
    exit()

ASKING_FEEDBACK = 1
ASKING_NAME = 2
ASKING_CARGO = 3

def get_user_data(user_id: int):
    try:
        all_users = users_sheet.get_all_records()
        for user in all_users:
            if str(user['telegram_user_id']) == str(user_id):
                logging.info(f"Utilizador {user_id} encontrado: {user['nome_completo']}, Cargo:{ user['cargo']}")
                return user
        return None
    except Exception as e:
        logging.error(f"Erro ao ler a planilha de funcionários: {e}")
        return None

def save_feedback(user_data: dict,  feedback_text: str):
    try:
        user_id_str = str(user_data['telegram_user_id'])
        cell = log_sheet.find(user_id_str)
        if not cell:
            logging.error(f"Utilizador {user_data['nome_completo']} não encontrado na planilha de log.")
            return False

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_sheet.update_cell(cell.row, 4, feedback_text)
        log_sheet.update_cell(cell.row, 5, timestamp)

        logging.info(f"Feedback de {user_data['nome_completo']} salvo com sucesso.")
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar feedback na planilha: {e}")
        return False

def save_new_user(user_id: int, nome: str, cargo: str):
    try:
        new_row_funcionarios = [str(user_id), nome, cargo]
        users_sheet.append_row(new_row_funcionarios)

        new_row_feedback = [str(user_id), nome, cargo, "", ""]
        log_sheet.append_row(new_row_feedback)

        return True
    except Exception as e:
        logging.error(f"Erro ao salvar novo usuário: {e}")
        return False

def load_prompt(file_path: str, user_data: dict) -> str:
    """Lê o prompt de um arquivo e insere os dados do usuário."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            template = f.read()
        return template.format(
            nome_completo=user_data['nome_completo'],
            cargo=user_data['cargo']
        )
    except Exception as e:
        logging.error(f"Erro ao carregar prompt: {e}")
        return None

async def start_command(update, context):
    user = update.effective_user
    await update.message.reply_text(f"Olá {user.first_name}! bem vindo ao chat de suporte")

    await update.message.reply_text(
        "Olá! Eu sou o chat de comunicação interna do Vilarejo.\n\n"
        "📌 Comandos disponíveis:\n"
        "/sounovo - Se é a sua primeira vez usando o chat use /sounovo para se cadastrar\n"
        "/feedback - digite /feedback para enviar seu feedback a qualquer hora\n"
        "/cancelar - Cancelar uma operação"
    )

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    if not user_data:
        await update.message.reply_text("Você ainda não está cadastrado! Use /sounovo primeiro.")
        return ConversationHandler.END
    context.user_data['info'] = user_data

    prompt = load_prompt("prompt_feedback.txt", user_data)
    if not prompt:
        await update.message.reply_text("Erro ao carregar perguntas. Contate o suporte")
        return ConversationHandler.END

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        await update.message.reply_text(response.text, parse_mode=constants.ParseMode.MARKDOWN)
    except Exception as e:
        logging.error(f"Erro ao chamar a API do Gemini: {e}")
        await update.message.reply_text("Não Consegui gerar as perguntas agora. Tente novamente mais tarde.")
        return ConversationHandler.END
    return ASKING_FEEDBACK

async def receive_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    feedback_text = update.message.text
    user_data = context.user_data.get('info')

    if not user_data:
        await update.message.reply_text("Ocorreu um erro ao recuperar os seus dados. Por Favor, comece novamente com /start")
        return ConversationHandler.END
    
    if save_feedback(user_data, feedback_text):
        await update.message.reply_text("Muito obrigado pelo seu feedback! a sua opnião é valiosa.")
    else:
        await update.message.reply_text("Obrigado pelo feedback! tice um problema ao registralo. Por favor, contacte o supoerte")

    context.user_data.clear()
    return ConversationHandler.END

async def sou_novo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("qual é o seu nome completo?")
    return ASKING_NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nome'] = update.message.text
    await update.message.reply_text("Qual é o seu cargo?")
    return ASKING_CARGO

async def receive_cargo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = context.user_data.get('nome')
    cargo = update.message.text
    user_id = update.effective_user.id

    if save_new_user(user_id, nome, cargo):
        await update.message.reply_text(f"Cadastro concluído! Bem vindo {nome}!")
    else:
        await update.message.reply_text(f"Erro ao registrar seu cadastro")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operação cancelada. Se precisar, de algo mais, estou aqui")
    context.user_data.clear()
    return ConversationHandler.END


async def handle_message(update, context):
    user= update.effective_user
    chat_id = update.effective_chat.id
    user_message = update.message.text

    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

    try:
        logging.info(f"enviando para o Gemini:'{user_message}'")
        response = client.models.generate_content(
            model='gemini-1.5-flash'
            , contents=user_message
        )
        await update.message.reply_text(response.text, parse_mode=constants.ParseMode.MARKDOWN)
        logging.info("Resposta do Gemini enviada com sucesso")
    except Exception as e:
        logging.error(f"Erro ao chamar a API do Gemini: {e}")
        await update.message.reply_text("Desculpe, ocorreu um erro ao tentar gerar uma resposta.")

def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    feedback_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", feedback_command)],
        states={
            ASKING_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_feedback)]
        },
        fallbacks=[CommandHandler("cancelar", cancel_command)]
    )

    cadastro_handler = ConversationHandler(
        entry_points=[CommandHandler("sounovo", sou_novo_command)],
        states={
            ASKING_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            ASKING_CARGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_cargo)]
        },
        fallbacks=[CommandHandler("cancelar", cancel_command)]
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(feedback_handler)
    application.add_handler(cadastro_handler)

    print("Bot iniciando!")
    application.run_polling(3)


if __name__ == "__main__":
    main()


