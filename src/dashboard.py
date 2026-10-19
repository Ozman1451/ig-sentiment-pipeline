import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib

# Page Config
st.set_page_config(page_title="Gen Z QSR Radar", layout="wide", page_icon="🍔")
st.title("🍔 Gen Z QSR Sentiment Radar")
st.markdown("Analyzing Instagram comments for Cheezious, Johnny & Jugnu, and Crumble.")

# Load Data
@st.cache_data
def load_data():
    csv_path = pathlib.Path.cwd() / "reports/final_qsr_data.csv"
    df = pd.read_csv(csv_path)
    # Clean up aspects for the filter
    df["aspects_str"] = df["aspects_str"].fillna("none")
    return df

df = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")
all_sentiments = df["sentiment"].unique().tolist()
selected_sent = st.sidebar.multiselect("Sentiment", all_sentiments, default=all_sentiments)

# Extract unique aspects (handling comma-separated strings)
unique_aspects = set([asp.strip() for sublist in df['aspects_str'].str.split(',') for asp in sublist])
selected_aspect = st.sidebar.selectbox("Aspect Focus", ["All"] + sorted(list(unique_aspects)))

# Apply Filters
filtered_df = df[df["sentiment"].isin(selected_sent)]
if selected_aspect != "All":
    filtered_df = filtered_df[filtered_df["aspects_str"].str.contains(selected_aspect, na=False)]

# --- KPI METRICS ---
c1, c2, c3, c4 = st.columns(4)
total_count = len(filtered_df)
pos_count = len(filtered_df[filtered_df['sentiment'] == 'positive'])
neg_count = len(filtered_df[filtered_df['sentiment'] == 'negative'])

c1.metric("Total Comments", total_count)
c2.metric("Positive Hype", f"{(pos_count/total_count)*100 if total_count else 0:.1f}%")
c3.metric("Negative / Mid", f"{(neg_count/total_count)*100 if total_count else 0:.1f}%")
c4.metric("Top Emotion", filtered_df["emotion"].mode()[0].title() if not filtered_df.empty else "N/A")

st.divider()

# --- CHARTS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Sentiment Distribution")
    fig_sent = px.pie(filtered_df, names="sentiment", hole=0.4, 
                      color="sentiment",
                      color_discrete_map={"positive":"#2ecc71", "negative":"#e74c3c", "neutral":"#95a5a6", "mixed":"#f39c12"})
    st.plotly_chart(fig_sent, use_container_width=True)

with col2:
    st.subheader("Gen Z Emotions")
    emo_counts = filtered_df["emotion"].value_counts().reset_index()
    emo_counts.columns = ["emotion", "count"]
    fig_emo = px.bar(emo_counts, x="emotion", y="count", color="emotion", template="plotly_white")
    st.plotly_chart(fig_emo, use_container_width=True)

# --- DATA EXPLORER ---
st.subheader("Deep Dive: The Comments")
st.markdown("Read the actual filtered comments below.")
display_cols = ["text", "sentiment", "emotion", "aspects_str", "intent", "likes"]
st.dataframe(filtered_df[display_cols], use_container_width=True, height=400)
