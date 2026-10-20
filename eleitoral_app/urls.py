from django.urls import path
from .views import DashboardView, CartoesResultadosView, ExplicacaoMetodosView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('cartoes/', CartoesResultadosView.as_view(), name='cartoes_resultados'),
    path('metodos/', ExplicacaoMetodosView.as_view(), name='explicacao_metodos'),
]
