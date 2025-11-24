import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
import zipfile

def sort_contours(cnts, method="top-to-bottom"):
    # コマを読み順（上から下、左から右）に並べ替えるための関数
    reverse = False
    i = 1 # y座標でソート
    if method == "left-to-right":
        i = 0 # x座標でソート
        
    boundingBoxes = [cv2.boundingRect(c) for c in cnts]
    (cnts, boundingBoxes) = zip(*sorted(zip(cnts, boundingBoxes),
        key=lambda b:b[1][i], reverse=reverse))
    return (cnts, boundingBoxes)

def extract_panels(image_file):
    # ファイルをOpenCV形式に変換
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # グレースケール化
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 二値化（白黒はっきりさせる）。枠線が黒、背景が白と仮定して反転
    # 画像によって閾値(200)の調整が必要な場合があります
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # 輪郭抽出
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    panel_images = []
    
    # 輪郭が見つかった場合のみ処理
    if contours:
        # 上から順に並び替え
        (contours, _) = sort_contours(contours, method="top-to-bottom")

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            
            # 小さすぎるノイズを除去（画像の面積の0.5%以下は無視するなど）
            img_area = img.shape[0] * img.shape[1]
            if w * h < img_area * 0.01: 
                continue
            
            # 切り出し
            crop = img[y:y+h, x:x+w]
            
            # OpenCV(BGR) -> PIL(RGB)変換
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(crop_rgb)
            panel_images.append(pil_img)
            
    return panel_images

# --- Streamlit UI ---
st.title("🖼️ マンガのコマ割りカッター")
st.write("マンガの画像をアップロードすると、コマを自動検出して分割します。")

uploaded_file = st.file_uploader("画像を選択してください", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # オリジナル画像の表示
    st.image(uploaded_file, caption='アップロードされた画像', use_column_width=True)
    
    if st.button('コマを抽出する'):
        with st.spinner('画像処理中...'):
            # コマ抽出処理の実行
            uploaded_file.seek(0) # ファイルポインタをリセット
            panels = extract_panels(uploaded_file)
            
            if not panels:
                st.error("コマが見つかりませんでした。画像のコントラストが低いか、枠線がはっきりしていない可能性があります。")
            else:
                st.success(f"{len(panels)}個のコマを検出しました！")
                
                # ZIPファイルの作成準備
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    
                    # ギャラリー表示用のカラム設定
                    cols = st.columns(3)
                    
                    for i, panel in enumerate(panels):
                        # 画面表示
                        with cols[i % 3]:
                            st.image(panel, caption=f"Panel {i+1}", use_column_width=True)
                        
                        # ZIPに追加するためのバイト変換
                        img_byte_arr = io.BytesIO()
                        panel.save(img_byte_arr, format='PNG')
                        zf.writestr(f"panel_{i+1:02d}.png", img_byte_arr.getvalue())
                
                # ダウンロードボタン
                st.download_button(
                    label="📦 まとめてダウンロード (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="panels.zip",
                    mime="application/zip"
                )