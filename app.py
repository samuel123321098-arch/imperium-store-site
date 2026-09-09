from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def carregar_json(nome_arquivo):
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

@app.route("/debug-json")
def debug_json():
    data_dir = os.path.join(BASE_DIR, "data")
    debug_info = {
        "current_dir": BASE_DIR,
        "files_in_base": os.listdir(BASE_DIR) if os.path.exists(BASE_DIR) else [],
        "files_in_data": os.listdir(data_dir) if os.path.exists(data_dir) else "Pasta data/ não existe",
        "loaded_products": carregar_json("products.json"),
        "loaded_keys": carregar_json("keys.json"),
    }
    return jsonify(debug_info)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)