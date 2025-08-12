import random
from datetime import datetime, timedelta
import gspread
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente (se precisar)
load_dotenv()

SHEETS_CREDENTIALS_FILE = "credentials.json"
SHEETS_FUNCIONARIOS = "Funcionarios_Bot"
SHEETS_LOG_NAME = "Log_Feedback_Bot"

# Conectar ao Google Sheets
gc = gspread.service_account(filename=SHEETS_CREDENTIALS_FILE)
users_sheet = gc.open(SHEETS_FUNCIONARIOS).sheet1
log_sheet = gc.open(SHEETS_LOG_NAME).sheet1

# Nomes e cargos para gerar
nomes = ["Maria", "João", "José", "Ana", "Pedro", "Lucas", "Carla", "Marcos", "Juliana", "Fernanda", "Bruno", "Paula", "Ricardo", "Patrícia", "Sérgio"]
cargos = ["Desenvolvedor de software", "Recursos Humanos", "Vendedor"]

# Feedbacks de teste (poderia ser lorem ipsum)
feedbacks = [
    "Muito satisfeito com o ambiente de trabalho.",
    "Poderia melhorar a comunicação interna.",
    "Faltam recursos para completar as tarefas.",
    "Equipe muito colaborativa!",
    "Necessário mais treinamento em ferramentas.",
    "Gostaria de mais flexibilidade no horário.",
    "Processos poderiam ser mais ágeis.",
    "Adoro trabalhar aqui, ótima equipe!",
    "Falta de equipamentos está prejudicando.",
    "Clima organizacional muito bom."
]

# Quantidade de registros
qtd = random.randint(10, 15)

for _ in range(qtd):
    telegram_id = str(random.randint(10**9, 10**10 - 1))  # 10 dígitos
    nome = random.choice(nomes)
    cargo = random.choice(cargos)

    # Adicionar na planilha de funcionários
    users_sheet.append_row([telegram_id, nome, cargo])

    # Gerar feedback aleatório
    feedback = random.choice(feedbacks)
    data_aleatoria = datetime.now() - timedelta(days=random.randint(0, 30))
    timestamp = data_aleatoria.strftime('%Y-%m-%d %H:%M:%S')

    # Adicionar na planilha de feedbacks
    log_sheet.append_row([telegram_id, nome, cargo, feedback, timestamp])

print(f"{qtd} registros adicionados com sucesso!")
