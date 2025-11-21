import json

LIVROS_NOMES = {
    'gn': 'Gênesis',
    'ex': 'Êxodo',
    'lv': 'Levítico',
    'nm': 'Números',
    'dt': 'Deuteronômio',
    'js': 'Josué',
    'jz': 'Juízes',
    'rt': 'Rute',
    '1sm': '1 Samuel',
    '2sm': '2 Samuel',
    '1rs': '1 Reis',
    '2rs': '2 Reis',
    '1cr': '1 Crônicas',
    '2cr': '2 Crônicas',
    'ed': 'Esdras',
    'ne': 'Neemias',
    'et': 'Ester',
    'jó': 'Jó',        # <- com acento, ok!
    'sl': 'Salmos',
    'pv': 'Provérbios',
    'ec': 'Eclesiastes',
    'ct': 'Cantares',
    'is': 'Isaías',
    'jr': 'Jeremias',
    'lm': 'Lamentações',
    'ez': 'Ezequiel',
    'dn': 'Daniel',
    'os': 'Oséias',
    'jl': 'Joel',
    'am': 'Amós',
    'ob': 'Obadias',
    'jn': 'Jonas',
    'mq': 'Miquéias',
    'na': 'Naum',
    'hc': 'Habacuque',
    'sf': 'Sofonias',
    'ag': 'Ageu',
    'zc': 'Zacarias',
    'ml': 'Malaquias',
    'mt': 'Mateus',
    'mc': 'Marcos',
    'lc': 'Lucas',
    'jo': 'João',
    'atos': 'Atos',
    'rm': 'Romanos',
    '1co': '1 Coríntios',
    '2co': '2 Coríntios',
    'gl': 'Gálatas',
    'ef': 'Efésios',
    'fp': 'Filipenses',
    'cl': 'Colossenses',
    '1ts': '1 Tessalonicenses',
    '2ts': '2 Tessalonicenses',
    '1tm': '1 Timóteo',
    '2tm': '2 Timóteo',
    'tt': 'Tito',
    'fm': 'Filemom',
    'hb': 'Hebreus',
    'tg': 'Tiago',
    '1pe': '1 Pedro',
    '2pe': '2 Pedro',
    '1jo': '1 João',
    '2jo': '2 João',
    '3jo': '3 João',
    'jd': 'Judas',
    'ap': 'Apocalipse'
}

class Versiculo:
    def __init__(self,numero,texto): self.numero=numero; self.texto=texto
class Capitulo:
    def __init__(self,numero): self.numero=numero; self.versiculos=[]
    def adicionar_versiculo(self,texto): self.versiculos.append(Versiculo(len(self.versiculos)+1,texto))
    def get_versiculo(self,numero):
        if 1<=numero<=len(self.versiculos): return self.versiculos[numero-1]
        return None
class Livro:
    def __init__(self,abreviacao):
        self.abrev=abreviacao
        self.nome=LIVROS_NOMES.get(abreviacao,abreviacao.capitalize())
        self.capitulos=[]
    def adicionar_capitulo(self,capitulo): self.capitulos.append(capitulo)
    def get_capitulo(self,numero):
        if 1<=numero<=len(self.capitulos): return self.capitulos[numero-1]
        return None
def carregar_biblia(caminho_arquivo):
    with open(caminho_arquivo,'r',encoding='utf-8-sig') as f: biblia_json=json.load(f)
    livros=[]
    for livro_data in biblia_json:
        livro=Livro(livro_data['abbrev'])
        for i,cap in enumerate(livro_data['chapters'],1):
            c=Capitulo(i)
            for v in cap: c.adicionar_versiculo(v)
            livro.adicionar_capitulo(c)
        livros.append(livro)
    return livros
