from django.db import models

class Candidato(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    partido = models.CharField(max_length=50, default="Programa Oficial")
    cor_tema = models.CharField(max_length=20, default="#34c759")

    def __str__(self):
        return f"{self.nome}"

class ParagrafoPrograma(models.Model):
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE, related_name='paragrafos')
    id_paragrafo = models.IntegerField()
    eixo_tematico = models.CharField(max_length=100, default="Geral")
    texto_original = models.TextField()
    texto_limpo = models.TextField()
    total_palavras = models.IntegerField(default=0)
    palavras_unicas = models.IntegerField(default=0)

    def __str__(self):
        return f"[{self.candidato.nome}] Parágrafo {self.id_paragrafo}"

class ResultadoMetodo(models.Model):
    METODO_CHOICES = (
        ('METODO_1', 'Método 1: Busca Léxica & KWIC'),
        ('METODO_2', 'Método 2: Busca Semântica por Similaridade'),
        ('METODO_3', 'Método 3: RAG (Síntese e Contexto)'),
        ('METODO_4', 'Método 4: Agrupamento Temático Automático'),
    )
    
    metodo_tipo = models.CharField(max_length=20, choices=METODO_CHOICES, default='METODO_2')
    num_item = models.IntegerField()
    eixo_tematico = models.CharField(max_length=100)
    titulo_item = models.TextField()
    sintese_rag = models.TextField(blank=True)
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE)
    id_paragrafo = models.IntegerField(default=1)
    relevancia_score = models.CharField(max_length=50)
    trecho_encontrado = models.TextField()

    def __str__(self):
        return f"[{self.get_metodo_tipo_display()}] [{self.eixo_tematico}] {self.candidato.nome}"

class MetricaLegibilidade(models.Model):
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE)
    score_ifsz = models.FloatField()
    classificacao = models.CharField(max_length=50)
    media_palavras_frase = models.FloatField()
    total_palavras = models.IntegerField()
    total_frases = models.IntegerField()

    def __str__(self):
        return f"Legibilidade: {self.candidato.nome} ({self.score_ifsz} pts)"

class MapaConhecimento(models.Model):
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE)
    eixo_tematico = models.CharField(max_length=100)
    subnoes = models.TextField()

    def __str__(self):
        return f"Mapa [{self.candidato.nome}] - {self.eixo_tematico}"
