from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import unicodedata
import random

def formatar_slug(texto):
    if not texto: return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip().replace(' ', '-')

def limpar_numero(texto):
    """Extrai números de string (ex: 'R$ 2.100,00' -> 2100.0)"""
    if not texto: return 0.0
    nums = ''.join([c for c in texto if c.isdigit() or c == ','])
    if not nums: return 0.0
    return float(nums.replace(',', '.'))

class GalvaoProvider:
    def __init__(self):
        self.base_url = "https://www.galvao.com.br/imoveis"
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def run(self, filtros):
        resultados = []

        # Parâmetros
        cidade = formatar_slug(filtros.get('cidade', 'curitiba'))
        tipo = formatar_slug(filtros.get('tipo', 'apartamento'))
        bairros = filtros.get('bairros', [])

        # Filtros Numéricos (Com defaults para a URL da Galvão)
        quartos_min = filtros.get('quartos_min', 1)
        preco_min = 0 # Galvão exige um "de", vamos usar 0
        preco_max = filtros.get('preco_max', 50000) # Se não tiver max, chuta alto
        area_min = filtros.get('area_min', 0)
        area_max = 50000 # Maximo generico

        # URL da Galvão não aceita float (2500.00), tem que ser int (2500)
        p_min = int(preco_min)
        p_max = int(preco_max)
        a_min = int(area_min)
        a_max = int(area_max)

        with sync_playwright() as p:
            print("--> [Galvão] Iniciando navegador...")
            browser = p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
            page = browser.new_page()

            for bairro in bairros:
                slug_bairro = formatar_slug(bairro)

                # --- MONTAGEM DA URL COMPLEXA ---
                # Padrão: /apartamento-locacao-curitiba-{bairro}-{q}-ou-mais-quartos-de-{pmin}-ate-{pmax}-de-{amin}m2-ate-{amax}m2
                url_slug = (
                    f"{tipo}-locacao-{cidade}-{slug_bairro}-"
                    f"{quartos_min}-ou-mais-quartos-"
                    f"de-{p_min}-ate-{p_max}-"
                    f"de-{a_min}m2-ate-{a_max}m2"
                )

                full_url = f"{self.base_url}/{url_slug}"

                print(f"--> [Galvão] Buscando em {bairro.upper()}")
                # print(f"    URL: {full_url}")

                try:
                    page.goto(full_url, timeout=60000)

                    # Espera o card (classe list__link que é o <a> principal)
                    try:
                        page.wait_for_selector('.list__link', timeout=8000)
                    except:
                        print(f"    (Sem imóveis ou timeout no {bairro})")
                        continue

                    soup = BeautifulSoup(page.content(), 'html.parser')
                    # O card principal é o próprio link <a> com a classe list__link
                    cards = soup.find_all('a', class_='list__link')

                    validos = 0
                    for card in cards:
                        try:
                            # 1. Link
                            link_rel = card['href']
                            link = f"https://www.galvao.com.br{link_rel}"

                            # 2. Bairro (Validação)
                            # O HTML tem: <span class="list__address"> <strong>Bairro: </strong>Alto da Glória </span>
                            bairro_box = card.find('strong', string=lambda t: t and 'Bairro' in t)
                            if bairro_box:
                                # Pega o texto do pai (o span) e remove a palavra "Bairro:"
                                bairro_real = bairro_box.parent.get_text().replace('Bairro:', '').strip()
                            else:
                                bairro_real = bairro

                            # Trava de Segurança de Bairro
                            if slug_bairro not in formatar_slug(bairro_real):
                                continue

                            # 3. Preço
                            # O HTML é confuso, tem <br> no meio. Vamos pegar todo o texto da div list__price
                            price_div = card.find(class_='list__price')
                            if price_div:
                                # O texto vem sujo: "Valor líquidoR$ 2.100,00". Limpar numero resolve.
                                preco_val = limpar_numero(price_div.get_text())
                            else:
                                preco_val = 0

                            # 4. Características (Quartos, Área, Vagas)
                            # Eles estão em divs genéricas 'list__item'. Temos que iterar e advinhar pelo texto.
                            quartos_val = 0
                            area_txt = "-"
                            vagas_val = 0 # HTML que você mandou não tinha vaga, mas deixo preparado

                            features = card.find_all(class_='list__item')
                            for f in features:
                                texto = f.get_text().strip().lower()

                                if 'm²' in texto:
                                    area_txt = texto
                                elif 'quarto' in texto:
                                    quartos_val = limpar_numero(texto)
                                elif 'vaga' in texto:
                                    vagas_val = limpar_numero(texto)
                                elif 'bwc' in texto or 'banheiro' in texto:
                                    pass # Se quiser pegar banheiro, é aqui

                            # Validação Numérica Extra
                            if preco_max > 0 and preco_val > preco_max: continue
                            if quartos_min > 0 and quartos_val < quartos_min: continue

                            resultados.append({
                                'Imobiliaria': 'Galvão',
                                'Bairro': bairro_real,
                                'Tipo': tipo,
                                'Preco': preco_val,
                                'Quartos': int(quartos_val),
                                'Vagas': int(vagas_val), # Pode vir 0 se não achar
                                'Area': area_txt,
                                'Link': link
                            })
                            validos += 1

                        except Exception as e:
                            # print(f"Erro no card: {e}")
                            continue

                    print(f"    Encontrados: {validos}")

                except Exception as e:
                    print(f"    Erro na URL: {e}")

                time.sleep(random.uniform(1, 2))

            browser.close()

        return resultados
