import streamlit as st
import neal
from pyqubo import Array, Constraint, LogEncInteger
import plotly.graph_objects as go
import os
import urllib.parse

# --- ページ設定 ---
st.set_page_config(page_title="Jiro Order Optimizer", layout="wide")

# --- CSS定義 (デザイン一元管理) ---
st.markdown("""
<style>
/* Google Fonts読み込み */
@import url('https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Reggae+One&display=swap');

/* 全体のフォント調整 */
body { font-family: "Hiragino Kaku Gothic Std", "メイリオ", sans-serif; }

/* 1. コール（呪文）のスタイル */
.jiro-call {
    background-color: #F4D03F; 
    color: #000000; 
    padding: 25px 10px; 
    border: 6px solid #000000; 
    border-radius: 4px; 
    text-align: center; 
    font-family: 'Reggae One', system-ui, sans-serif; /* 攻撃的な筆文字 */
    font-weight: 400;
    font-size: 42px; 
    letter-spacing: 0.05em;
    line-height: 1.4;
    text-shadow: 2px 2px 0px rgba(0,0,0,0.1); 
    box-shadow: 10px 10px 0px #000000; 
    margin-bottom: 20px;
}
.jiro-call-sub {
    font-family: "Arial Black", sans-serif;
    font-size: 14px;
    font-weight: normal;
    margin-top: 5px;
    opacity: 0.8;
}

/* 2. 食券風デザイン */
.ticket-container {
    display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;
}
.ticket {
    display: inline-block; padding: 8px 20px; border-radius: 4px;
    color: white; font-weight: bold; font-family: "Hiragino Kaku Gothic Std", sans-serif;
    box-shadow: 2px 2px 0px rgba(0,0,0,0.3); font-size: 18px;
    border: 1px solid rgba(255,255,255,0.3);
}
.ticket-noodle { background-color: #e67e22; }
.ticket-pork { background-color: #3498db; }
.ticket-vege { background-color: #27ae60; }
.ticket-fat { background-color: #95a5a6; }
.ticket-garlic { background-color: #f1c40f; color: black !important; }
.ticket-topping { background-color: #9b59b6; }
.ticket-soup_option { background-color: #e74c3c; }

/* 3. ボタン（Solve）のスタイル */
button[kind="primary"] {
    background-color: #F4D03F !important; color: #000000 !important;
    border: 2px solid #000000 !important; border-radius: 5px !important;
    font-weight: 900 !important; font-size: 20px !important;
    padding: 15px !important; box-shadow: 0px 5px 0px #000000 !important;
    transition: all 0.1s !important; margin-top: 10px; margin-bottom: 10px;
}
button[kind="primary"]:active {
    box-shadow: 0px 0px 0px #000000 !important; transform: translateY(5px) !important;
}
button[kind="primary"]:hover {
    background-color: #ffeb3b !important; border-color: #000000 !important; color: #000000 !important;
}

/* 4. スコア表示 */
.big-score { font-size: 48px; font-weight: bold; color: #F4D03F; text-shadow: 2px 2px 0px #000000; margin-bottom: -10px; }
.big-score-label { font-size: 14px; color: #888; }
</style>
""", unsafe_allow_html=True)

