import os
import sys
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_analise_eleitoral.settings')

application = get_wsgi_application()

# Executa migrações e carga dos PDFs no arranque do servidor
try:
    from django.core.management import call_command
    print("=== Executando migrações no startup ===")
    call_command('migrate', interactive=False)
    
    print("=== Executando ingestão de dados dos PDFs ===")
    # Executa o script ingestao_pdf.py garantindo que o banco seja povoado no Render
    ingestao_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ingestao_pdf.py')
    if os.path.exists(ingestao_path):
        with open(ingestao_path, 'r', encoding='utf-8') as f:
            exec(f.read(), {'__name__': '__main__'})
        print("=== Ingestão concluída com sucesso! ===")
    else:
        print(f"Aviso: Arquivo {ingestao_path} não encontrado.")
except Exception as e:
    print(f"Erro no startup do WSGI: {e}")