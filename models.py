import json

LIVROS_NOMES = {
'Gn':'Gênesis','Ex':'Êxodo'
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