# --- データ定義 ---
items_data = {
    # 麺
    "麺通常(300g)":   {"cal": 1000, "sodium": 6.0, "satisfaction": 150, "price": 700, "cat": "noodle"},
    "麺少なめ(200g)": {"cal": 700,  "sodium": 5.0, "satisfaction": 100, "price": 700, "cat": "noodle"},
    "麺半分(150g)":   {"cal": 550,  "sodium": 4.5, "satisfaction": 80,  "price": 700, "cat": "noodle"},
    # 豚
    "豚(2枚・標準)":  {"cal": 0,    "sodium": 0.0, "satisfaction": 50,  "price": 0,   "cat": "pork"},
    "豚増し(5枚)":    {"cal": 500,  "sodium": 3.5, "satisfaction": 100, "price": 150, "cat": "pork"},
    "豚ダブル(8枚)":  {"cal": 1000, "sodium": 7.0, "satisfaction": 160, "price": 250, "cat": "pork"},
    # ヤサイ
    "ヤサイ少なめ":   {"cal": 20,   "sodium": 0.0, "satisfaction": 20,  "price": 0,   "cat": "vege"},
    "ヤサイ普通":     {"cal": 40,   "sodium": 0.0, "satisfaction": 40,  "price": 0,   "cat": "vege"},
    "ヤサイマシ":     {"cal": 60,   "sodium": 0.0, "satisfaction": 60,  "price": 0,   "cat": "vege"},
    "ヤサイマシマシ": {"cal": 100,  "sodium": 0.0, "satisfaction": 90,  "price": 0,   "cat": "vege"},
    # アブラ
    "アブラ無し":     {"cal": 0,    "sodium": 0.0, "satisfaction": 0,   "price": 0,   "cat": "fat"},
    "アブラ普通":     {"cal": 100,  "sodium": 0.2, "satisfaction": 30,  "price": 0,   "cat": "fat"},
    "アブラマシ":     {"cal": 270,  "sodium": 0.5, "satisfaction": 70,  "price": 0,   "cat": "fat"},
    "アブラマシマシ": {"cal": 500,  "sodium": 1.0, "satisfaction": 100, "price": 0,   "cat": "fat"},
    # ニンニク
    "ニンニク無し":   {"cal": 0,    "sodium": 0.0, "satisfaction": 0,   "price": 0,   "cat": "garlic"},
    "ニンニク少なめ": {"cal": 5,    "sodium": 0.0, "satisfaction": 20,  "price": 0,   "cat": "garlic"},
    "ニンニク普通":   {"cal": 20,   "sodium": 0.0, "satisfaction": 50,  "price": 0,   "cat": "garlic"},
    "ニンニク増し":   {"cal": 40,   "sodium": 0.0, "satisfaction": 80,  "price": 0,   "cat": "garlic"},
    # オプション
    "★スープ完飲(K.K.)": {"cal": 600, "sodium": 8.0, "satisfaction": 120, "price": 0, "cat": "soup_option"},
    "生卵":              {"cal": 80,   "sodium": 0.0, "satisfaction": 20,  "price": 50,  "cat": "topping"},
    "うずら(5個)":       {"cal": 100,  "sodium": 0.5, "satisfaction": 30,  "price": 150, "cat": "topping"},
}

item_names = list(items_data.keys())
num_items = len(item_names)
target_categories = ["noodle", "pork", "vege", "fat", "garlic"]

high_carb_items = ["麺通常(300g)"]
high_fat_items = ["アブラマシ", "アブラマシマシ"]
low_carb_items = ["麺半分(150g)"] 
volumey_vege = ["ヤサイマシ", "ヤサイマシマシ"]

# --- 関数群 ---

def calculate_details(selected_items, weights):
    total_cal = sum(items_data[n]["cal"] for n in selected_items)
    total_sodium = sum(items_data[n]["sodium"] for n in selected_items)
    total_price = sum(items_data[n]["price"] for n in selected_items)
    
    weighted_satisfaction = 0
    for n in selected_items:
        cat = items_data[n]["cat"]
        w = weights.get(cat, 1.0)
        if cat in ["soup_option", "topping"]: w = weights.get("topping", 1.0)
        weighted_satisfaction += items_data[n]["satisfaction"] * w
    
    randle_penalty = 0
    diet_bonus = 0
    
    if any(i in selected_items for i in high_carb_items) and any(i in selected_items for i in high_fat_items):
        randle_penalty = 50
    if any(i in selected_items for i in low_carb_items) and any(i in selected_items for i in volumey_vege):
        diet_bonus = 30 

    final_score = weighted_satisfaction + diet_bonus - randle_penalty
    
    return {
        "cal": total_cal, "sodium": total_sodium, "price": total_price,
        "base_sat": weighted_satisfaction, "randle_penalty": randle_penalty,
        "diet_bonus": diet_bonus, "final_score": final_score
    }

