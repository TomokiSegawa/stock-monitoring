// ===========================================
// 日本株アナライザー - フロントエンド
// ===========================================

let stockData = [];
let currentCardIndex = 0;

// ==================== Init ====================
document.addEventListener("DOMContentLoaded", () => {
    setupNavigation();
    setupAddForm();
    loadAllData();
});

// ==================== Navigation ====================
function setupNavigation() {
    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            const view = btn.dataset.view;
            document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
            document.getElementById(`${view}-view`).classList.add("active");

            if (view === "summary") renderSummaryTable();
            if (view === "add") loadRegisteredStocks();
        });
    });
}

// ==================== Data Loading ====================
async function loadAllData() {
    showLoading(true);
    try {
        const res = await fetch("/api/analyze/all");
        stockData = await res.json();
        renderCards();
        showLoading(false);
    } catch (err) {
        document.getElementById("loading").innerHTML =
            `<p style="color: var(--red);">データの取得に失敗しました。再読み込みしてください。</p>`;
    }
}

function showLoading(show) {
    document.getElementById("loading").classList.toggle("hidden", !show);
    document.getElementById("card-container").style.display = show ? "none" : "block";
    document.getElementById("card-nav").style.display = show ? "none" : "flex";
}

// ==================== Card Rendering ====================
function renderCards() {
    const wrapper = document.getElementById("card-wrapper");
    wrapper.innerHTML = "";

    stockData.forEach((stock, idx) => {
        const card = document.createElement("div");
        card.className = "stock-card";
        card.innerHTML = buildCardHTML(stock);
        wrapper.appendChild(card);
    });

    currentCardIndex = 0;
    updateCardPosition();
    setupSwipe();

    // Draw charts after rendering
    stockData.forEach((stock, idx) => {
        drawMiniChart(`chart-${stock.code}`, stock.recent_prices);
    });
}

function buildCardHTML(stock) {
    const changeCls = stock.today_change >= 0 ? "positive" : "negative";
    const changeSign = stock.today_change >= 0 ? "+" : "";
    const yesterdayCls = stock.yesterday_change >= 0 ? "positive" : "negative";
    const yesterdaySign = stock.yesterday_change >= 0 ? "+" : "";
    const weekCls = stock.week_change >= 0 ? "positive" : "negative";
    const weekSign = stock.week_change >= 0 ? "+" : "";
    const avg3mCls = stock.vs_3m_avg_pct >= 0 ? "positive" : "negative";
    const avg3mSign = stock.vs_3m_avg_pct >= 0 ? "+" : "";

    let signalsHTML = stock.signals.map(s => `
        <div class="signal-item">
            <span class="signal-name">${s.name}</span>
            <span class="signal-detail">${s.detail}</span>
            <span class="signal-dot ${s.direction}"></span>
        </div>
    `).join("");

    return `
    <div class="card-inner">
        <div class="card-header">
            <div class="stock-identity">
                <h2>${stock.name}</h2>
                <div class="stock-code">${stock.code}.T</div>
            </div>
            <div class="current-price">
                <div class="price">&yen;${stock.current_price.toLocaleString()}</div>
                <div class="change ${changeCls}">${changeSign}${stock.today_change.toLocaleString()} (${changeSign}${stock.today_change_pct}%)</div>
            </div>
        </div>

        <div class="recommendation-badge rec-${stock.recommendation}">
            ${stock.recommendation_label}
            <span style="font-size: 0.75rem; font-weight: 400; margin-left: 8px;">スコア: ${stock.total_score}</span>
        </div>

        <div class="price-summary">
            <div class="summary-item">
                <div class="label">本日の変動</div>
                <div class="value ${changeCls}">${changeSign}${stock.today_change_pct}%</div>
            </div>
            <div class="summary-item">
                <div class="label">昨日の変動</div>
                <div class="value ${yesterdayCls}">${yesterdaySign}${stock.yesterday_change_pct}%</div>
            </div>
            <div class="summary-item">
                <div class="label">週間変動</div>
                <div class="value ${weekCls}">${weekSign}${stock.week_change_pct}%</div>
            </div>
            <div class="summary-item">
                <div class="label">3ヶ月平均比</div>
                <div class="value ${avg3mCls}">${avg3mSign}${stock.vs_3m_avg_pct}%</div>
            </div>
        </div>

        <div class="mini-chart">
            <h3>過去30日の値動き</h3>
            <canvas class="chart-canvas" id="chart-${stock.code}"></canvas>
        </div>

        <div class="technicals">
            <div class="tech-item">
                <div class="tech-label">SMA5</div>
                <div class="tech-value">${stock.sma5 ? stock.sma5.toLocaleString() : "-"}</div>
            </div>
            <div class="tech-item">
                <div class="tech-label">SMA25</div>
                <div class="tech-value">${stock.sma25 ? stock.sma25.toLocaleString() : "-"}</div>
            </div>
            <div class="tech-item">
                <div class="tech-label">SMA75</div>
                <div class="tech-value">${stock.sma75 ? stock.sma75.toLocaleString() : "-"}</div>
            </div>
            <div class="tech-item">
                <div class="tech-label">RSI</div>
                <div class="tech-value">${stock.rsi}</div>
            </div>
            <div class="tech-item">
                <div class="tech-label">MACD</div>
                <div class="tech-value">${stock.macd}</div>
            </div>
            <div class="tech-item">
                <div class="tech-label">出来高比</div>
                <div class="tech-value">${stock.volume_ratio}x</div>
            </div>
        </div>

        <div class="signals-section">
            <h3>分析シグナル</h3>
            ${signalsHTML}
        </div>

        <div class="last-updated">最終更新: ${stock.last_updated}</div>
    </div>
    `;
}

