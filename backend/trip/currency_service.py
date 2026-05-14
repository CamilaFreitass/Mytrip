import time
import requests

# Cache por moeda base: {'BRL': {'rates': {...}, 'timestamp': ...}}
_cache: dict = {}
_CACHE_TTL = 3600  # 1 hora

SIMBOLOS = {
    'BRL': 'R$',
    'USD': 'US$',
    'EUR': '€',
    'GBP': '£',
    'ARS': '$',
    'CLP': 'CLP$',
    'COP': 'COL$',
    'MXN': 'MX$',
    'JPY': '¥',
    'CAD': 'CA$',
    'AUD': 'A$',
    'CHF': 'CHF',
    'CNY': '¥',
    'PEN': 'S/',
    'UYU': '$U',
    'BOB': 'Bs',
    'PYG': '₲',
}

MOEDAS_DISPONIVEIS = [
    ('BRL', 'BRL — Real Brasileiro'),
    ('USD', 'USD — Dólar Americano'),
    ('EUR', 'EUR — Euro'),
    ('GBP', 'GBP — Libra Esterlina'),
    ('ARS', 'ARS — Peso Argentino'),
    ('CLP', 'CLP — Peso Chileno'),
    ('COP', 'COP — Peso Colombiano'),
    ('MXN', 'MXN — Peso Mexicano'),
    ('JPY', 'JPY — Iene Japonês'),
    ('CAD', 'CAD — Dólar Canadense'),
    ('AUD', 'AUD — Dólar Australiano'),
    ('CHF', 'CHF — Franco Suíço'),
    ('CNY', 'CNY — Yuan Chinês'),
    ('PEN', 'PEN — Sol Peruano'),
    ('UYU', 'UYU — Peso Uruguaio'),
    ('BOB', 'BOB — Boliviano'),
    ('PYG', 'PYG — Guarani Paraguaio'),
]


def _buscar_rates(moeda_base: str) -> dict | None:
    entrada = _cache.get(moeda_base)
    if entrada and (time.time() - entrada['timestamp']) < _CACHE_TTL:
        return entrada['rates']

    try:
        resp = requests.get(
            f'https://open.er-api.com/v6/latest/{moeda_base}',
            timeout=5,
        )
        if resp.status_code == 200:
            dados = resp.json()
            if dados.get('result') == 'success':
                rates = dados['rates']
                _cache[moeda_base] = {'rates': rates, 'timestamp': time.time()}
                return rates
    except Exception:
        pass

    return None


def obter_taxa(moeda_origem: str, moeda_destino: str) -> float | None:
    if moeda_origem == moeda_destino:
        return 1.0

    rates = _buscar_rates(moeda_origem)
    if rates and moeda_destino in rates:
        return rates[moeda_destino]

    return None


def converter(valor: float, moeda_origem: str, moeda_destino: str) -> float | None:
    taxa = obter_taxa(moeda_origem, moeda_destino)
    if taxa is None:
        return None
    return round(valor * taxa, 2)


def formatar(valor: float | None, moeda: str) -> str | None:
    if valor is None:
        return None
    simbolo = SIMBOLOS.get(moeda, moeda)
    return f"{simbolo} {valor:,.2f}"