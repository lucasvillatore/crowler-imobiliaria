from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import unicodedata
import random
import urllib.parse

def formatar_slug(texto):
    if not texto: return ""
    # Remove acentos e troca espaços por hifens para a parte estrutural da URL
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip().replace(' ', '-')

def limpar_numero(texto):
    if not texto: return 0.0
    nums = ''.join([c for c in texto if c.isdigit()])
    if not nums: return 0.0
    return float(nums)

class ZapProvider:
    def __init__(self):
        self.base_url = "https://www.zapimoveis.com.br/aluguel"
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

    def run(self, filtros):
        resultados = []
        cidade = "Curitiba"
        estado = "Paraná"
        
        # Lista de bairros vinda dos filtros (com a correção de casing)
        bairros_raw = filtros.get('bairros', [])
        preco_max = filtros.get('preco_max', 2500)
        area_min = filtros.get('area_min', 50)

        with sync_playwright() as p:
            print("--> [Zap] Iniciando navegador...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=self.user_agent,
                locale="pt-BR",
                timezone_id="America/Sao_Paulo"
            )
            page = context.new_page()

            for bairro in bairros_raw:
                # 1. Formatações para a URL
                bairro_slug = formatar_slug(bairro) # ex: agua-verde
                # O Zap espera o nome no 'onde' exatamente como no cadastro deles (Camel Case)
                bairro_title = bairro.title().replace("Da ", "da ").replace("De ", "de ")
                
                # 2. Montagem do parâmetro 'onde' conforme seu exemplo
                # Note as vírgulas (%2C) e a hierarquia
                # BR>Parana (sem acento no hierarchy) > Curitiba > Barrios > Nome
                hierarquia_estado = "Parana"
                onde_str = f", {estado}, {cidade}, , {bairro_title}, , , neighborhood, BR>{hierarquia_estado}>NULL>{cidade}>Barrios>{bairro_title}, , "
                onde_encoded = urllib.parse.quote(onde_str)

                # 3. Construção da URL Final
                full_url = (
                    f"{self.base_url}/apartamentos/pr+curitiba++{bairro_slug}/2-quartos/?"
                    f"transacao=aluguel&"
                    f"onde={onde_encoded}&"
                    f"tipos=apartamento_residencial&"
                    f"quartos=2%2C3%2C4&"
                    f"precoMaximo={int(preco_max)}&"
                    f"areaMinima={int(area_min)}&"
                    f"origem=busca-recente"
                )

                print(f"--> [Zap] Buscando em: {bairro_title}")

                try:
                    # Vai para a página e espera os resultados
                    page.goto(full_url, wait_until="load", timeout=60000)
                    
                    # Espera as LIs da lista oficial (data-cy="rp-property-cd")
                    try:
                        page.wait_for_selector('li[data-cy="rp-property-cd"]', timeout=15000)
                    except:
                        print(f"    ⚠️  Bairro {bairro_title} não retornou lista de resultados.")
                        continue

                    # Scroll para garantir que o lazy load não quebre o soup
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                    time.sleep(1)

                    soup = BeautifulSoup(page.content(), 'html.parser')
                    # Pega apenas as LIs da lista, não os recomendados
                    lis = soup.find_all('li', {'data-cy': 'rp-property-cd'})

                    validos_bairro = 0
                    for li in lis:
                        card = li.find('a', class_='olx-core-surface')
                        if not card: continue

                        link = card.get('href', '')
                        if not link.startswith('http'):
                            link = f"https://www.zapimoveis.com.br{link}"

                        # Extração de dados
                        try:
                            # Preço principal
                            preco_tag = li.find('p', class_='olx-ad-card__price')
                            preco_val = limpar_numero(preco_tag.text) if preco_tag else 0

                            # Características (Área e Quartos) via data-cy
                            area_tag = li.find('li', {'data-cy': 'rp-cardProperty-propertyArea-txt'})
                            area_txt = area_tag.get_text(strip=True) if area_tag else "-"

                            quartos_tag = li.find('li', {'data-cy': 'rp-cardProperty-bedroomQuantity-txt'})
                            quartos_val = limpar_numero(quartos_tag.text) if quartos_tag else 2

                            resultados.append({
                                'Imobiliaria': 'Zap Imóveis',
                                'Bairro': bairro_title,
                                'Preco': preco_val,
                                'Quartos': int(quartos_val),
                                'Area': area_txt,
                                'Link': link
                            })
                            validos_bairro += 1
                        except Exception as e:
                            continue

                    print(f"    ✅ Encontrados {validos_bairro} imóveis.")

                except Exception as e:
                    print(f"    ❌ Erro crítico no bairro {bairro}: {e}")

                # Delay maior entre bairros para evitar bloqueio de IP (importante no Zap)
                time.sleep(random.uniform(3, 6))

            browser.close()

        return resultados
