import os
from flask import Flask, render_template, request, session
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key')

# Naziv aplikacije
APP_NAME = "HT PROMPT GURU"

# Konfiguracija za Azure OpenAI
API_KEY = os.environ.get('AZURE_OPENAI_API_KEY')
ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT')

# Provjera je li API_KEY i ENDPOINT učitan
if not API_KEY or not ENDPOINT:
    raise ValueError("API_KEY i ENDPOINT moraju biti postavljeni kao varijable okruženja")

# Definirajte maksimalan broj poruka u povijesti kako biste ograničili duljinu prompta
MAX_HISTORY_LENGTH = 20

def get_llm_response():
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY  # Zaglavlje za Azure OpenAI API
    }

    # Dohvati povijest razgovora iz sesije
    conversation_history = session.get('conversation_history', [])

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

        # Dodaj odgovor LLM-a u povijest
        conversation_history.append({
            "role": "assistant",
            "content": response_text
        })

        # Ažuriraj povijest u sesiji, osiguravajući da sistemski prompt ostane
        session['conversation_history'] = [conversation_history[0]] + conversation_history[1:][- (MAX_HISTORY_LENGTH - 1):]

        return response_text
    except requests.RequestException as e:
        return f"Došlo je do greške: {e}"

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'conversation_history' not in session:
        session['conversation_history'] = []

    if request.method == 'POST':
        user_input = request.form['prompt']
        session['conversation_history'].append({'role': 'user', 'content': user_input})

        try:
            # Postavljanje instrukcija za procjenu prompta
            if len(session['conversation_history']) == 1:  # Ako nema prethodnog razgovora
                system_prompt = """
                Ocijenit ćeš korisnički prompt na temelju sljedećih kategorija:
                - Jasnoća i preciznost
                - Kontekst i svrha
                - Specifične upute i ograničenja
                - Ton, stil i jezik
                - Struktura i organizacija

                Na temelju ove ocjene, prompt ocijeni kao:
                - Odličan
                - Vrlo dobar
                - Dobar
                - Dovoljan
                - Loš

                Pruži konstruktivne prijedloge za poboljšanje.
                """
                session['conversation_history'].insert(0, {"role": "system", "content": system_prompt})

            # Dohvati odgovor od LLM-a
            assistant_reply = get_llm_response()
            session['conversation_history'].append({'role': 'assistant', 'content': assistant_reply})

        except Exception as e:
            session['conversation_history'].append({'role': 'assistant', 'content': f'Greška: {e}'})

    return render_template('index.html', messages=session['conversation_history'], app_name=APP_NAME)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
