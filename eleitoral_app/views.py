from django.views.generic import TemplateView
from .models import Candidato, ParagrafoPrograma, ResultadoMetodo, MetricaLegibilidade, MapaConhecimento

DADOS_EXPLICAO_METODOS = {
    'METODO_1': {
        'nome': 'Método 1: Busca Léxica & KWIC',
        'subtitulo': 'Localização exata por Palavras-Chave em Janela de Contexto',
        'descricao': """Contagem e localização exata das palavras-chave em cada parágrafo do PDF real.""",
        'como_funciona': """1. Varredura por expressões regulares.\n2. Mapeamento da quantidade exata de menções no texto oficial.""",
        'quando_usar': 'Para identificar a presença objetiva de termos específicos.',
        'metricas': 'Contagem de citações diretas no texto.'
    },
    'METODO_2': {
        'nome': 'Método 2: Busca Semântica por Similaridade',
        'subtitulo': 'Vetorização TF-IDF com Similaridade de Cosseno',
        'descricao': """Cálculo vetorial para encontrar o parágrafo do PDF real mais parecido com a pergunta.""",
        'como_funciona': """1. Vetorização TF-IDF dos parágrafos lidos.\n2. Distância angular (Cosseno) entre a pergunta e os trechos.""",
        'quando_usar': 'Para responder perguntas sobre o programa mesmo sem correspondência exata de palavras.',
        'metricas': 'Score % de Similaridade de Cosseno.'
    },
    'METODO_3': {
        'nome': 'Método 3: RAG (Retrieval-Augmented Generation)',
        'subtitulo': 'Injeção de Contexto Documental e Síntese Comparativa Imparcial',
        'descricao': """Recuperação de evidências documentais e construção de síntese comparativa equilibrada entre todos os programas de governo.""",
        'como_funciona': """1. Resgate do melhor parágrafo de cada candidato.\n2. Síntese comparativa lado a lado sem favorecimento.""",
        'quando_usar': 'Para comparar o posicionamento geral dos candidatos em cada eixo.',
        'metricas': 'Síntese comparativa imparcial.'
    },
    'METODO_4': {
        'nome': 'Método 4: Agrupamento Temático Automático',
        'subtitulo': 'Volume e Presença Temática no Documento',
        'descricao': """Mapeamento da proporção de parágrafos dedicados a cada eixo temático no PDF.""",
        'como_funciona': """1. Contagem de parágrafos associados a cada área temática sobre o total do documento.""",
        'quando_usar': 'Para descobrir o nível de prioridade que cada candidato deu a cada tema.',
        'metricas': 'Porcentagem (%) de atenção dedicada ao tema.'
    },
    'LEGIBILIDADE': {
        'nome': 'Módulo de Legibilidade: Flesch-Szigriszt',
        'subtitulo': 'Análise da Complexidade Textual',
        'descricao': """Avalia a complexidade do texto lido a partir da contagem de frases, palavras e sílabas.""",
        'como_funciona': """Aplicação do índice de Flesch-Szigriszt adaptado para a língua portuguesa.""",
        'quando_usar': 'Para verificar a facilidade de leitura e clareza do documento.',
        'metricas': 'Pontuação IFSZ (0-100).'
    }
}

class DashboardView(TemplateView):
    template_name = 'eleitoral_app/dashboard.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        
        candidatos_ordenados = list(Candidato.objects.all())
        candidatos_ordenados.sort(key=lambda x: 0 if x.cor_tema == '#ff3b30' or 'lula' in x.nome.lower() else 1)
        
        c['candidatos'] = candidatos_ordenados
        c['total_paragrafos'] = ParagrafoPrograma.objects.count()
        c['total_m1'] = ResultadoMetodo.objects.filter(metodo_tipo='METODO_1').values('num_item').distinct().count()
        c['total_m2'] = ResultadoMetodo.objects.filter(metodo_tipo='METODO_2').values('num_item').distinct().count()
        c['total_m3'] = ResultadoMetodo.objects.filter(metodo_tipo='METODO_3').values('num_item').distinct().count()
        c['total_m4'] = ResultadoMetodo.objects.filter(metodo_tipo='METODO_4').values('num_item').distinct().count()
        
        metricas_ord = list(MetricaLegibilidade.objects.all())
        metricas_ord.sort(key=lambda m: 0 if m.candidato.cor_tema == '#ff3b30' or 'lula' in m.candidato.nome.lower() else 1)
        c['metricas_legibilidade'] = metricas_ord
        
        mapas_estruturados = {}
        for cand in candidatos_ordenados:
            mapas_estruturados[cand.nome] = {
                'cor': cand.cor_tema,
                'eixos': {}
            }
            registros = MapaConhecimento.objects.filter(candidato=cand)
            for reg in registros:
                mapas_estruturados[cand.nome]['eixos'][reg.eixo_tematico] = reg.subnoes.split(';')
                
        c['dados_mapas'] = mapas_estruturados
        return c

class CartoesResultadosView(TemplateView):
    template_name = 'eleitoral_app/cartoes_resultados.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        
        metodo_sel = self.request.GET.get('metodo', 'METODO_2')
        qtd_por_card = int(self.request.GET.get('qtd', 2))
        eixo_sel = self.request.GET.get('eixo', '')
        
        qs_metodo = ResultadoMetodo.objects.filter(metodo_tipo=metodo_sel)
        if eixo_sel:
            qs_metodo = qs_metodo.filter(eixo_tematico=eixo_sel)
            
        numeros_itens = list(qs_metodo.values_list('num_item', flat=True).distinct().order_by('num_item'))
        
        lotes = []
        for i in range(0, len(numeros_itens), qtd_por_card):
            lotes_nums = numeros_itens[i:i + qtd_por_card]
            itens_lote = qs_metodo.filter(num_item__in=lotes_nums).order_by('num_item')
            
            agrupados_por_item = {}
            for item in itens_lote:
                if item.num_item not in agrupados_por_item:
                    agrupados_por_item[item.num_item] = {
                        'num': item.num_item,
                        'titulo': item.titulo_item,
                        'eixo': item.eixo_tematico,
                        'sintese': item.sintese_rag,
                        'respostas': []
                    }
                agrupados_por_item[item.num_item]['respostas'].append(item)
                
            for num_item, item_dict in agrupados_por_item.items():
                item_dict['respostas'].sort(
                    key=lambda r: 0 if r.candidato.cor_tema == '#ff3b30' or 'lula' in r.candidato.nome.lower() else 1
                )
                
            lotes.append({
                'intervalo': f"{lotes_nums[0]} a {lotes_nums[-1]}" if len(lotes_nums) > 1 else f"{lotes_nums[0]}",
                'itens': list(agrupados_por_item.values())
            })
            
        c['lotes_cartoes'] = lotes
        c['qtd_selecionada'] = qtd_por_card
        c['metodo_selecionado'] = metodo_sel
        c['eixo_selecionado'] = eixo_sel
        c['metodo_nome'] = dict(ResultadoMetodo.METODO_CHOICES).get(metodo_sel)
        c['eixos_disponiveis'] = ResultadoMetodo.objects.values_list('eixo_tematico', flat=True).distinct().order_by('eixo_tematico')
        c['total_perguntas_exibidas'] = len(numeros_itens)
        c['explicacao_metodo_ativo'] = DADOS_EXPLICAO_METODOS.get(metodo_sel, {})
        return c

class ExplicacaoMetodosView(TemplateView):
    template_name = 'eleitoral_app/explicacao_metodos.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c['metodos_info'] = DADOS_EXPLICAO_METODOS
        return c
