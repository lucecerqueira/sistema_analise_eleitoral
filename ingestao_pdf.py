#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import string
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_analise_eleitoral.settings')
django.setup()

import pdfplumber
import pytesseract
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk

try:
    nltk.download('stopwords', quiet=True)
    from nltk.corpus import stopwords
    stop_words_pt = set(stopwords.words('portuguese'))
except Exception:
    stop_words_pt = set()

from eleitoral_app.models import Candidato, ParagrafoPrograma, ResultadoMetodo, MetricaLegibilidade, MapaConhecimento

TEMAS_EXPANDIDOS = {
    'SUS / Saúde': ['sus', 'saúde', 'saude', 'hospital', 'atendimento', 'vacina', 'médicos', 'sanitário'],
    'Tecnologia': ['tecnologia', 'inovação', 'ciência', 'digital', 'pesquisa', 'conectividade', 'tecnológica'],
    'Economia': ['economia', 'emprego', 'renda', 'inflação', 'pib', 'investimento', 'indústria', 'trabalho'],
    'Educação': ['educação', 'escola', 'professores', 'universidade', 'ensino', 'capacitação', 'alfabetização'],
    'Meio Ambiente': ['ambiente', 'clima', 'climáticas', 'sustentabilidade', 'desmatamento', 'amazônia', 'carbono', 'preservação'],
    'Segurança Pública': ['segurança', 'polícia', 'policia', 'criminalidade', 'inteligência', 'facções', 'prisional', 'prevenção'],
    'Infraestrutura': ['infraestrutura', 'saneamento', 'rodovias', 'ferrovias', 'transporte', 'moradia', 'habitação', 'logística'],
    'Gestão e Transparência': ['transparência', 'corrupção', 'eficiência', 'administrativa', 'reforma', 'integridade', 'desburocratização'],
    'Inclusão Social': ['social', 'pobreza', 'fome', 'desigualdade', 'assistência', 'vulnerabilidade', 'transferência', 'renda'],
    'Agricultura': ['agronegócio', 'agrícola', 'safra', 'produtor', 'pecuária', 'crédito rural', 'agricultura familiar']
}

CORES_DISPONIVEIS = ["#ff3b30", "#34c759", "#007aff", "#af52de", "#ff9500", "#5856d6"]

def extrair_texto_pdf(caminho_pdf):
    texto_completo = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            try:
                texto = pagina.extract_text(layout=True)
                if texto and len(texto.strip()) > 50:
                    texto_completo.append(texto)
                else:
                    img = pagina.to_image(resolution=300).original
                    texto_ocr = pytesseract.image_to_string(img, lang='por')
                    if len(texto_ocr.strip()) > 50:
                        texto_completo.append(texto_ocr)
            except Exception:
                pass
    return "\n".join(texto_completo)

def limpar_texto(texto):
    texto_limpo = texto.lower()
    texto_limpo = re.sub(r'(\w+)-\n(\w+)', r'\1\2', texto_limpo)
    texto_limpo = re.sub(r'\n+', ' ', texto_limpo)
    texto_limpo = re.sub(r'[' + re.escape(string.punctuation) + '—”’“”]', '', texto_limpo)
    texto_limpo = re.sub(r'\b\d+\b', '', texto_limpo)
    palavras = [p for p in texto_limpo.split() if p not in stop_words_pt and len(p) > 2]
    return " ".join(palavras)

def calcular_flesch_pt(texto):
    frases = max(1, len(re.split(r'[.!?]+', texto)))
    palavras = max(1, len(re.findall(r'\b\w+\b', texto)))
    silabas = max(1, sum([len(re.findall(r'[aeiouáéíóúâêôãõà]', w.lower())) for w in re.findall(r'\b\w+\b', texto)]))
    score = 248.835 - (1.015 * (palavras / frases)) - (84.6 * (silabas / palavras))
    return round(score, 1), round(palavras/frases, 1), palavras, frases