// ==================== Card Navigation ====================
function updateCardPosition() {
    const wrapper = document.getElementById("card-wrapper");
    wrapper.style.transform = `translateX(-${currentCardIndex * 100}%)`;

    document.getElementById("prev-btn").disabled = currentCardIndex === 0;
    document.getElementById("next-btn").disabled = currentCardIndex >= stockData.length - 1;
    document.getElementById("card-indicator").textContent =
        `${currentCardIndex + 1} / ${stockData.length}`;
}

document.getElementById("prev-btn").addEventListener("click", () => {
    if (currentCardIndex > 0) {
        currentCardIndex--;
        updateCardPosition();
    }
});

document.getElementById("next-btn").addEventListener("click", () => {
    if (currentCardIndex < stockData.length - 1) {
        currentCardIndex++;
        updateCardPosition();
    }
});

// ==================== Swipe ====================
function setupSwipe() {
    const container = document.getElementById("card-container");
    let startX = 0;
    let isDragging = false;

    container.addEventListener("touchstart", e => {
        startX = e.touches[0].clientX;
        isDragging = true;
    }, { passive: true });

    container.addEventListener("touchend", e => {
        if (!isDragging) return;
        isDragging = false;
        const endX = e.changedTouches[0].clientX;
        const diff = startX - endX;

        if (Math.abs(diff) > 50) {
            if (diff > 0 && currentCardIndex < stockData.length - 1) {
                currentCardIndex++;
            } else if (diff < 0 && currentCardIndex > 0) {
                currentCardIndex--;
            }
            updateCardPosition();
        }
    }, { passive: true });
}

