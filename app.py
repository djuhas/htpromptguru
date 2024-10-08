import os
import re
from flask import Flask, render_template, request, session
import requests

app = Flask(__name__)

# Postavite tajni ključ za sesije iz varijabli okruženja
app.secret_key = os.environ.get('SECRET_KEY')

# Konfiguracija za LLM
API_KEY = os.environ.get('API_KEY')
ENDPOINT = os.environ.get('ENDPOINT')

# Provjera je li API_KEY i ENDPOINT učitan
if not API_KEY or not ENDPOINT:
    raise ValueError("API_KEY i ENDPOINT moraju biti postavljeni kao varijable okruženja")

# Definirajte maksimalan broj poruka u povijesti kako biste ograničili duljinu prompta
MAX_HISTORY_LENGTH = 20  # Možete prilagoditi ovaj broj prema potrebi

def get_llm_response(user_prompt):
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY  # Ispravno zaglavlje za Azure OpenAI API
    }

    # Inicijaliziraj prompt za ocjenjivanje prema zadanom obrascu
    system_prompt = (
        "Ocijenit ćeš korisnički prompt na temelju sljedećih kategorija:"
        "1. Jasnoća i preciznost"
        "2. Kontekst i svrha"
        "3. Specifične upute i ograničenja"
        "4. Ton, stil i jezik"
        "5. Struktura i organizacija"
        "Ocjeni prompt koristeći '/x/' za razdvajanje svake linije odgovora"
        "Prvo vrati ukupno procjenu (navedi score i pojasni ga), zatim detalje po kategorijama koje su mogle biti bolje i na kraju prijedlog za poboljšanje te ne zaboravi odvojiti svaki dio s '/x/'."
    )

    conversation_history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "messages": conversation_history,
        "temperature": 0.9,  # Povećano za veći kreativni output
        "top_p": 1.0,        # Koristi sve moguće uzorke
        "max_tokens": 1500   # Povećano na 1500
    }

    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()  # Provjera uspješnosti zahtjeva
        data = response.json()
        
        # Provjeravamo ispravno polje za odgovor
        response_text = data['choices'][0]['message']['content']

        # Zamjena '/x/' s novim redom
        response_text = response_text.replace('/x/', '\n').strip()

        return response_text
    except requests.RequestException as e:
        return f"Došlo je do greške: {e}"

# Početna stranica (jednostavan chat bez levele)
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'conversation_history' not in session:
        session['conversation_history'] = []

    conversation_history = session['conversation_history']
    error = None

    if request.method == 'POST':
        user_input = request.form.get('prompt')

        # Spremi korisnički unos u povijest
        conversation_history.append({
            "role": "user",
            "content": user_input
        })
        session['conversation_history'] = conversation_history[-MAX_HISTORY_LENGTH:]

        # Dohvati odgovor od GPT modela
        response_text = get_llm_response(user_input)
        conversation_history.append({
            "role": "assistant",
            "content": response_text
        })
        session['conversation_history'] = conversation_history[-MAX_HISTORY_LENGTH:]

    return render_template('index.html', messages=conversation_history)

if __name__ == '__main__':
    app.run(debug=True)
