from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import os
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
TRANSLATOR_KEY = os.getenv("TRANSLATOR_KEY")
TRANSLATOR_ENDPOINT = os.getenv("TRANSLATOR_ENDPOINT")


# -----------------------------
# 英語ニュース検索 API（5件に制限）
# -----------------------------
@app.get("/tools/news")
def get_news(keyword: str):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": keyword + " stock news",
        "api_key": SERPER_API_KEY,
        "num": 5
    }

    response = requests.get(url, params=params)
    data = response.json()

    articles = []

    def safe(v):
        return v if v is not None else ""

    # top_stories
    for item in data.get("top_stories", []):
        articles.append({
            "title": safe(item.get("title")),
            "snippet": safe(item.get("snippet")),
            "link": safe(item.get("link")),
            "source": safe(item.get("source"))
        })

    # organic_results
    for item in data.get("organic_results", []):
        articles.append({
            "title": safe(item.get("title")),
            "snippet": safe(item.get("snippet")),
            "link": safe(item.get("link")),
            "source": safe(item.get("source"))
        })

    # news_results
    for item in data.get("news_results", []):
        articles.append({
            "title": safe(item.get("title")),
            "snippet": safe(item.get("snippet")),
            "link": safe(item.get("link")),
            "source": safe(item.get("source"))
        })

    # ★ 5件に制限
    articles = articles[:5]

    return {"keyword": keyword, "count": len(articles), "articles": articles}


# -----------------------------
# 翻訳 API（Azure Translator）
# -----------------------------
@app.get("/tools/translate")
def translate(text: str):
    try:
        headers = {
            "Ocp-Apim-Subscription-Key": TRANSLATOR_KEY,
            "Ocp-Apim-Subscription-Region": "japanwest",  # ★ Japan West
            "Content-Type": "application/json"
        }

        body = [{"text": text}]

        base = TRANSLATOR_ENDPOINT.rstrip("/")
        url = f"{base}/translate?api-version=3.0&to=ja"

        res = requests.post(url, headers=headers, json=body)

        print("=== Translator Debug ===")
        print("URL:", url)
        print("Status:", res.status_code)
        print("Response:", res.text)
        print("========================")

        ja = res.json()[0]["translations"][0]["text"]
        return {"ja": ja}

    except Exception as e:
        print("Translate error:", e)
        return {"ja": "翻訳エラー"}


# -----------------------------
# ストック価格 API
# -----------------------------
@app.get("/tools/stock_price")
def stock_price(symbol: str):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d")
    price = float(data["Close"].iloc[-1])
    return {"symbol": symbol, "price": price, "currency": "USD"}


# -----------------------------
# UI（翻訳ボタン付き）
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
        @media screen and (orientation: portrait) {
            body {
                font-size: 22px;
                line-height: 1.6;
                padding: 20px;
            }
            h2 {
                font-size: 26px;
                text-align: center;
            }
            input {
                font-size: 22px;
                padding: 14px;
                width: 100%;
            }
            button {
                font-size: 22px;
                padding: 14px;
                border-radius: 10px;
                margin-top: 10px;
            }
            .ticker-btn {
                width: 48%;
                background: #e8e8e8;
            }
            .card {
                font-size: 20px;
                padding: 18px;
                margin-top: 20px;
                border-radius: 12px;
                background: #f2f2f2;
            }
            a {
                font-size: 22px;
                font-weight: bold;
            }
            .ja {
                margin-top: 10px;
                padding: 10px;
                background: #fff7d1;
                border-radius: 8px;
                font-size: 20px;
            }
        }
        </style>
    </head>

    <body>
        <h2>USA Stock News</h2>

        <!-- ★ 銘柄ボタン一覧 -->
        <div style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:20px;">
            <button class="ticker-btn" onclick="setTicker('NVDA')">NVIDIA</button>
            <button class="ticker-btn" onclick="setTicker('AMD')">AMD</button>
            <button class="ticker-btn" onclick="setTicker('AI')">C3AI</button>
            <button class="ticker-btn" onclick="setTicker('INTC')">Intel</button>
            <button class="ticker-btn" onclick="setTicker('TSLA')">Tesla</button>
            <button class="ticker-btn" onclick="setTicker('PFE')">Pfizer</button>
            <button class="ticker-btn" onclick="setTicker('QCOM')">Qualcomm</button>
            <button class="ticker-btn" onclick="setTicker('AMZN')">Amazon</button>
            <button class="ticker-btn" onclick="setTicker('MSFT')">Microsoft</button>
            <button class="ticker-btn" onclick="setTicker('GOOG')">Google</button>
            <button class="ticker-btn" onclick="setTicker('AAPL')">Apple</button>
            <button class="ticker-btn" onclick="setTicker('JNJ')">Johnson & Johnson</button>
            <button class="ticker-btn" onclick="setTicker('SOLV')">Solvay</button>
            <button class="ticker-btn" onclick="setTicker('MMM')">3M</button>
            <button class="ticker-btn" onclick="setTicker('VZ')">Verizon</button>
            <button class="ticker-btn" onclick="setTicker('XOM')">ExxonMobil</button>
            <button class="ticker-btn" onclick="setTicker('T')">AT&T</button>
        </div>

        <!-- 手入力も残す（任意） -->
        <input id="ticker" placeholder="例: QCOM, AAPL, MSFT">
        <button onclick="search()">ニュース検索</button>

        <div id="result"></div>

        <script>

        // ★ ボタンを押したら ticker にセットして自動検索
        function setTicker(t) {
            document.getElementById("ticker").value = t;
            search();
        }

        async function search() {
            const t = document.getElementById("ticker").value;
            const url = `/tools/news?keyword=${t}`;
            const res = await fetch(url);
            const data = await res.json();

            let html = "<h3>検索結果</h3>";
            let index = 0;

            for (const n of data.articles) {
                html += `
                    <div class="card">
                        <a id="title_${index}" href="${n.link}" target="_blank">${n.title}</a><br>
                        <small>${n.source}</small><br>

                        <p id="eng_${index}">${n.snippet}</p>

                        <button onclick="translateText(${index})">翻訳</button>
                        <div id="ja_${index}" class="ja"></div>
                    </div>
                `;
                index++;
            }
            document.getElementById("result").innerHTML = html;
        }

        async function translateText(i) {
            let eng = document.getElementById("eng_" + i).innerText;

            // ★ snippet が空なら title を翻訳
            if (!eng || eng.trim() === "") {
                eng = document.getElementById("title_" + i).innerText;
            }

            const url = `/tools/translate?text=` + encodeURIComponent(eng);
            const res = await fetch(url);
            const data = await res.json();

            document.getElementById("ja_" + i).innerHTML = data.ja;
        }
        </script>
    </body>
    </html>
    """
