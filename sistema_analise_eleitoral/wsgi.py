import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_analise_eleitoral.settings')

application = get_wsgi_application()

# Executa migrações automaticamente no arranque do Gunicorn
try:
    from django.core.management import call_command
    call_command('migrate', interactive=False)
    # Executa a carga inicial dos dados de candidatos
    call_command('shell', command="import ingestao_pdf")
except Exception as e:
    print(f"Erro ao executar automigracao no startup: {e}")