// ==================== Mini Chart ====================
function drawMiniChart(canvasId, prices) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !prices || prices.length === 0) return;

    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const padding = { top: 10, right: 10, bottom: 20, left: 50 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    const closes = prices.map(p => p.close);
    const minPrice = Math.min(...closes) * 0.998;
    const maxPrice = Math.max(...closes) * 1.002;
    const priceRange = maxPrice - minPrice || 1;

    // Grid lines
    ctx.strokeStyle = "rgba(46, 51, 72, 0.5)";
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(w - padding.right, y);
        ctx.stroke();

        const price = maxPrice - (priceRange / 4) * i;
        ctx.fillStyle = "#8b8fa3";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "right";
        ctx.fillText(price.toFixed(0), padding.left - 5, y + 4);
    }

    // Price line
    const isUp = closes[closes.length - 1] >= closes[0];
    const lineColor = isUp ? "#00b894" : "#e17055";

    ctx.beginPath();
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";

    prices.forEach((p, i) => {
        const x = padding.left + (chartW / (prices.length - 1)) * i;
        const y = padding.top + chartH - ((p.close - minPrice) / priceRange) * chartH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Gradient fill
    const lastX = padding.left + chartW;
    const lastY = padding.top + chartH - ((closes[closes.length - 1] - minPrice) / priceRange) * chartH;
    ctx.lineTo(lastX, padding.top + chartH);
    ctx.lineTo(padding.left, padding.top + chartH);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
    grad.addColorStop(0, isUp ? "rgba(0,184,148,0.2)" : "rgba(225,112,85,0.2)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = grad;
    ctx.fill();

    // Date labels
    ctx.fillStyle = "#8b8fa3";
    ctx.font = "9px sans-serif";
    ctx.textAlign = "center";
    const labelInterval = Math.max(1, Math.floor(prices.length / 5));
    prices.forEach((p, i) => {
        if (i % labelInterval === 0 || i === prices.length - 1) {
            const x = padding.left + (chartW / (prices.length - 1)) * i;
            ctx.fillText(p.date, x, h - 2);
        }
    });
}

// ==================== Summary Table ====================
function renderSummaryTable() {
    const container = document.getElementById("summary-table-container");
    const loading = document.getElementById("summary-loading");

    if (stockData.length === 0) {
        loading.classList.remove("hidden");
        return;
    }
    loading.classList.add("hidden");

    let html = `
    <table class="summary-table">
        <thead>
            <tr>
                <th>銘柄</th>
                <th>現在値</th>
                <th>本日</th>
                <th>週間</th>
                <th>3M平均比</th>
                <th>RSI</th>
                <th>判定</th>
            </tr>
        </thead>
        <tbody>
    `;

    stockData.forEach(stock => {
        const todayCls = stock.today_change_pct >= 0 ? "positive" : "negative";
        const todaySign = stock.today_change_pct >= 0 ? "+" : "";
        const weekCls = stock.week_change_pct >= 0 ? "positive" : "negative";
        const weekSign = stock.week_change_pct >= 0 ? "+" : "";
        const avg3mCls = stock.vs_3m_avg_pct >= 0 ? "positive" : "negative";
        const avg3mSign = stock.vs_3m_avg_pct >= 0 ? "+" : "";

        html += `
        <tr>
            <td class="stock-name-cell">${stock.code}<br><span style="font-weight:400;font-size:0.75rem;color:var(--text-secondary)">${stock.name}</span></td>
            <td>&yen;${stock.current_price.toLocaleString()}</td>
            <td class="${todayCls}">${todaySign}${stock.today_change_pct}%</td>
            <td class="${weekCls}">${weekSign}${stock.week_change_pct}%</td>
            <td class="${avg3mCls}">${avg3mSign}${stock.vs_3m_avg_pct}%</td>
            <td>${stock.rsi}</td>
            <td><span class="rec-badge rec-${stock.recommendation}">${stock.recommendation_label}</span></td>
        </tr>
        `;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;
}

// ==================== Add Stock ====================
function setupAddForm() {
    const input = document.getElementById("stock-code-input");
    const btn = document.getElementById("add-stock-btn");

    input.addEventListener("input", () => {
        input.value = input.value.replace(/[^0-9]/g, "");
    });

    input.addEventListener("keydown", e => {
        if (e.key === "Enter") btn.click();
    });

    btn.addEventListener("click", async () => {
        const code = input.value.trim();
        if (code.length !== 4) {
            showAddResult(false, "4桁の銘柄コードを入力してください");
            return;
        }

        btn.disabled = true;
        btn.textContent = "追加中...";

        try {
            const res = await fetch("/api/stocks/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code }),
            });
            const data = await res.json();
            showAddResult(data.success, data.message);

            if (data.success) {
                input.value = "";
                loadRegisteredStocks();
                // Reload analysis data
                loadAllData();
            }
        } catch (err) {
            showAddResult(false, "通信エラーが発生しました");
        } finally {
            btn.disabled = false;
            btn.textContent = "追加";
        }
    });
}

function showAddResult(success, message) {
    const el = document.getElementById("add-result");
    el.textContent = message;
    el.className = success ? "success" : "error";
}

async function loadRegisteredStocks() {
    const container = document.getElementById("registered-stocks");
    try {
        const res = await fetch("/api/stocks");
        const stocks = await res.json();
        const defaultCodes = ["9104", "8604", "6098", "8058"];

        container.innerHTML = Object.entries(stocks).map(([code, name]) => {
            const isDefault = defaultCodes.includes(code);
            return `
            <div class="registered-item">
                <div class="registered-info">
                    <span class="registered-code">${code}</span>
                    <span class="registered-name">${name}</span>
                    ${isDefault ? '<span class="default-badge">デフォルト</span>' : ""}
                </div>
                ${!isDefault ? `<button class="remove-btn" onclick="removeStock('${code}')">削除</button>` : ""}
            </div>
            `;
        }).join("");
    } catch (err) {
        container.innerHTML = `<p style="color:var(--red)">銘柄一覧の取得に失敗しました</p>`;
    }
}

async function removeStock(code) {
    try {
        const res = await fetch("/api/stocks/remove", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code }),
        });
        const data = await res.json();
        if (data.success) {
            loadRegisteredStocks();
            loadAllData();
        }
    } catch (err) {
        // silent fail
    }
}
