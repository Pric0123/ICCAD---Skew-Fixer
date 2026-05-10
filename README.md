<div align="center">

```
  ███████╗████████╗ █████╗     ██╗███╗   ██╗███████╗██╗ ██████╗ ██╗  ██╗████████╗
  ██╔════╝╚══██╔══╝██╔══██╗    ██║████╗  ██║██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝
  ███████╗   ██║   ███████║    ██║██╔██╗ ██║███████╗██║██║  ███╗███████║   ██║
  ╚════██║   ██║   ██╔══██║    ██║██║╚██╗██║╚════██║██║██║   ██║██╔══██║   ██║
  ███████║   ██║   ██║  ██║    ██║██║ ╚████║███████║██║╚██████╔╝██║  ██║   ██║
  ╚══════╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝ ╚═════╝╚═╝  ╚═╝   ╚═╝
```

### 把 IC 設計的「部落知識」翻譯成新人也能看懂的語言

**An AI-assisted translator that turns cryptic STA reports into onboarding-friendly knowledge cards.**

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-Llama_3.3_70B-orange)
![Parser](https://img.shields.io/badge/Parser-Deterministic_Hybrid-red)
![Domain](https://img.shields.io/badge/Domain-CAD%2FEDA-green)

</div>

---

## 🎯 為什麼做這個？

在 IC 設計團隊裡，一份 5 萬行的 STA report，**資深工程師看 10 秒就知道哪裡要改，新人看 3 個月還在學語彙**。Log 變成了「部落方言」，知識傳承靠肉身在旁邊看，老人離職就斷層。

**ChipMentor 透過「確定性解析 (Deterministic Parsing) + 大語言模型 (LLM)」的混合架構，精準提取關鍵數據並轉譯為易讀的知識卡片，解決 Log 密碼化與知識部落化的病灶。**

---

## 🔭 設計框架：觀點 → 策略 → 手法 → 驗證

### 觀點 (Perspective)
EDA 流程產生的所有資料，都是寫給資深工程師看的。我們需要一個 **Audience-aware（分眾感知）** 的翻譯層，讓新人、PM、跨團隊工程師都能用自己的語言理解同一份資料。

### 策略 (Strategy)
建立 **Deterministic Parser + LLM Hybrid** 架構。利用程式邏輯確保數據 100% 準確，利用 AI 進行人性化翻譯並排除幻覺風險。

### 手法 (Method)
1. **區塊化解析 (Block Parsing)**：將大型報告切割成獨立 Path 區塊，精準提取 Slack、Path Group 與 Setup/Hold 類型。
2. **邏輯深度計算 (Logic Depth Calculation)**：自動統計 Standard Cell 數量，量化路徑複雜度以輔助診斷。
3. **防幻覺護欄 (Guardrails)**：在 Prompt Level 建立物理規則，防止 LLM 在 Setup/Hold 判斷上產生錯誤建議（例如：禁止在 Hold violation 時建議減少邏輯）。
4. **低溫控制 (Low Temp Inference)**：將推理溫度設為 `0.2`，確保輸出穩定嚴謹，減少模型發散。

### 驗證 (Validation)
- ✅ **數據準確性**：Deterministic Parser 在 PrimeTime / OpenROAD 格式測試案例上達到 100% 正確率（n=4 paths）。大型 report 驗證尚在進行中。
- ✅ **防幻覺測試**：能精確區分 Max/Min 路徑並根據邏輯深度給予對應的物理修正建議。
- 🚧 **擴展性測試**：針對 >1MB 大型 report 的效能優化與截斷策略驗證中。

---

## 🎬 Before / After

### Before（原始 STA Report）
```text
PATH 1 - VIOLATED
  Startpoint : clk_div/q_reg[3]
  Endpoint   : alu/result_reg[7]
  slack (VIOLATED) : -0.347 ns
  ... (數百行邏輯節點與延遲數據)
```

### After（ChipMentor 產出的知識卡片）
```text
┌─ ChipMentor 知識卡片 ────────────────────────────────────┐
│  📋 Report 總覽                                          │
│  設計：cpu_core_top｜違規：2 條｜通過：1 條              │
│                                                          │
│  ⚠️ 違規路徑分析                                         │
│  PATH 1：clk_div → alu，slack -0.347 ns                  │
│  邏輯深度 4 gates，建議減少組合邏輯或換大 driving cell    │
│                                                          │
│  🔧 建議行動                                             │
│  1. 檢查 U1234/U1235 的 Fanout 與 Net Delay              │
│  2. 確認 Clock Tree 是否存在異常的 Skew                  │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 快速開始

### 環境需求
- Python 3.10+
- Linux / WSL2
- Groq API Key（[免費申請](https://console.groq.com)）

### 安裝與執行
```bash
git clone https://github.com/Pric0123/sta-insight.git
cd sta-insight

python3 -m venv ~/sta-insight-env
source ~/sta-insight-env/bin/activate

pip install groq python-dotenv rich

echo "GROQ_API_KEY=your_key_here" > .env

# 新人視角（預設）
python3 sta_parser.py sta_report_sample.txt

# 指定角色
python3 sta_parser.py sta_report_sample.txt --role rtl
python3 sta_parser.py sta_report_sample.txt --role backend
python3 sta_parser.py sta_report_sample.txt --role pm

# 管理層週報
python3 sta_parser.py sta_report_sample.txt --summary
```

---

## 🛠 技術堆疊

| 層級 | 技術 |
|---|---|
| **解析引擎** | Regex-based Deterministic Block Parser |
| **推理核心** | Llama 3.3 70B (via Groq Cloud Inference) |
| **防護機制** | Physical Rules Guardrails (Temperature=0.2) |
| **UI 渲染** | Rich (Terminal-based Knowledge Cards) |
| **執行環境** | Linux / WSL2 Ubuntu |

---

## 📍 目前限制（誠實揭露）

- ❗ **單檔處理**：目前一次僅支援單份 report 解析。
- ⚠️ **格式依賴**：支援 PrimeTime 與 OpenROAD 兩種格式，其他 EDA 工具格式尚未驗證。
- ⚠️ **樣本規模**：Deterministic Parser 目前在 n=4 paths 的測試案例上驗證，大型真實 report 的覆蓋率待補完。
- 🚧 **UI**：目前為 Terminal 介面，Streamlit Web UI 開發中。

---

## 🗺 Roadmap

- [x] 病灶一：STA report → 新人知識卡片
- [x] 病灶二：多角色分析（RTL / 後端 / 驗證 / PM）
- [x] 病灶三：管理層週報自動產生
- [x] OpenROAD 真實格式支援
- [ ] Streamlit Web UI
- [ ] 大型 report Chunking 優化
- [ ] CI/CD 整合

---

## 👤 關於作者

楊元蓁 (Price Yang) ｜ 中原大學 工業與系統工程學系 & 建築學系 雙主修

📧 willyang2002@gmail.com
🐙 [@Pric0123](https://github.com/Pric0123)

---

<div align="center">

**「真正的工程創新來自跨領域的視角。」**

</div>
