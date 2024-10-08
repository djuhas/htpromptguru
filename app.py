import os
from flask import Flask, render_template, request, session
import requests

app = Flask(__name__)

# Postavite tajni ključ za sesije iz varijabli okruženja
app.secret_key = os.environ.get('SECRET_KEY')

# Konfiguracija za LLM
API_KEY = os.environ.get('API_KEY')
ENDPOINT = os.environ.get('ENDPOINT')

# Naziv aplikacije
APP_NAME = "HT PROMPT GURU"

# Postavljanje AzureOpenAI klijenta pomoću okruženja varijabli
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-05-01-preview"
)

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'messages' not in session:
        session['messages'] = []

    if request.method == 'POST':
        user_input = request.form['prompt']
        session['messages'].append({'role': 'user', 'content': user_input})

        try:
            thread = client.beta.threads.create()
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input
            )

            assistant = client.beta.assistants.create(
                model="docgen-gpt-4o-mini", 
                instructions="""
                Ocjenjivanje:
                Na temelju procjene navedenih kategorija, prompt ocijeni kao:
                - Odličan
                - Vrlo dobar
                - Dobar
                - Dovoljan
                - Loš
                
                Kategorije za procjenu:
                - Jasnoća i preciznost
                - Kontekst i svrha
                - Specifične upute i ograničenja
                - Ton, stil i jezik
                - Struktura i organizacija

                Savjeti za poboljšanje:
                Pruži konstruktivne prijedloge za poboljšanje.
                """,
                temperature=0.95,
                top_p=0.6
            )

            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )

            while run.status in ['queued', 'in_progress', 'cancelling']:
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            if run.status == 'completed':
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                assistant_reply = messages.data[0].content[0].text.value
                
                assistant_reply_html = markdown.markdown(assistant_reply)
                session['messages'].append({'role': 'assistant', 'content': assistant_reply_html})

        except Exception as e:
            session['messages'].append({'role': 'assistant', 'content': f'Error: {e}'})

    return render_template('index.html', messages=session['messages'], app_name=APP_NAME)

if __name__ == '__main__':
    app.run(debug=True)
