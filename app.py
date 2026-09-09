from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

# Pega o diretório exato onde o app.py está rodando no servidor
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def carregar_json(nome_arquivo):
    # Tenta nas duas localizações mais prováveis (raiz ou pasta data/)
    caminhos = [
        os.path.join(BASE_DIR, nome_arquivo),
        os.path.join(BASE_DIR, "data", nome_arquivo)
    ]
    for caminho in caminhos:
        if os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

@app.route("/")
def home():
    produtos = carregar_json("products.json")
    keys_data = carregar_json("keys.json")
    
    if produtos and keys_data:
        for sku, dados in produtos.items():
            sku_limpo = sku.strip().upper()
            for k, v in keys_data.items():
                if k.strip().upper() == sku_limpo:
                    if isinstance(v, list):
                        dados['estoque'] = len(v)
                    break
                    
    return render_template("index.html", produtos=produtos)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)