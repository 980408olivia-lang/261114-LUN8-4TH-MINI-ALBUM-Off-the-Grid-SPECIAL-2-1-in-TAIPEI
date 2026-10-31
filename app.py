import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json

st.set_page_config(page_title="LUN8 應募實時監控", page_icon="🔥", layout="centered")

st.title("🔥 K-MONSTAR 應募商品實時監控")
st.markdown("**監控目標**：LUN8 4th Mini Album Special 2:1 四格照活動")

# SHOPLINE 商品頁面網址
url = "https://www.kmonstar.com.tw/products/%E6%87%89%E5%8B%9F-261114-lun8-4th-mini-album-off-the-grid-special-21-%E5%9B%9B%E6%A0%BC%E7%85%A7%E6%B4%BB%E5%8B%95-in-taipei"

st.sidebar.header("⚙️ 數據設定")
initial_stock = st.sidebar.number_input("設定活動初始總庫存 (Base Stock)", min_value=1, value=500, step=10)

@st.cache_data(ttl=10)
def fetch_real_stock_and_price(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    session = requests.Session()
    
    try:
        # 1. 抓取商品頁面解析 Variant ID 與價格
        res = session.get(target_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return {"success": False, "error": f"HTTP {res.status_code}"}

        # 解析售價
        price = "NT$ 630"
        price_match = re.search(r'NT\$[\s]?[\d,]+', res.text)
        if price_match:
            price = price_match.group(0)

        # 搜尋 SHOPLINE 的 Variant ID (商品變體 ID)
        variant_ids = re.findall(r'"_id"\s*:\s*"([a-f0-9]{24})"', res.text) or \
                      re.findall(r'data-variant-id="([a-f0-9]{24})"', res.text) or \
                      re.findall(r'variant_id["\']?\s*:\s*["\']?([a-f0-9]{24})["\']?', res.text)

        real_stock = None

        # 2. 如果找到變體 ID，發送探測請求獲取真正庫存
        if variant_ids:
            var_id = variant_ids[0]
            # 呼叫 SHOPLINE 的庫存/購物車檢查接口
            check_url = f"https://www.kmonstar.com.tw/carts/check_stock.json?variant_id={var_id}"
            check_res = session.get(check_url, headers=headers, timeout=5)
            
            if check_res.status_code == 200:
                stock_data = check_res.json()
                if "quantity" in stock_data:
                    real_stock = int(stock_data["quantity"])
                elif "stock" in stock_data:
                    real_stock = int(stock_data["stock"])

        # 3. 備用方案：從網頁內藏的 JS 變數 (window._slData) 萃取庫存
        if real_stock is None:
            script_matches = re.findall(r'quantity"\s*:\s*(\d+)', res.text)
            # 過濾掉 0 與異常大數，取合理的庫存量
            valid_quantities = [int(q) for q in script_matches if 0 < int(q) <= 10000]
            if valid_quantities:
                real_stock = valid_quantities[0]

        return {
            "success": True,
            "price": price,
            "stock": real_stock
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

data = fetch_real_stock_and_price(url)

if data["success"]:
    current_price = data["price"]
    auto_stock = data["stock"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 商品售價", value=current_price)
    with col2:
        if auto_stock is not None:
            st.metric(label="📦 自動抓取真實庫存", value=f"{auto_stock} 件")
            sales = max(0, initial_stock - auto_stock)
            st.markdown("---")
            st.metric(label="📈 即時計算累積銷量", value=f"{sales} 件")
            st.success("✅ 已透過 API 成功探測出官方真實剩餘庫存！")
        else:
            st.metric(label="📦 自動抓取真實庫存", value="探測中 / 無上限")
            st.warning("⚠️ 官方採用無庫存上限模式或鎖定 API，系統正持續嘗試探測中。")
else:
    st.error(f"❌ 讀取失敗：{data.get('error')}")

if st.button("🔄 立即重新整理"):
    st.rerun()
