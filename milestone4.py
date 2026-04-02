# ============================
# ReviewSense – Milestone 4 (Enhanced & Fixed Final)
# Interactive Customer Feedback Dashboard with Login System
# ============================
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from wordcloud import WordCloud
import numpy as np
import shelve
import hashlib
import os

# ─────────────────────────────────────────────
# Page configuration (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ReviewSense Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Shared CSS  (login + dashboard styles)
# ─────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=Space+Mono:wght@400;700&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Sora', sans-serif;
    }

    /* ── Auth card ── */
    .auth-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh;
    }
    .auth-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 20px;
        padding: 3rem 2.5rem;
        max-width: 440px;
        margin: 4rem auto;
        box-shadow: 0 25px 60px rgba(0,0,0,0.5);
    }
    .auth-logo {
        font-family: 'Space Mono', monospace;
        font-size: 2.2rem;
        font-weight: 700;
        color: #38bdf8;
        text-align: center;
        letter-spacing: -1px;
        margin-bottom: 0.25rem;
    }
    .auth-tagline {
        text-align: center;
        color: #64748b;
        font-size: 0.85rem;
        margin-bottom: 2rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .auth-divider {
        border: none;
        border-top: 1px solid #334155;
        margin: 1.5rem 0;
    }

    /* ── Dashboard header ── */
    .main-header {
        font-family: 'Space Mono', monospace;
        font-size: 2.4rem;
        color: #38bdf8;
        text-align: center;
        margin-bottom: 2rem;
        letter-spacing: -1px;
    }

    /* ── Metric cards ── */
    .metric-card {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 1px solid #334155;
        padding: 1.5rem;
        border-radius: 14px;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }

    /* ── Tab styling ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #1e293b;
        border-radius: 8px;
        border: 1px solid #334155;
        color: #94a3b8;
        font-family: 'Space Mono', monospace;
        padding: 0.5rem 1.5rem;
    }
    .stTabs [aria-selected="true"] {
        background: #38bdf8 !important;
        color: #0f172a !important;
        border-color: #38bdf8 !important;
    }

    /* ── Streamlit input overrides ── */
    div[data-testid="stTextInput"] input {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 2px rgba(56,189,248,0.2) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9, #38bdf8) !important;
        color: #0f172a !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.4rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(56,189,248,0.35) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# Utility: password hashing & user store
# ─────────────────────────────────────────────
DB_PATH = "reviewsense_users"   # shelve file prefix


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_users() -> dict:
    with shelve.open(DB_PATH) as db:
        return dict(db.get("users", {}))


def _save_users(users: dict):
    with shelve.open(DB_PATH) as db:
        db["users"] = users


def register_user(username: str, password: str, email: str) -> tuple[bool, str]:
    username = username.strip().lower()
    if not username or not password or not email:
        return False, "All fields are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    users = _get_users()
    if username in users:
        return False, "Username already exists. Please choose another."
    users[username] = {"password": _hash(password), "email": email.strip()}
    _save_users(users)
    return True, "Account created successfully! You can now sign in."


def authenticate_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip().lower()
    users = _get_users()
    if username not in users:
        return False, "Username not found."
    if users[username]["password"] != _hash(password):
        return False, "Incorrect password."
    return True, "Login successful!"


# ─────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "auth_tab" not in st.session_state:
    st.session_state.auth_tab = "signin"   # "signin" | "signup"


# ─────────────────────────────────────────────
# ██████  AUTH PAGES
# ─────────────────────────────────────────────
def show_auth_page():
    st.markdown(
        """
        <div class="auth-card">
            <div class="auth-logo">📊 ReviewSense</div>
            <div class="auth-tagline">Customer Feedback Intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # We use real Streamlit tabs so they actually work
    tab_signin, tab_signup = st.tabs(["🔑  Sign In", "✨  Create Account"])

    # ── Sign In ────────────────────────────────
    with tab_signin:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container():
            si_user = st.text_input("Username", key="si_user", placeholder="your_username")
            si_pass = st.text_input("Password", key="si_pass", type="password", placeholder="••••••••")

            if st.button("Sign In →", use_container_width=True, key="btn_signin"):
                if si_user and si_pass:
                    ok, msg = authenticate_user(si_user, si_pass)
                    if ok:
                        st.session_state.logged_in = True
                        st.session_state.username = si_user.strip().lower()
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.warning("Please enter both username and password.")

    # ── Sign Up ────────────────────────────────
    with tab_signup:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container():
            su_user  = st.text_input("Username",  key="su_user",  placeholder="choose_a_username")
            su_email = st.text_input("Email",     key="su_email", placeholder="you@example.com")
            su_pass  = st.text_input("Password",  key="su_pass",  type="password", placeholder="min. 6 characters")
            su_pass2 = st.text_input("Confirm Password", key="su_pass2", type="password", placeholder="repeat password")

            if st.button("Create Account →", use_container_width=True, key="btn_signup"):
                if su_pass != su_pass2:
                    st.error("❌ Passwords do not match.")
                else:
                    ok, msg = register_user(su_user, su_pass, su_email)
                    if ok:
                        st.success(f"✅ {msg}")
                        st.info("Switch to the **Sign In** tab to log in.")
                    else:
                        st.error(f"❌ {msg}")


# ─────────────────────────────────────────────
# ██████  DATA LOADERS
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("./Milestone2_Sentiment_Analysis.csv")
    df["sentiment"] = df["sentiment"].str.lower().str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@st.cache_data
def load_keywords():
    try:
        keywords_df = pd.read_csv("Milestone3_Keyword_Insights.csv")
        if "keyword" in keywords_df.columns and "frequency" in keywords_df.columns:
            return keywords_df
    except Exception:
        pass

    try:
        with open("Milestone3_Keyword_Insights.csv", "r", encoding="utf-8") as f:
            content = f.read()
        if "=== KEYWORD FREQUENCY ===" in content:
            keyword_part = content.split("=== KEYWORD FREQUENCY===")[1].split(
                "=== PRODUCT SENTIMENT SUMMARY ==="
            )[0]
            keyword_part = keyword_part.strip().splitlines()
            if len(keyword_part) > 1:
                return pd.read_csv(pd.StringIO("\n".join(keyword_part)))
    except Exception:
        pass

    return pd.DataFrame()


# ─────────────────────────────────────────────
# ██████  DASHBOARD
# ─────────────────────────────────────────────
def show_dashboard():
    df = load_data()
    keywords_df = load_keywords()

    sentiment_options  = ["positive", "negative", "neutral"]
    sentiment_display  = {"positive": "Positive", "negative": "Negative", "neutral": "Neutral"}

    # ── Sidebar ────────────────────────────────
    with st.sidebar:
        st.markdown(
            f"<div style='background:#1e293b;border:1px solid #334155;border-radius:12px;"
            f"padding:1rem;margin-bottom:1rem;text-align:center;'>"
            f"<span style='color:#38bdf8;font-family:Space Mono,monospace;font-size:0.9rem;'>"
            f"👤 {st.session_state.username}</span></div>",
            unsafe_allow_html=True,
        )
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username  = ""
            st.rerun()

        st.markdown("---")
        st.header("🔍 Filters")

        sentiment_filter_display = st.multiselect(
            "Select Sentiment",
            options=[sentiment_display[s] for s in sentiment_options],
            default=[sentiment_display[s] for s in sentiment_options],
        )
        sentiment_filter = [k for k, v in sentiment_display.items() if v in sentiment_filter_display]

        product_filter = st.multiselect(
            "Select Product",
            options=sorted(df["product"].unique()),
            default=sorted(df["product"].unique()),
        )

        st.subheader("📅 Date Range")
        default_start = df["date"].min().date() if pd.notna(df["date"].min()) else datetime(2025, 1, 1).date()
        default_end   = df["date"].max().date() if pd.notna(df["date"].max()) else datetime(2025, 12, 31).date()
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start", value=default_start)
        end_date   = col2.date_input("End",   value=default_end)

    # ── Apply filters ──────────────────────────
    filtered_df = df[
        (df["sentiment"].isin(sentiment_filter))
        & (df["product"].isin(product_filter))
        & (df["date"] >= pd.to_datetime(start_date))
        & (df["date"] <= pd.to_datetime(end_date))
    ].copy()

    # ── Header ─────────────────────────────────
    st.markdown(
        '<h1 class="main-header">📊 ReviewSense – Customer Feedback Dashboard</h1>',
        unsafe_allow_html=True,
    )

    # ── KPI Metrics ────────────────────────────
    total_reviews = len(filtered_df)
    pos_count = len(filtered_df[filtered_df["sentiment"] == "positive"])
    neg_count = len(filtered_df[filtered_df["sentiment"] == "negative"])
    neu_count = len(filtered_df[filtered_df["sentiment"] == "neutral"])
    pos_pct = (pos_count / total_reviews * 100) if total_reviews > 0 else 0
    neg_pct = (neg_count / total_reviews * 100) if total_reviews > 0 else 0
    neu_pct = (neu_count / total_reviews * 100) if total_reviews > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Reviews", total_reviews)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Positive", f"{pos_pct:.1f}%", delta=f"{pos_count} reviews")
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Negative", f"{neg_pct:.1f}%", delta=f"{neg_count} reviews")
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Neutral", f"{neu_pct:.1f}%", delta=f"{neu_count} reviews")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Sentiment Distribution ─────────────────
    st.subheader("😊 Sentiment Distribution")
    if not filtered_df.empty:
        fig1, ax1 = plt.subplots(figsize=(8, 5))
        counts = filtered_df["sentiment"].value_counts()
        colors = {"positive": "#4CAF50", "negative": "#F44336", "neutral": "#9E9E9E"}
        bars = ax1.bar(
            [sentiment_display.get(s, s.title()) for s in counts.index],
            counts.values,
            color=[colors.get(s, "gray") for s in counts.index],
        )
        ax1.set_xlabel("Sentiment")
        ax1.set_ylabel("Number of Reviews")
        ax1.set_title("Overall Sentiment Breakdown")
        for bar in bars:
            yval = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, yval + 10, int(yval), ha="center", va="bottom")
        st.pyplot(fig1)
    else:
        st.info("No data matches the selected filters.")

    # ── Product Sentiment ──────────────────────
    st.subheader("📱 Product-wise Sentiment")
    if not filtered_df.empty:
        product_sent = (
            filtered_df.groupby("product")["sentiment"].value_counts().unstack(fill_value=0)
        )
        for col in sentiment_options:
            if col not in product_sent.columns:
                product_sent[col] = 0
        product_sent["Total"] = product_sent.sum(axis=1)
        product_sent["Positive %"] = (
            product_sent.get("positive", 0) / product_sent["Total"] * 100
        ).round(1)
        product_sent = product_sent.sort_values("Positive %", ascending=False)

        display_cols = [sentiment_display[s] for s in sentiment_options]
        product_sent_disp = product_sent.copy()
        product_sent_disp.rename(columns=sentiment_display, inplace=True)
        st.dataframe(
            product_sent_disp[display_cols + ["Total", "Positive %"]].style.format(precision=1),
            use_container_width=True,
        )

        fig_hm, ax_hm = plt.subplots(figsize=(10, 6))
        sns.heatmap(product_sent[sentiment_options], annot=True, fmt="d", cmap="RdYlGn", ax=ax_hm)
        ax_hm.set_title("Product Sentiment Heatmap")
        st.pyplot(fig_hm)

    # ── Trend Over Time ────────────────────────
    st.subheader("📈 Sentiment Trends Over Time")
    if not filtered_df.empty:
        filtered_df["month"] = filtered_df["date"].dt.to_period("M")
        trend = filtered_df.groupby(["month", "sentiment"]).size().unstack(fill_value=0)
        fig_trend, ax_trend = plt.subplots(figsize=(12, 6))
        for col in trend.columns:
            ax_trend.plot(trend.index.astype(str), trend[col], marker="o", linewidth=2, label=col)
        ax_trend.set_xlabel("Month")
        ax_trend.set_ylabel("Number of Reviews")
        ax_trend.set_title("Monthly Sentiment Trend")
        ax_trend.legend()
        ax_trend.tick_params(axis="x", rotation=45)
        plt.tight_layout()
        st.pyplot(fig_trend)
    else:
        st.info("No date-based data available after filtering.")

    # ── Keywords & Word Cloud ──────────────────
    st.subheader("🔑 Top Keywords & Word Cloud")
    if not keywords_df.empty:
        top10 = keywords_df.head(15)
        colA, colB = st.columns([3, 2])
        with colA:
            fig_bar, ax_bar = plt.subplots(figsize=(10, 6))
            ax_bar.barh(top10["keyword"], top10["frequency"], color="skyblue")
            ax_bar.set_xlabel("Frequency")
            ax_bar.set_title("Top Keywords")
            ax_bar.invert_yaxis()
            st.pyplot(fig_bar)
        with colB:
            if len(top10) > 0:
                word_freq = dict(zip(keywords_df["keyword"], keywords_df["frequency"]))
                wc = WordCloud(width=400, height=400, background_color="white", min_font_size=10).generate_from_frequencies(word_freq)
                fig_wc, ax_wc = plt.subplots(figsize=(6, 6))
                ax_wc.imshow(wc, interpolation="bilinear")
                ax_wc.axis("off")
                st.pyplot(fig_wc)

    # ── Confidence Score ───────────────────────
    st.subheader("📊 Confidence Score Distribution")
    if not filtered_df.empty:
        fig_hist, ax_hist = plt.subplots(figsize=(10, 5))
        ax_hist.hist(filtered_df["confidence_score"], bins=25, color="cornflowerblue", edgecolor="black", alpha=0.7)
        ax_hist.set_xlabel("Confidence Score (–1 to +1)")
        ax_hist.set_ylabel("Count")
        ax_hist.set_title("Sentiment Confidence Distribution")
        st.pyplot(fig_hist)

    # ── Data Preview & Export ──────────────────
    with st.expander("📋 Preview Filtered Data (first 15 rows)"):
        st.dataframe(filtered_df.head(15), use_container_width=True)

    st.subheader("💾 Export Options")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            "⬇️ Download Filtered Reviews",
            filtered_df.to_csv(index=False).encode("utf-8"),
            "ReviewSense_Filtered_Reviews.csv",
            "text/csv",
            use_container_width=True,
        )
    with col_dl2:
        if not keywords_df.empty:
            st.download_button(
                "⬇️ Download Keyword List",
                keywords_df.to_csv(index=False).encode("utf-8"),
                "ReviewSense_Keywords.csv",
                "text/csv",
                use_container_width=True,
            )

    st.success("✅ Dashboard ready! Use the sidebar to explore different views.")


# ─────────────────────────────────────────────
# ██████  ROUTER
# ─────────────────────────────────────────────
if st.session_state.logged_in:
    show_dashboard()
else:
    show_auth_page()