def create_gauge(value, user_limit, title, suffix, mode="standard"):
    bar_color = "#1f77b4"
    steps = []
    
    # 基準値
    STD_CAL_CAUTION, STD_CAL_DANGER = 1000, 1500
    STD_SODIUM_CAUTION, STD_SODIUM_DANGER = 6.0, 8.0

    if mode == "health_cal":
        bar_color = "#2ecc71"
        if value > STD_CAL_DANGER: bar_color = "#e74c3c"
        elif value > STD_CAL_CAUTION: bar_color = "#f39c12"
        steps = [
            {'range': [0, STD_CAL_CAUTION], 'color': '#e8f8f5'},
            {'range': [STD_CAL_CAUTION, STD_CAL_DANGER], 'color': '#fef9e7'},
            {'range': [STD_CAL_DANGER, max(value*1.2, user_limit*1.2)], 'color': '#fdedec'}
        ]
    elif mode == "health_sod":
        bar_color = "#2ecc71"
        if value > STD_SODIUM_DANGER: bar_color = "#e74c3c"
        elif value > STD_SODIUM_CAUTION: bar_color = "#f39c12"
        steps = [
            {'range': [0, STD_SODIUM_CAUTION], 'color': '#e8f8f5'},
            {'range': [STD_SODIUM_CAUTION, STD_SODIUM_DANGER], 'color': '#fef9e7'},
            {'range': [STD_SODIUM_DANGER, max(value*1.2, user_limit*1.2)], 'color': '#fdedec'}
        ]
    else:
        if value > user_limit: bar_color = "#e74c3c"
        steps = [{'range': [0, user_limit], 'color': '#f4f6f7'}]

    max_range = max(user_limit * 1.2, value * 1.1)
    if mode == "health_cal": max_range = max(max_range, 2000)
    if mode == "health_sod": max_range = max(max_range, 10)

    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = value, number = {'suffix': suffix},
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [None, max_range], 'tickwidth': 1},
            'bar': {'color': bar_color}, 'bgcolor': "white",
            'borderwidth': 1, 'bordercolor': "#ccc", 'steps': steps,
            'threshold': {'line': {'color': "black", 'width': 3}, 'thickness': 0.8, 'value': user_limit}
        }
    ))
    fig.update_layout(height=160, width=220, margin=dict(l=20,r=20,t=30,b=10), paper_bgcolor='rgba(0,0,0,0)')
    return fig

def draw_radar_chart(opt_stats, user_stats, limits):
    categories = ['カロリー', '塩分', '価格', '満足度(Score)']
    base_score = max(opt_stats['final_score'], user_stats.get('final_score', 1) if user_stats else 1) * 1.2
    
    def normalize(val, limit):
        return min((val / limit) * 100, 150) if limit > 0 else 0

    r_opt = [
        normalize(opt_stats['cal'], limits['cal']), normalize(opt_stats['sodium'], limits['sodium']),
        normalize(opt_stats['price'], limits['price']), (opt_stats['final_score'] / base_score) * 100
    ]
    
    data = [go.Scatterpolar(r=r_opt, theta=categories, fill='toself', name='Optimized', line_color='#1f77b4')]

    if user_stats:
        r_user = [
            normalize(user_stats['cal'], limits['cal']), normalize(user_stats['sodium'], limits['sodium']),
            normalize(user_stats['price'], limits['price']), (user_stats['final_score'] / base_score) * 100
        ]
        data.append(go.Scatterpolar(r=r_user, theta=categories, fill='toself', name='User Order', line_color='#ff7f0e'))

    data.append(go.Scatterpolar(r=[100]*4, theta=categories, mode='lines', name='Limit', line=dict(color='red', dash='dot', width=1), hoverinfo='skip'))

    layout = go.Layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 150]), bgcolor='rgba(0,0,0,0)'),
        showlegend=True,
        legend=dict(x=1, y=1, xanchor="right", yanchor="top", font=dict(size=14, color="black"), bgcolor="rgba(255,255,255,0.8)", bordercolor="#ccc", borderwidth=1),
        margin=dict(l=40, r=40, t=20, b=20), height=350, paper_bgcolor='rgba(0,0,0,0)',
    )
    return go.Figure(data=data, layout=layout)

# --- UI レイアウト開始 ---

# ヘッダー画像
img_file = "jiro2.jpg"  # 保存したファイル名 (適宜変更してください)
if os.path.exists(img_file):
    col_left_margin, col_img, col_right_margin = st.columns([1, 1, 1])
    with col_img: st.image(img_file, use_container_width=True)
    st.write("")
