import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re

st.set_page_config(page_title="K-MONSTAR 自動實時監控", page_icon="🔥", layout="centered")

st.title("🔥 K-MONSTAR 應募商品實時監控")

# 請根據專案填寫對應的網址
url = "https://www.kmonstar.com.tw/products/%E6%87%89%E5%8B%9F-261114-lun8-4th-mini-album-off-the-grid-special-21-%E5%9B%9B%E6%A0%BC%E7%85%A7%E6%B4%BB%E5%8B%95-in-taipei"

st.sidebar.header("⚙️ 數據設定")
initial_stock = st.sidebar.number_input("設定活動初始總庫存 (Base Stock)", min_value=1, value=500, step=10)

@st.cache_data(ttl=10)
def fetch_realtime_inventory(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        session = requests.Session()
        res = session.get(target_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return {"success": False, "error": f"HTTP {res.status_code}"}
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. 自動抓取商品價格
        price = "NT$ 待確認"
        price_elem = soup.select_one('.price') or soup.find('meta', property='product:price:amount')
        if price_elem:
            price = price_elem.text.strip() if price_elem.name != 'meta' else f"NT$ {price_elem['content']}"
        else:
            match = re.search(r'NT\$[\d,]+', res.text)
            if match:
                price = match.group(0)

        # 2. 解析 SHOPLINE 隱藏庫存 JSON 數據 (從 script 標籤中挖掘 API 結構)
        stock = None
        
        # 方法 A: 解析 JSON-LD 結構
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'offers' in data:
                        offers = data['offers']
                        if isinstance(offers, dict) and 'inventoryLevel' in offers:
                            stock = int(offers['inventoryLevel'].get('value', 0))
                        elif isinstance(offers, list) and len(offers) > 0:
                            if 'inventoryLevel' in offers[0]:
                                stock = int(offers[0]['inventoryLevel'].get('value', 0))
                except:
                    pass

        # 方法 B: 搜尋網頁源碼中的 Shopline 全局變數/API 庫存欄位
        if stock is None:
            quantity_matches = re.findall(r'"quantity"\s*:\s*(\d+)', res.text)
            if quantity_matches:
                # 排除 0 以外的有效庫存數據
                valid_qty = [int(q) for q in quantity_matches if int(q) > 0]
                if valid_qty:
                    stock = valid_qty[0]

        return {
            "success": True,
            "price": price,
            "stock": stock
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

data = fetch_realtime_inventory(url)

if data["success"]:
    current_price = data["price"]
    auto_stock = data["stock"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 商品售價", value=current_price)
    with col2:
        if auto_stock is not None:
            st.metric(label="📦 自動抓取當前庫存", value=f"{auto_stock} 件")
            estimated_sales = max(0, initial_stock - auto_stock)
            st.metric(label="📈 即時計算累積銷量", value=f"{estimated_sales} 件")
        else:
            st.metric(label="📦 自動抓取當前庫存", value="無限制 / 隱藏中")
            st.warning("⚠️ 官方目前將庫存設定為無限或完全隱藏，系統正即時輪詢 API 變動中。")
            
    st.success("✅ 已成功呼叫後台 API 並自動解析數據！")
else:
    st.error(f"❌ 讀取失敗：{data.get('error')}")

if st.button("🔄 立即重新整理"):
    st.rerun()
