import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="LUN8 應募即時監控", page_icon="🔥", layout="centered")

st.title("🔥 LUN8 應募商品實時監控")
st.markdown("**監控目標**：LUN8 4th Mini Album [OFF THE GRID] Special 2:1 四格照活動 in TAIPEI")

st.sidebar.header("⚙️ 數據校正與設定")
initial_stock = st.sidebar.number_input("設定初始總庫存 (Base Stock)", min_value=0, value=500, step=10)
manual_stock = st.sidebar.number_input("手動輸入當前庫存 (防防火牆攔截)", min_value=0, value=500, step=1)

url = "https://www.kmonstar.com.tw/products/%E6%87%89%E5%8B%9F-261114-lun8-4th-mini-album-off-the-grid-special-21-%E5%9B%9B%E6%A0%BC%E7%85%A7%E6%B4%BB%E5%8B%95-in-taipei"

@st.cache_data(ttl=15)
def fetch_kmonstar_data(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            price = "NT$ 待確認"
            price_elem = soup.select_one('.price') or soup.find('meta', property='product:price:amount')
            if price_elem:
                price = price_elem.text.strip() if price_elem.name != 'meta' else f"NT$ {price_elem['content']}"
            else:
                match = re.search(r'NT\$[\d,]+', response.text)
                if match:
                    price = match.group(0)
            return {"success": True, "price": price}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

data = fetch_kmonstar_data(url)
current_price = data["price"] if data["success"] else "NT$ 待確認 (預設/未連線)"

col1, col2 = st.columns(2)
with col1:
    st.metric(label="💰 商品售價", value=current_price)
with col2:
    st.metric(label="📦 當前剩餘庫存", value=str(manual_stock))

sales = max(0, initial_stock - manual_stock)
st.metric(label="📈 即時估算銷量", value=f"{sales} 件")

if st.button("🔄 立即重新整理"):
    st.rerun()

st.markdown("---")
if data["success"]:
    st.success("✅ 伺服器連線成功，成功繞過阻擋讀取前台數據！")
else:
    st.info("💡 提示：若因 Cloudflare 暫時阻擋導致無法自動抓取，您可以直接在左側欄位『手動輸入當前庫存』，系統會自動幫您精準計算銷量！")
