"""
日本株式市場分析アプリ
Flask + Yahoo Finance API
"""

from flask import Flask, render_template, jsonify, request
from stock_analyzer import analyze_stock, analyze_all_stocks, add_stock, remove_stock, get_all_stocks

app = Flask(__name__)


@app.route("/")
def index():
    """メインページ"""
    return render_template("index.html")


@app.route("/api/stocks")
def api_stocks():
    """全銘柄の一覧を返す"""
    return jsonify(get_all_stocks())


@app.route("/api/analyze/all")
def api_analyze_all():
    """全銘柄の分析結果を返す"""
    results = analyze_all_stocks()
    return jsonify(results)


@app.route("/api/analyze/<code>")
def api_analyze(code: str):
    """指定銘柄の分析結果を返す"""
    result = analyze_stock(code)
    if result is None:
        return jsonify({"error": f"銘柄コード {code} のデータを取得できませんでした"}), 404
    return jsonify(result)


@app.route("/api/stocks/add", methods=["POST"])
def api_add_stock():
    """銘柄を追加する"""
    data = request.get_json()
    code = data.get("code", "")
    success, message = add_stock(code)
    return jsonify({"success": success, "message": message}), 200 if success else 400


@app.route("/api/stocks/remove", methods=["POST"])
def api_remove_stock():
    """銘柄を削除する"""
    data = request.get_json()
    code = data.get("code", "")
    success, message = remove_stock(code)
    return jsonify({"success": success, "message": message}), 200 if success else 400


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
