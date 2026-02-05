from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import unicodedata
import random
import urllib.parse

def formatar_slug(texto):
    if not texto: return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip().replace(' ', '-')

def limpar_numero(texto):
    if not texto: return 0.0
    nums = ''.join([c for c in texto if c.isdigit() or c == ','])
    if not nums: return 0.0
    return float(nums.replace(',', '.'))

def formatar_dinheiro_url(valor):
    texto = f"{valor:,.2f}"
    texto = texto.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"R$ {texto}"

def formatar_area_url(valor):
    texto = f"{valor:,.2f}"
    texto = texto.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"{texto} m²"

class ApolarProvider:
    def __init__(self):
        self.base_url = "https://www.apolar.com.br/alugar"
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def run(self, filtros):
        resultados = []

        cidade_alvo = formatar_slug(filtros.get('cidade', 'curitiba'))
        tipo_imovel = filtros.get('tipo', 'apartamento')
        bairros = filtros.get('bairros', [])

        # Filtros numéricos
        quartos_min = filtros.get('quartos_min', 0)
        preco_max = filtros.get('preco_max', 0)
        area_min = filtros.get('area_min', 0)
        preco_condominio_incluso = filtros.get('preco_condominio_incluso', False)

        with sync_playwright() as p:
            print("--> [Apolar] Iniciando navegador...")
            browser = p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
            page = browser.new_page()

            for bairro in bairros:
                slug_bairro = formatar_slug(bairro)

                # Montagem da URL (Mantive igual)
                url_path = f"{self.base_url}/{tipo_imovel}/{cidade_alvo}/{slug_bairro}"
                if quartos_min > 0: url_path += f"/{quartos_min}-quartos"

                params = {'mensal': '', 'country': 'Brasil'}
                if preco_max > 0: params['price_max'] = formatar_dinheiro_url(preco_max)
                if area_min > 0: params['area_min'] = formatar_area_url(area_min)
                if preco_condominio_incluso: params['price_condominium_included'] = 'true'

                full_url = f"{url_path}?{urllib.parse.urlencode(params)}"

                print(f"--> [Apolar] Analisando: {bairro.upper()}")

                try:
                    page.goto(full_url, timeout=60000)

                    try:
                        page.wait_for_selector('.property-component, .no-results-class', timeout=8000)
                    except:
                        continue

                    soup = BeautifulSoup(page.content(), 'html.parser')
                    cards = soup.find_all(class_='property-component')

                    imoveis_validos_pagina = 0

                    for card in cards:
                        try:
                            # --- 1. Extração de Dados ---
                            bairro_tag = card.find(class_='property-address-others')
                            bairro_encontrado_raw = bairro_tag.text.strip() if bairro_tag else ""

                            # Normaliza para comparar (Ex: "Boa Vista, Curitiba" vira "boa-vista-curitiba")
                            bairro_encontrado_slug = formatar_slug(bairro_encontrado_raw)

                            # --- 2. VALIDAÇÃO DE LOCALIZAÇÃO (TRAVA DE SEGURANÇA) ---
                            # Verifica se o nome do bairro desejado está dentro do endereço achado
                            # Ex: Se procuro "batel", aceito "batel, curitiba". Não aceito "centro".

                            if slug_bairro not in bairro_encontrado_slug:
                                # Se o bairro do card for diferente do bairro da busca, é LIXO (propaganda/sugestão)
                                continue

                            # Verifica Cidade também (para evitar "Boqueirão" em outra cidade)
                            if cidade_alvo not in bairro_encontrado_slug:
                                continue

                            # --- 3. Extração Numérica e Validação ---
                            preco_raw = card.find(class_='property-current-price')
                            preco_val = limpar_numero(preco_raw.text) if preco_raw else 0

                            quartos_raw = card.find(class_='feature bed')
                            quartos_val = limpar_numero(quartos_raw.text) if quartos_raw else 0

                            # Validação final de valores (URL filter as vezes falha)
                            if preco_max > 0 and preco_val > preco_max: continue
                            if quartos_min > 0 and quartos_val < quartos_min: continue

                            # --- 4. Coleta Final ---
                            tag_link = card.find('a', href=True)
                            link = tag_link['href'] if tag_link else ""

                            area_raw = card.find(class_='feature ruler')
                            area_txt = area_raw.text.strip() if area_raw else "-"


                            resultados.append({
                                'Imobiliaria': 'Apolar',
                                'Bairro': bairro, # Salvamos o bairro que PEDIMOS (já validado)
                                'Local Real': bairro_encontrado_raw, # Para conferência
                                'Tipo': tipo_imovel,
                                'Preco': preco_val,
                                'Quartos': int(quartos_val),
                                'Area': area_txt,
                                'Link': link
                            })
                            imoveis_validos_pagina += 1

                        except Exception:
                            continue

                    print(f"    Total Cards: {len(cards)} | Úteis: {imoveis_validos_pagina}")

                except Exception as e:
                    print(f"    Erro crítico: {e}")

                time.sleep(random.uniform(0.5, 1.0))

            browser.close()

        return resultados
