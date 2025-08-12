from flask import Flask, render_template
import os
from collections import Counter
from google import genai
import gspread
from dotenv import load_dotenv

load_dotenv()

# --- Configurações e Conexões ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY não encontrada no seu ficheiro .env!")

client = genai.Client(api_key=GEMINI_API_KEY)

try:
    gc = gspread.service_account(filename="credentials.json")
    users_sheet = gc.open("Funcionarios_Bot").sheet1
    log_sheet = gc.open("Log_Feedback_Bot").sheet1
except Exception as e:
    raise RuntimeError(f"Não foi possível conectar ao Google Sheets. Verifique o credentials.json e as permissões. Erro: {e}")

app = Flask(__name__)

@app.route("/")
def index():
    funcionarios = users_sheet.get_all_records()
    feedbacks = log_sheet.get_all_records()

    total_funcionarios = len(funcionarios)
    respondidos = sum(1 for row in feedbacks if str(row.get('feedback', '')).strip())
    percentual = round((respondidos / total_funcionarios) * 100, 1) if total_funcionarios > 0 else 0

    setores = Counter(f["cargo"] for f in funcionarios)

    reports = {}
    for setor in setores.keys():
        feedbacks_setor = [
            str(fb.get('feedback', '')).strip() 
            for fb in feedbacks 
            if str(fb.get("cargo", "")).strip().lower() == str(setor).strip().lower()
        ]
        feedbacks_validos = [fb for fb in feedbacks_setor if fb]

        if feedbacks_validos:
            prompt = f"Faça um resumo claro e objetivo sobre os seguintes feedbacks do setor '{setor}':\n\n" + "\n".join(feedbacks_validos)
            
            try:
                resp = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt
                )
                resumo = resp.candidates[0].content.parts[0].text
            except Exception as e:
                resumo = f"Erro ao gerar resumo pela IA: {e}"
        else:
            resumo = "Nenhum feedback recebido para este setor ainda."
        
        reports[setor] = resumo
    
    return render_template(
        "index.html",
        total_funcionarios=total_funcionarios,
        respondidos=respondidos,
        percentual=percentual,
        setores=dict(setores),
        reports=reports
    )

if __name__ == "__main__":
    app.run(debug=True)
