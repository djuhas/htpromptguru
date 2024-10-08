import os
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
        "Ocijenit ćeš korisnički prompt na temelju sljedećih kategorija:\n"
        "1. Jasnoća i preciznost\n"
        "2. Kontekst i svrha\n"
        "3. Specifične upute i ograničenja\n"
        "4. Ton, stil i jezik\n"
        "5. Struktura i organizacija\n\n"
        "Ocijeni prompt kao: Odličan, Vrlo dobar, Dobar, Dovoljan ili Loš.\n"
        "Pruži prijedloge za poboljšanje.\n"
        "Odgovori u običnom tekstualnom formatu bez korištenja zvjezdica ili drugog markdown formata. "
        "Razdvoji stavke s novim linijama za bolju čitljivost."
    )

    conversation_history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "messages": conversation_history,
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 150
    }

    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()  # Provjera uspješnosti zahtjeva
        data = response.json()
        response_text = data['choices'][0]['message']['content']

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
