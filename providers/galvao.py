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

        cidade = formatar_slug(filtros.get('cidade', 'curitiba'))
        tipo = formatar_slug(filtros.get('tipo', 'apartamento'))
        bairros = filtros.get('bairros', [])

        quartos_min = filtros.get('quartos_min', 1)
        preco_min = 0
        preco_max = filtros.get('preco_max', 50000)
        area_min = filtros.get('area_min', 0)
        area_max = 50000
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

                url_slug = (
                    f"{tipo}-locacao-{cidade}-{slug_bairro}-"
                    f"{quartos_min}-ou-mais-quartos-"
                    f"de-{p_min}-ate-{p_max}-"
                    f"de-{a_min}m2-ate-{a_max}m2"
                )

                full_url = f"{self.base_url}/{url_slug}"

                print(f"--> [Galvão] Buscando em {bairro.upper()}")

                try:
                    page.goto(full_url, timeout=60000)

                    try:
                        page.wait_for_selector('.list__link', timeout=8000)
                    except:
                        print(f"    (Sem imóveis ou timeout no {bairro})")
                        continue

                    soup = BeautifulSoup(page.content(), 'html.parser')
                    cards = soup.find_all('a', class_='list__link')

                    validos = 0
                    for card in cards:
                        try:
                            link_rel = card['href']
                            link = f"https://www.galvao.com.br{link_rel}"

                            bairro_box = card.find('strong', string=lambda t: t and 'Bairro' in t)
                            if bairro_box:
                                bairro_real = bairro_box.parent.get_text().replace('Bairro:', '').strip()
                            else:
                                bairro_real = bairro

                            if slug_bairro not in formatar_slug(bairro_real):
                                continue

                            price_div = card.find(class_='list__price')
                            if price_div:
                                preco_val = limpar_numero(price_div.get_text())
                            else:
                                preco_val = 0

                            quartos_val = 0
                            area_txt = "-"
                            vagas_val = 0

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
                                    pass

                            if preco_max > 0 and preco_val > preco_max: continue
                            if quartos_min > 0 and quartos_val < quartos_min: continue

                            resultados.append({
                                'Imobiliaria': 'Galvão',
                                'Bairro': bairro_real,
                                'Tipo': tipo,
                                'Preco': preco_val,
                                'Quartos': int(quartos_val),
                                'Vagas': int(vagas_val),
                                'Area': area_txt,
                                'Link': link
                            })
                            validos += 1

                        except Exception as e:
                            continue

                    print(f"    Encontrados: {validos}")

                except Exception as e:
                    print(f"    Erro na URL: {e}")

                time.sleep(random.uniform(1, 2))

            browser.close()

        return resultados
