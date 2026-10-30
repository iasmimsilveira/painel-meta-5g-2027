#!/usr/bin/env python3
"""Baixa os dados abertos da Anatel e gera site/index.html (Meta 5G 31/07/2027).

Uso: python3 atualizar.py [--cache DIR]
Só usa a biblioteca padrão do Python. Se algum dado vier incompleto, para com erro
e não sobrescreve a página anterior.
"""
import argparse, csv, datetime as dt, email.utils, io, json, math, os, sys, urllib.request, zipfile
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.abspath(__file__))
ANATEL = "https://www.anatel.gov.br/dadosabertos/paineis_de_dados"
URL_COMPROMISSOS = f"{ANATEL}/acompanhamento_e_controle/5g.zip"
URL_ESTACOES = f"{ANATEL}/outorga_e_licenciamento/estacoes_smp.zip"
PRAZO = "31/07/2027"
DENSIDADE = 15000
OPERADORAS = {"Tim S.A.": "TIM", "Claro S.A.": "CLARO", "Telefônica Brasil S.A.": "VIVO"}


def baixar(url, destino):
    """Baixa url para destino e devolve a data de publicação (Last-Modified) em ISO."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (painel-meta-5g)"})
    with urllib.request.urlopen(req, timeout=600) as r, open(destino + ".tmp", "wb") as f:
        lm = r.headers.get("Last-Modified")
        while True:
            bloco = r.read(1 << 20)
            if not bloco:
                break
            f.write(bloco)
    os.replace(destino + ".tmp", destino)
    return email.utils.parsedate_to_datetime(lm).date().isoformat() if lm else None


def ler_csv_do_zip(caminho, nome):
    z = zipfile.ZipFile(caminho)
    return csv.DictReader(io.TextIOWrapper(z.open(nome), encoding="utf-8-sig", newline=""), delimiter=";")


def compromissos_2027(caminho):
    mun = {}
    for r in ler_csv_do_zip(caminho, "Base_5G.csv"):
        op = OPERADORAS.get(r["OPERADORA"])
        if not op or r["PRAZO"] != PRAZO or not r["COMPROMISSO"].startswith("Instalar"):
            continue
        ib = r["COD_MUNICIPIO"]
        m = mun.setdefault(ib, dict(ib=ib, mu=r["MUNICIPIO"], uf=r["UF"], rg=r["REGIAO"],
                                    la=round(float(r["LATITUDE"].replace(",", ".")), 4),
                                    ln=round(float(r["LONGITUDE"].replace(",", ".")), 4), ops={}))
        m["ops"][op] = dict(st=r["STATUS"], lt=r["LOTE_EDITAL"],
                            ant=r["ANOS_ANTECIPADOS"] if "Antecipa" in r["TIPO_ALTERACAO"] else "")
    return mun


def sites_5g_por_municipio(caminho):
    """Sites 5G NR 3,5 GHz por (operadora, município): pares distintos (estação, código IBGE).

    Cada emissão aparece em várias linhas e só uma traz o código IBGE; uma mesma estação
    pode estar licenciada em dois municípios e conta nos dois.
    """
    vistos = set()
    for r in ler_csv_do_zip(caminho, "Estacoes_SMP.csv"):
        if r["Geração"] == "5G" and r["Faixa Estação"] == "3500" and r["Código IBGE"]:
            vistos.add((r["Empresa Estação"], r["Número Estação"], r["Código IBGE"]))
    cont = defaultdict(Counter)
    for emp, _, ib in vistos:
        cont[emp][ib] += 1
    return cont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(RAIZ, "cache"), help="pasta para os downloads")
    args = ap.parse_args()
    os.makedirs(args.cache, exist_ok=True)

    zc, ze = os.path.join(args.cache, "5g.zip"), os.path.join(args.cache, "estacoes_smp.zip")
    print("Baixando compromissos…", flush=True)
    data_comp = baixar(URL_COMPROMISSOS, zc)
    print("Baixando estações licenciadas (~95 MB)…", flush=True)
    data_est = baixar(URL_ESTACOES, ze)

    pop = json.load(open(os.path.join(RAIZ, "dados", "populacao_ibge.json")))["municipios"]
    mun = compromissos_2027(zc)
    sites = sites_5g_por_municipio(ze)

    for m in mun.values():
        p20, p22 = pop.get(m["ib"], [None, None])
        m["pop"], m["pop22"] = p20, p22
        for op in OPERADORAS.values():
            m["n_" + op] = sites[op][m["ib"]]

    # Checagens: se a Anatel mudar o formato, falha em vez de publicar números errados
    por_op = Counter(op for m in mun.values() for op in m["ops"])
    erros = []
    if any(n < 150 for n in (por_op[o] for o in OPERADORAS.values())):
        erros.append(f"poucos municípios no compromisso: {dict(por_op)}")
    if sum(sites["TIM"].values()) < 10000:
        erros.append(f"poucos sites 5G TIM na base: {sum(sites['TIM'].values())}")
    sem_pop = [m["mu"] for m in mun.values() if not m["pop"]]
    if sem_pop:
        erros.append(f"municípios sem população: {sem_pop}")
    if erros:
        sys.exit("ERRO, página não atualizada:\n- " + "\n- ".join(erros))

    hoje = dt.date.today().isoformat()
    meta = dict(prazo="2027-07-31", gerado=hoje, dens=DENSIDADE,
                datas=dict(compromissos=data_comp, estacoes=data_est))
    dados = json.dumps(dict(meta=meta, mun=sorted(mun.values(), key=lambda m: m["ib"])),
                       ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = open(os.path.join(RAIZ, "template.html"), encoding="utf-8").read().replace("/*DATA*/", dados)
    saida = os.path.join(RAIZ, "site", "index.html")
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida + ".tmp", "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(saida + ".tmp", saida)

    for op in OPERADORAS.values():
        ms = [m for m in mun.values() if op in m["ops"]]
        falta = sum(max(0, math.ceil(m["pop"] / DENSIDADE) - m["n_" + op]) for m in ms)
        ok = sum(1 for m in ms if m["n_" + op] >= math.ceil(m["pop"] / DENSIDADE))
        print(f"{op}: {len(ms)} municípios, {ok} na meta, faltam {falta} sites")
    print(f"Gerado {saida} (compromissos {data_comp}, estações {data_est})")


if __name__ == "__main__":
    main()