def extrair_trigramas(texto, top_k=3):
    if not texto.strip():
        return ["Sem citações diretas", "Eixo ausente", "Sem dados"]
    try:
        vec = CountVectorizer(ngram_range=(3, 3), stop_words=list(stop_words_pt)).fit([texto])
        words_freq = sorted([(w, vec.transform([texto]).sum(axis=0)[0, idx]) for w, idx in vec.vocabulary_.items()], key=lambda x: x[1], reverse=True)
        return [w[0].title() for w in words_freq[:top_k]]
    except Exception:
        return ["Propostas do Documento", "Ações Citadas", "Conteúdo Extraído"]

def executar_ingestao_de_pdfs():
    pasta_pdf = Path("media/planos_pdf")
    arquivos_pdf = list(pasta_pdf.glob("*.pdf"))
    
    print(f"-> Localizados {len(arquivos_pdf)} arquivos PDF na pasta 'media/planos_pdf/'")

    if not arquivos_pdf:
        print("-> [ERRO] Nenhum PDF encontrado em media/planos_pdf/. Por favor adicione ficheiros .pdf!")
        return

    Candidato.objects.all().delete()
    ParagrafoPrograma.objects.all().delete()
    ResultadoMetodo.objects.all().delete()
    MetricaLegibilidade.objects.all().delete()
    MapaConhecimento.objects.all().delete()
    print("-> Banco de dados limpo com sucesso!")

    cand_objs = []
    textos_candidatos = {}

    for idx, pdf_file in enumerate(arquivos_pdf):
        candidato_nome = pdf_file.stem.replace("_", " ").title()
        
        # Lula = Vermelho (#ff3b30) | Flávio Bolsonaro = Verde (#34c759)
        if "lula" in candidato_nome.lower():
            cor = "#ff3b30"
        elif "bolsonaro" in candidato_nome.lower() or "flavio" in candidato_nome.lower():
            cor = "#34c759"
        else:
            cor = CORES_DISPONIVEIS[idx % len(CORES_DISPONIVEIS)]
        
        print(f"-> Processando PDF real: {pdf_file.name} -> Candidato: '{candidato_nome}' [Cor: {cor}]...")
        
        texto_bruto = extrair_texto_pdf(pdf_file)
        cand_obj = Candidato.objects.create(nome=candidato_nome, partido="Programa Oficial", cor_tema=cor)
        cand_objs.append(cand_obj)
        
        paragrafos = [p.strip() for p in re.split(r'\n\s*\n', texto_bruto) if len(p.strip()) > 20]
        textos_candidatos[candidato_nome] = paragrafos
        
        for p_idx, p in enumerate(paragrafos, start=1):
            p_limpo = limpar_texto(p)
            ParagrafoPrograma.objects.create(
                candidato=cand_obj,
                id_paragrafo=p_idx,
                texto_original=p,
                texto_limpo=p_limpo,
                total_palavras=len(p.split()),
                palavras_unicas=len(set(p_limpo.split()))
            )

        # Legibilidade
        score, mpf, tot_p, tot_f = calcular_flesch_pt(texto_bruto)
        classif = "Fácil" if score >= 75 else ("Normal" if score >= 50 else "Um pouco Difícil")
        MetricaLegibilidade.objects.create(
            candidato=cand_obj, score_ifsz=score, classificacao=classif,
            media_palavras_frase=mpf, total_palavras=tot_p, total_frases=tot_f
        )

        # TRIGRAMAS Reais extraídos do PDF
        for eixo, palavras_chave in TEMAS_EXPANDIDOS.items():
            texto_eixo = " ".join([p for p in paragrafos if any(kw in p.lower() for kw in palavras_chave)])
            trigramas = extrair_trigramas(limpar_texto(texto_eixo), 3)
            MapaConhecimento.objects.create(
                candidato=cand_obj, eixo_tematico=eixo, subnoes=';'.join(trigramas)
            )

    # PROCESSAMENTO IMPARCIAL DOS MÉTODOS
    item_id = 1
    for eixo, termos in TEMAS_EXPANDIDOS.items():
        p1 = f"Quais são as propostas do candidato para o setor de {eixo}?"
        p2 = f"Como o programa de governo aborda as metas diretas em {eixo}?"
        
        for pergunta in [p1, p2]:
            resumos_por_candidato = []
            dados_candidatos = []

            for cand in cand_objs:
                paragrafos_cand = textos_candidatos[cand.nome]
                
                trecho_melhor = "Nenhum trecho com propostas diretas mapeadas para este eixo."
                pid_melhor = 1
                score_sim = 0.0
                citacoes = 0
                
                if paragrafos_cand:
                    corpus_limpo = [limpar_texto(p) for p in paragrafos_cand if len(limpar_texto(p)) > 5]
                    if corpus_limpo:
                        vectorizer = TfidfVectorizer(stop_words=list(stop_words_pt))
                        corpus = [pergunta] + corpus_limpo
                        tfidf = vectorizer.fit_transform(corpus)
                        sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
                        
                        best_idx = sims.argmax()
                        score_sim = sims[best_idx] * 100
                        if score_sim > 1.0:
                            trecho_melhor = paragrafos_cand[best_idx]
                            pid_melhor = best_idx + 1
                    
                    citacoes = sum(p.lower().count(termos[0]) for p in paragrafos_cand)

                dados_candidatos.append({
                    'cand': cand,
                    'pid': pid_melhor,
                    'score_sim': score_sim,
                    'citacoes': citacoes,
                    'trecho': trecho_melhor
                })

                if score_sim > 1.0:
                    resumos_por_candidato.append(f"<b>{cand.nome}</b> aborda o tema no Parágrafo {pid_melhor}")
                else:
                    resumos_por_candidato.append(f"<b>{cand.nome}</b> não possui menção direta com alta relevância")

            sintese_rag_comparativa = " | ".join(resumos_por_candidato)

            for d in dados_candidatos:
                cand = d['cand']
                trecho_melhor = d['trecho']
                pid_melhor = d['pid']
                score_sim = d['score_sim']
                citacoes = d['citacoes']

                # Método 1
                ResultadoMetodo.objects.create(
                    metodo_tipo='METODO_1', num_item=item_id, candidato=cand,
                    eixo_tematico=eixo, titulo_item=pergunta, id_paragrafo=pid_melhor,
                    relevancia_score=f"{citacoes} citações de '{termos[0]}'",
                    trecho_encontrado=trecho_melhor[:300]
                )
                
                # Método 2
                ResultadoMetodo.objects.create(
                    metodo_tipo='METODO_2', num_item=item_id, candidato=cand,
                    eixo_tematico=eixo, titulo_item=pergunta, id_paragrafo=pid_melhor,
                    relevancia_score=f"Relevância: {score_sim:.1f}%",
                    trecho_encontrado=trecho_melhor[:300]
                )
                
                # Método 3
                ResultadoMetodo.objects.create(
                    metodo_tipo='METODO_3', num_item=item_id, candidato=cand,
                    eixo_tematico=eixo, titulo_item=pergunta, sintese_rag=sintese_rag_comparativa,
                    id_paragrafo=pid_melhor, relevancia_score="Evidência do PDF",
                    trecho_encontrado=trecho_melhor[:300]
                )
            
            item_id += 1

    # Método 4
    for num_eixo, (eixo, termos) in enumerate(TEMAS_EXPANDIDOS.items(), 1):
        termos_str = ", ".join(termos[:4])
        for cand in cand_objs:
            paragrafos_cand = textos_candidatos[cand.nome]
            count_eixo = sum(1 for p in paragrafos_cand if any(kw in p.lower() for kw in termos))
            vol = (count_eixo / len(paragrafos_cand) * 100) if paragrafos_cand else 0.0
            
            trecho = paragrafos_cand[0][:250] if paragrafos_cand else "Sem informações."
            
            ResultadoMetodo.objects.create(
                metodo_tipo='METODO_4', num_item=num_eixo, candidato=cand,
                eixo_tematico=eixo, titulo_item=f"Cluster {num_eixo}: {eixo} ({termos_str})",
                id_paragrafo=1, relevancia_score=f"Volume: {vol:.1f}% do PDF",
                trecho_encontrado=trecho
            )

    print("-> Ingestão Concluída (Lula em Vermelho, Flávio em Verde)!")

if __name__ == '__main__':
    executar_ingestao_de_pdfs()
