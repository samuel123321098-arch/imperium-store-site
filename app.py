from flask import Flask, render_template
import json
import os

app = Flask(__name__)

PRODUCTS_FILE = "data/products.json"

def carregar_produtos():
    if not os.path.exists(PRODUCTS_FILE):
        return {}
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

@app.route("/")
def home():
    produtos = carregar_produtos()
    return render_template("index.html", produtos=produtos)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