else:
    st.title("🍜 Jiro Order Optimizer")

# サイドバー: 比較設定
with st.sidebar:
    st.header("🛠️ 比較設定")
    enable_comparison = st.checkbox("「いつものオーダー」と比較", value=True)
    user_selection = []
    if enable_comparison:
        st.caption("普段頼んでいる内容を入力してください")
        u_noodle_sel = st.selectbox("いつもの麺", [k for k,v in items_data.items() if v['cat']=='noodle'])
        u_vege_sel = st.selectbox("いつものヤサイ", [k for k,v in items_data.items() if v['cat']=='vege'], index=1)
        u_garlic_sel = st.selectbox("いつものニンニク", [k for k,v in items_data.items() if v['cat']=='garlic'], index=2)
        u_pork_sel = st.selectbox("いつもの豚", [k for k,v in items_data.items() if v['cat']=='pork'])
        u_fat_sel = st.selectbox("いつものアブラ", [k for k,v in items_data.items() if v['cat']=='fat'], index=1)
        u_opts_sel = st.multiselect("いつものOP", [k for k,v in items_data.items() if v['cat'] in ['soup_option','topping']])
        user_selection = [u_noodle_sel, u_pork_sel, u_vege_sel, u_fat_sel, u_garlic_sel] + u_opts_sel

# メインエリア: 制約 & 優先度
c_limit, c_weight = st.columns([1, 1], gap="large")

with c_limit:
    st.subheader("1. 本日のリミット設定")
    st.caption("健康と財布を守るためのライン")
    budget = st.number_input("予算 (円)", 700, 2500, 1000, 50)
    cal_limit = st.slider("カロリー上限 (kcal)", 1000, 3000, 1800, 50, help="【目安】成人男性の1日の推定必要カロリー: 約2600kcal")
    sodium_limit = st.slider("塩分上限 (g)", 5.0, 15.0, 8.0, 0.5, help="【目安】成人男性の1日の目標量: 7.5g未満")

with c_weight:
    st.subheader("2. 今日の気分・優先度")
    st.caption("0.0(妥協可) 〜 1.0(絶対欲しい)")
    
    def transform_weight(val): return 1.5 * val + 0.5

    u_noodle = st.slider("麺の量", 0.0, 1.0, 0.5, 0.1, help="麺をたくさん食べたい欲求度は？")
    u_punch = st.slider("アブラ・ニンニク", 0.0, 1.0, 0.5, 0.1, help="アブラとニンニクの刺激をどれくらい求める？")
    u_vege = st.slider("ヤサイ", 0.0, 1.0, 0.5, 0.1, help="野菜のタワーをどれくらい積み上げたい？")
    u_pork = st.slider("豚", 0.0, 1.0, 0.5, 0.1, help="チャーシューをどれくらい重視する？")
    u_topping = st.slider("トッピング", 0.0, 1.0, 0.5, 0.1, help="うずらや生卵などのオプションをつけたい？")

    weights_map = {
        "noodle": transform_weight(u_noodle), "fat": transform_weight(u_punch), "garlic": transform_weight(u_punch),
        "vege": transform_weight(u_vege), "pork": transform_weight(u_pork),
        "topping": transform_weight(u_topping), "soup_option": transform_weight(u_topping)
    }

st.write("")
solve_btn = st.button("最適化を実行 (Solve)", type="primary", use_container_width=True)

