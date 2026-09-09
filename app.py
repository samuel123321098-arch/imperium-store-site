from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

PRODUCTS_FILE = "data/products.json"
KEYS_FILE = "data/keys.json"

def carregar_produtos():
    if not os.path.exists(PRODUCTS_FILE):
        return {}
    
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        produtos = json.load(f)
    
    # Sincroniza o estoque automaticamente com as chaves cadastradas pelo bot no Discord
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f_keys:
                keys_data = json.load(f_keys)
                for sku, dados in produtos.items():
                    # O estoque do site passa a ser exatamente a quantidade de contas no keys.json
                    dados['estoque'] = len(keys_data.get(sku, []))
        except Exception:
            pass
            
    return produtos

@app.route("/")
def home():
    produtos = carregar_produtos()
    return render_template("index.html", produtos=produtos)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
