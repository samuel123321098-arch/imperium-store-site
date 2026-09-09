from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

def achar_arquivo(nome):
    """Procura o arquivo na raiz ou dentro da pasta data/"""
    caminhos = [nome, os.path.join("data", nome), os.path.join("..", nome)]
    for caminho in caminhos:
        if os.path.exists(caminho):
            return caminho
    return nome

@app.route("/")
def home():
    prod_path = achar_arquivo("products.json")
    produtos = {}
    
    if os.path.exists(prod_path):
        with open(prod_path, "r", encoding="utf-8") as f:
            produtos = json.load(f)
            
    # Procura o arquivo de chaves/estoque em qualquer lugar (raiz ou data/)
    keys_path = achar_arquivo("keys.json")
    if os.path.exists(keys_path):
        try:
            with open(keys_path, "r", encoding="utf-8") as f:
                keys_data = json.load(f)
                
                if isinstance(keys_data, dict):
                    for sku, dados in produtos.items():
                        sku_limpo = sku.strip().upper()
                        estoque_encontrado = None
                        
                        # Procura o SKU ignorando maiúsculas/minúsculas ou pequenos espaços
                        for k, v in keys_data.items():
                            if k.strip().upper() == sku_limpo:
                                if isinstance(v, list):
                                    estoque_encontrado = len(v)
                                elif isinstance(v, (int, float)):
                                    estoque_encontrado = int(v)
                                break
                        
                        if estoque_encontrado is not None:
                            dados['estoque'] = estoque_encontrado
        except Exception as e:
            print(f"Erro ao ler chaves: {e}")

    return render_template("index.html", produtos=produtos)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)