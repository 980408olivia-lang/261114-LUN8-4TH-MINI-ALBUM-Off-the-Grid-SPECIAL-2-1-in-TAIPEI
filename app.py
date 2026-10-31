import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re

st.set_page_config(page_title="LUN8 應募實時監控", page_icon="🔥", layout="centered")

st.title("🔥 K-MONSTAR 應募商品實時監控")

# SHOPLINE 商品頁面網址
url = "https://www.kmonstar.com.tw/products/%E6%87%89%E5%8B%9F-261114-lun8-4th-mini-album-off-the-grid-special-21-%E5%9B%9B%E6%A0%BC%E7%85%A7%E6%B4%BB%E5%8B%95-in-taipei"

st.sidebar.header("⚙️ 數據設定")
initial_stock = st.sidebar.number_input("設定活動初始總庫存", min_value=1, value=500, step=10)
manual_stock_input = st.sidebar.number_input("手動備用庫存 (抓取失敗時使用)", min_value=0, value=500, step=1)

@st.cache_data(ttl=5)
def fetch_shopline_inventory(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    try:
        res = requests.get(target_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return {"success": False, "error": f"HTTP {res.status_code}"}
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 抓取售價
        price = "NT$ 630"
        price_match = re.search(r'NT\$[\s]?[\d,]+', res.text)
        if price_match:
            price = price_match.group(0)

        # 深度解析 SHOPLINE 前台 JavaScript 變數內的庫存 (quantity / stock)
        stock = None
        
        # 搜尋 variants / inventory 關鍵字區塊
        patterns = [
            r'"quantity"\s*:\s*(\d+)',
            r'"inventory_quantity"\s*:\s*(\d+)',
            r'"stock"\s*:\s*(\d+)',
            r'quantity:\s*(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, res.text)
            if matches:
                # 取得匹配到的數值
                nums = [int(m) for m in matches]
                # 排除過大值 (如 ID) 取得合理的庫存數字
                valid_nums = [n for n in nums if n <= 10000]
                if valid_nums:
                    stock = valid_nums[0]
                    break

        return {"success": True, "price": price, "stock": stock}
    except Exception as e:
        return {"success": False, "error": str(e)}

data = fetch_shopline_inventory(url)

if data["success"]:
    current_price = data["price"]
    auto_stock = data["stock"]
    
    # 若自動抓取成功則使用自動庫存，否則使用手動備用庫存
    final_stock = auto_stock if auto_stock is not None else manual_stock_input
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 商品售價", value=current_price)
    with col2:
        st.metric(label="📦 當前剩餘庫存", value=f"{final_stock} 件")
        
    # 計算並強制顯示銷售數量
    estimated_sales = max(0, initial_stock - final_stock)
    st.markdown("---")
    st.metric(label="📈 即時估算銷量", value=f"{estimated_sales} 件")

    if auto_stock is not None:
        st.success(f"✅ 成功從網頁源碼抓到精準庫存：{auto_stock} 件！")
    else:
        st.info("💡 目前使用左側設定庫存估算中。")
else:
    st.error(f"❌ 讀取失敗：{data.get('error')}")

if st.button("🔄 立即重新整理"):
    st.rerun()
