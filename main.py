from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import requests
import os
import yfinance as yf
from dotenv import load_dotenv
from openai import AzureOpenAI
import io
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

app = FastAPI()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
TRANSLATOR_KEY = os.getenv("TRANSLATOR_KEY")
TRANSLATOR_ENDPOINT = os.getenv("TRANSLATOR_ENDPOINT")

AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2024-02-01"
)


# -----------------------------
# ニュース検索（SerpAPI）
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

    for item in data.get("top_stories", []):
        articles.append({
            "title": safe(item.get("title")),
            "snippet": safe(item.get("snippet")),
            "link": safe(item.get("link")),
            "source": safe(item.get("source"))
        })

    for item in data.get("organic_results", []):
        articles.append({
            "title": safe(item.get("title")),
            "snippet": safe(item.get("snippet")),
            "link": safe(item.get("link")),
            "source": safe(item.get("source"))
        })

    for item in data.get("news_results", []):
        articles.append({
            "title": safe(item.get("title")),
            "snippet": safe(item.get("snippet")),
            "link": safe(item.get("link")),
            "source": safe(item.get("source"))
        })

    return {"articles": articles[:5]}


# -----------------------------
# 英語要約（Azure OpenAI）
# -----------------------------
@app.get("/tools/summary")
def summary(url: str):
    prompt = f"""
Extract the main content from the following news article URL,
and summarize it in **5–7 lines of English** for an investor audience.

- Remove ads, menus, and irrelevant text
- Keep only the core news content
- Output in English only
- No bullet points

URL: {url}
"""

    res = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    text = res.choices[0].message.content
    return {"summary": text}


# -----------------------------
# 日本語要約（Azure Translator）
# -----------------------------
@app.get("/tools/summary_ja")
def summary_ja(text: str):
    headers = {
        "Ocp-Apim-Subscription-Key": TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": "japanwest",
        "Content-Type": "application/json"
    }

    body = [{"text": text}]
    base = TRANSLATOR_ENDPOINT.rstrip("/")
    url = f"{base}/translate?api-version=3.0&to=ja"

    res = requests.post(url, headers=headers, json=body)
    ja = res.json()[0]["translations"][0]["text"]
    return {"ja_summary": ja}


# -----------------------------
# JennyNeural 音声生成（Azure Speech）
# -----------------------------
@app.post("/tools/speech_jenny")
def speech_jenny(text: str):
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )

    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None
    )

    result = synthesizer.speak_text_async(text).get()

    return StreamingResponse(
        io.BytesIO(result.audio_data),
        media_type="audio/mpeg"
    )


# -----------------------------
# UI（要約ボタンだけ）
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
        body { font-size: 22px; padding: 20px; line-height: 1.6; }
        .ticker-btn { width: 48%; padding: 14px; margin: 5px; font-size: 22px; }
        .card { background:#f2f2f2; padding:18px; margin-top:20px; border-radius:12px; }
        .ja { background:#fff7d1; padding:10px; border-radius:8px; margin-top:10px; }
        button { width:100%; padding:14px; font-size:22px; margin-top:10px; }
        </style>
    </head>

    <body>
        <h2>USA Stock News</h2>

        <div style="display:flex; flex-wrap:wrap;">
            <button class="ticker-btn" onclick="setTicker('NVDA')">NVIDIA</button>
            <button class="ticker-btn" onclick="setTicker('AMD')">AMD</button>
            <button class="ticker-btn" onclick="setTicker('AI')">C3AI</button>
            <button class="ticker-btn" onclick="setTicker('INTC')">Intel</button>
            <button class="ticker-btn" onclick="setTicker('TSLA')">Tesla</button>
            <button class="ticker-btn" onclick="setTicker('QCOM')">Qualcomm</button>
            <button class="ticker-btn" onclick="setTicker('MSFT')">Microsoft</button>
            <button class="ticker-btn" onclick="setTicker('AAPL')">Apple</button>
        </div>

        <input id="ticker" placeholder="例: NVDA, MSFT, AAPL">
        <button onclick="search()">ニュース検索</button>

        <div id="result"></div>

        <script>

        function setTicker(t) {
            document.getElementById("ticker").value = t;
            search();
        }

        async function search() {
            const t = document.getElementById("ticker").value;
            const res = await fetch(`/tools/news?keyword=${t}`);
            const data = await res.json();

            let html = "";
            let i = 0;

            for (const n of data.articles) {
                html += `
                    <div class="card">
                        <a id="title_${i}" href="${n.link}" target="_blank">${n.title}</a><br>
                        <small>${n.source}</small>
                        <p id="eng_${i}">${n.snippet}</p>

                        <button onclick="showSummary(${i})">要約</button>

                        <div id="summary_${i}" class="ja"></div>
                        <div id="summary_ja_${i}" class="ja"></div>
                    </div>
                `;
                i++;
            }

            document.getElementById("result").innerHTML = html;
        }

        async function showSummary(i) {
            const url = document.getElementById("title_" + i).href;

            // ① 英語要約
            const res = await fetch(`/tools/summary?url=` + encodeURIComponent(url));
            const data = await res.json();
            const text = data.summary;
            document.getElementById("summary_" + i).innerText = text;

            // ② 日本語要約
            const res2 = await fetch(`/tools/summary_ja?text=` + encodeURIComponent(text));
            const data2 = await res2.json();
            document.getElementById("summary_ja_" + i).innerText = data2.ja_summary;

            // ③ JennyNeural 音声再生
            const audioRes = await fetch("/tools/speech_jenny?text=" + encodeURIComponent(text), {
                method: "POST"
            });

            const blob = await audioRes.blob();
            const audioURL = URL.createObjectURL(blob);
            new Audio(audioURL).play();
        }

        </script>
    </body>
    </html>
    """