# --- ソルバー実行 & 結果表示 ---
if solve_btn:
    st.subheader("📊 Optimization Results")
    status_text = st.empty()
    status_text.info("最適化計算中... (Simulated Annealing)")
    
    # QUBO構築
    x = Array.create('x', shape=num_items, vartype='BINARY')
    H_obj = 0
    for i, n in enumerate(item_names):
        cat = items_data[n]["cat"]
        w = weights_map.get(cat, 1.0)
        if cat in ["soup_option", "topping"]: w = weights_map.get("topping", 1.0)
        H_obj += -1 * items_data[n]["satisfaction"] * w * x[i]

    idx_map = {n: i for i, n in enumerate(item_names)}
    H_randle = 0
    for c_item in high_carb_items:
        for f_item in high_fat_items:
            if c_item in idx_map and f_item in idx_map: H_randle += 50.0 * x[idx_map[c_item]] * x[idx_map[f_item]]
    
    H_synergy = 0
    for l_item in low_carb_items:
        for v_item in volumey_vege:
            if l_item in idx_map and v_item in idx_map: H_synergy += -30.0 * x[idx_map[l_item]] * x[idx_map[v_item]]

    curr_sod = sum(items_data[n]["sodium"] * x[i] for i, n in enumerate(item_names))
    s_sod = LogEncInteger("s_sod", (0, int(sodium_limit * 10) + 5))
    H_sod = Constraint((curr_sod * 10 + s_sod - int(sodium_limit * 10))**2, label="Sodium")
    
    curr_cal = sum(items_data[n]["cal"] * x[i] for i, n in enumerate(item_names))
    s_cal = LogEncInteger("s_cal", (0, int(cal_limit) + 100))
    H_cal = Constraint((curr_cal + s_cal - cal_limit)**2, label="Calorie")
    
    curr_price = sum(items_data[n]["price"] * x[i] for i, n in enumerate(item_names))
    s_price = LogEncInteger("s_price", (0, budget))
    H_price = Constraint((curr_price + s_price - budget)**2, label="Price")
    
    H_exclusive = 0
    for cat in target_categories:
        indices = [i for i, n in enumerate(item_names) if items_data[n]["cat"] == cat]
        H_exclusive += Constraint((sum(x[i] for i in indices) - 1)**2, label=f"OneHot_{cat}")

    M = 5000.0
    H = H_obj + H_randle + H_synergy + M*(H_sod + H_cal + H_price + H_exclusive)
    
    model = H.compile()
    bqm = model.to_bqm()
    sampler = neal.SimulatedAnnealingSampler()
    response = sampler.sample(bqm, num_reads=1000, num_sweeps=1000, beta_range=(0.1, 5.0))
    
    decoded_samples = model.decode_sampleset(response)
    valid_plans, compromise_plans, seen_configs = [], [], set()

    for d_sample in decoded_samples:
        sample_dict = d_sample.sample
        current_config = tuple(sample_dict[f"x[{i}]"] for i in range(num_items))
        if current_config in seen_configs: continue
        seen_configs.add(current_config)

        sel_items = [n for idx, n in enumerate(item_names) if sample_dict.get(f"x[{idx}]") == 1]
        
        # バリデーション
        if not any(items_data[n]["cat"] == "noodle" for n in sel_items): continue
        is_cat_broken = False
        for cat in target_categories:
            if sum(1 for item in sel_items if items_data[item]["cat"] == cat) != 1:
                is_cat_broken = True; break
        if is_cat_broken: continue

        check_stats = calculate_details(sel_items, weights_map)
        is_over = (check_stats["price"] > budget) or (check_stats["cal"] > cal_limit) or (check_stats["sodium"] > sodium_limit)
        
        plan_data = {"sample": sample_dict, "stats": check_stats, "energy": d_sample.energy}
        if not is_over: valid_plans.append(plan_data)
        else: compromise_plans.append(plan_data)

    status_text.empty()
    final_plans = sorted(valid_plans, key=lambda x: x["energy"])[:3] if valid_plans else sorted(compromise_plans, key=lambda x: x["energy"])[:3]
    is_approximate = not valid_plans

    if not final_plans:
        st.error("有効なオーダーが見つかりませんでした。条件を緩和してください。")
        st.stop()

    if is_approximate:
        st.warning("⚠️ 指定された制約を厳密に満たすプランが見つかりませんでした。条件に近いプランを表示します。")

    u_stats = calculate_details(user_selection, weights_map) if enable_comparison and user_selection else None
    limits = {"cal": cal_limit, "sodium": sodium_limit, "price": budget}
    
    tabs = st.tabs([f"🏆 プラン A (Best)" if i==0 else f"プラン {chr(65+i)}" for i in range(len(final_plans))])
    
    for i, (tab, plan) in enumerate(zip(tabs, final_plans)):
        with tab:
            sample = plan["sample"]
            stats = plan["stats"]
            sel_list = [n for idx, n in enumerate(item_names) if sample.get(f"x[{idx}]") == 1]
            
            # --- コール生成 ---
            sel_vege = next((n for n in sel_list if items_data[n]["cat"] == "vege"), "")
            sel_garlic = next((n for n in sel_list if items_data[n]["cat"] == "garlic"), "")
            sel_fat = next((n for n in sel_list if items_data[n]["cat"] == "fat"), "")
            
            call_parts = []
            is_default = ("無し" in sel_garlic and "普通" in sel_vege and ("普通" in sel_fat or "無し" in sel_fat))
            
            if is_default:
                final_call = "そのままで"
            else:
                if "少なめ" in sel_garlic: call_parts.append("ニンニク少なめ")
                elif "普通" in sel_garlic: call_parts.append("ニンニク")
                elif "増し" in sel_garlic: call_parts.append("ニンニクマシ")
                
                if "少なめ" in sel_vege: call_parts.append("ヤサイ少なめ")
                elif "マシマシ" in sel_vege: call_parts.append("ヤサイマシマシ")
                elif "マシ" in sel_vege: call_parts.append("ヤサイ")
                
                if "マシマシ" in sel_fat: call_parts.append("アブラマシマシ")
                elif "マシ" in sel_fat: call_parts.append("アブラ")

                final_call = " ".join(call_parts) if call_parts else "そのままで"

            # 表示
            st.markdown(f'<div class="jiro-call">{final_call}<div class="jiro-call-sub">MAKE IT A GREAT DAY</div></div>', unsafe_allow_html=True)

            col_score, col_gauges = st.columns([1, 2])
            with col_score:
                st.markdown('<div class="big-score-label">満足度スコア (Objective)</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="big-score">{stats["final_score"]:.1f}</div>', unsafe_allow_html=True)
                if u_stats and u_stats['final_score'] > 0:
                    diff = stats['final_score'] - u_stats['final_score']
                    pct = (diff / u_stats['final_score']) * 100
                    color = "green" if pct >= 0 else "red"
                    st.markdown(f'<div style="color:{color}; font-weight:bold; font-size:18px;">{pct:+.1f}% vs いつもの</div>', unsafe_allow_html=True)

            with col_gauges:
                g1, g2, g3 = st.columns(3)
                # 【修正】 use_container_width=False に変更（固定幅で描画させるため）
                with g1: st.plotly_chart(create_gauge(stats['cal'], cal_limit, "カロリー", "kcal", mode="health_cal"), use_container_width=False, key=f"gc{i}")
                with g2: st.plotly_chart(create_gauge(stats['sodium'], sodium_limit, "塩分", "g", mode="health_sod"), use_container_width=False, key=f"gs{i}")
                with g3: st.plotly_chart(create_gauge(stats['price'], budget, "価格", "円", mode="budget"), use_container_width=False, key=f"gp{i}")

            st.markdown("---")
            r1, r2 = st.columns([1, 1])
            with r1:
                st.plotly_chart(draw_radar_chart(stats, u_stats, limits), use_container_width=True, key=f"radar_{i}")
            
            with r2:
                st.write("#### 📝 構成内容（食券）")
                tags_html = '<div class="ticket-container">'
                for item in sel_list:
                    cat = items_data[item]["cat"]
                    cat_class = f"ticket-{cat}" if cat in ["noodle", "pork", "vege", "fat", "garlic", "topping", "soup_option"] else "ticket-topping"
                    tags_html += f'<div class="ticket {cat_class}">{item}</div>'
                tags_html += '</div>'
                st.markdown(tags_html, unsafe_allow_html=True)
                
                if stats["randle_penalty"] > 0: st.warning(f"⚠️ 糖質×脂質 ペナルティ (-{stats['randle_penalty']})")
                if stats["diet_bonus"] > 0: st.success(f"✨ 減量シナジー ボーナス (+{stats['diet_bonus']})")
            
            st.markdown("---")
            tweet_text = f"【Jiro Order Optimizer】\n私の最適化プラン: {final_call}\n💰 {int(stats['price'])}円 | 🔥 {int(stats['cal'])}kcal | 🧂 {stats['sodium']:.1f}g\n満足度スコア: {stats['final_score']:.1f}\n#JiroOrderOptimizer"
            share_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(tweet_text)}"
            st.link_button("X (Twitter) でオーダーをポスト", share_url)