import streamlit as st
import pandas as pd
import plotly.express as px
import subprocess
import pathlib
import os
from apify_client import ApifyClient
from openai import OpenAI

# --- Configuration & Auth ---
ROOT = pathlib.Path.cwd()
try:
    APIFY_TOKEN = (pathlib.Path.home() / ".config/ig-apify/apify.token").read_text().strip()
except Exception:
    APIFY_TOKEN = "YOUR_APIFY_TOKEN_HERE"

apify = ApifyClient(APIFY_TOKEN)
llm_client = OpenAI(base_url="http://localhost:8000/v1", api_key="local")

st.set_page_config(page_title="Gen Z QSR Radar", layout="wide", page_icon="🍔")
st.title("🍔 IG Pipeline Control Center")

# --- Initialize Session State ---
if "posts_df" not in st.session_state:
    st.session_state.posts_df = None
if "selected_posts" not in st.session_state:
    st.session_state.selected_posts = []
if "pipeline_run_complete" not in st.session_state:
    st.session_state.pipeline_run_complete = False

# --- PHASE 1: DISCOVERY ---
st.sidebar.header("1. Target Discovery")
target_url = st.sidebar.text_input("Instagram Brand URL", "https://www.instagram.com/cheeziouspakistan/")
max_posts = st.sidebar.number_input("Recent Posts to Analyze", min_value=1, max_value=20, value=5)

if st.sidebar.button("Fetch Post Metrics"):
    with st.spinner("Scraping profile metadata via Apify..."):
        run_input = {
            "directUrls": [target_url.strip()],
            "resultsLimit": max_posts,
        }
        run = apify.actor("apify/instagram-scraper").call(run_input=run_input)
        
        posts_data = []
        for item in apify.dataset(run.default_dataset_id).iterate_items():
            if "url" in item:
                posts_data.append({
                    "Post URL": item.get("url"),
                    "Type": item.get("type", "Image"),
                    "Likes": item.get("likesCount", 0),
                    "Comments": item.get("commentsCount", 0),
                    "Views/Plays": item.get("videoPlayCount", 0)
                })

        st.session_state.posts_df = pd.DataFrame(posts_data)
        st.session_state.selected_posts = [p["Post URL"] for p in posts_data]
        st.session_state.pipeline_run_complete = False

# --- PHASE 2: REVIEW & EXECUTE ---
if st.session_state.posts_df is not None and not st.session_state.posts_df.empty:
    st.subheader("Post Metrics")
    st.dataframe(st.session_state.posts_df, use_container_width=True)
    
    st.sidebar.header("2. Pipeline Settings")
    max_comments = st.sidebar.number_input("Max Comments per Post", min_value=10, max_value=1000, value=50)
    
    if st.sidebar.button("🚀 Run Full AI Pipeline"):
        with st.status("Executing Pipeline...", expanded=True) as status:
            st.write("Writing target URLs...")
            with open(ROOT / "data/raw/selected_posts.txt", "w") as f:
                for url in st.session_state.selected_posts:
                    f.write(f"{url}\n")
            
            st.write(f"Scraping deep comments (limit: {max_comments} per post)...")
            env = os.environ.copy()
            env["MAX_COMMENTS"] = str(max_comments)
            subprocess.run(["python", "src/collect_comments.py"], env=env)
            
            st.write("Sanitizing and hashing data...")
            subprocess.run(["python", "src/clean.py"])
            subprocess.run(["python", "src/strict_clean.py"])
            
            st.write("Running local vLLM inference (Qwen 2.5)...")
            subprocess.run(["python", "src/tag.py"])
            
            st.write("Aggregating final reports...")
            subprocess.run(["python", "src/aggregate.py"])
            
            status.update(label="Pipeline Complete!", state="complete", expanded=False)
        
        st.session_state.pipeline_run_complete = True

elif st.session_state.posts_df is not None and st.session_state.posts_df.empty:
    st.warning("No posts found. Verify the URL is correct or try running again.")

# --- PHASE 3: DASHBOARD & AI INSIGHTS ---
if getattr(st.session_state, "pipeline_run_complete", False):
    st.divider()
    st.header("📊 Final Dashboard & AI Insights")
    
    # Load Data
    final_df = pd.read_csv(ROOT / "reports/final_qsr_data.csv")
    final_df["aspects_str"] = final_df["aspects_str"].fillna("none")
    
    # 1. Executive Summary
    st.subheader("🤖 Qwen 2.5 Executive Summary")
    with st.spinner("Generating insights..."):
        summary_text = (ROOT / "reports/qsr_summary.md").read_text()
        prompt = f"You are a Gen Z brand strategist. Analyze this Instagram sentiment report for {target_url}:\n{summary_text}\n\nProvide exactly 3 bullet points analyzing their social presence, highlighting the biggest risk, the biggest strength, and a highly actionable operational recommendation based strictly on the data. Be concise, punchy, and use mature business language."
        try:
            response = llm_client.chat.completions.create(
                model="m",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.3
            )
            st.info(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Could not generate summary: Ensure vLLM is running. ({e})")
        
    st.divider()
    
    # 2. Filters
    st.sidebar.header("3. Data Filters")
    all_sentiments = final_df["sentiment"].unique().tolist()
    selected_sent = st.sidebar.multiselect("Sentiment", all_sentiments, default=all_sentiments)
    
    unique_aspects = set([asp.strip() for sublist in final_df['aspects_str'].str.split(',') for asp in sublist])
    selected_aspect = st.sidebar.selectbox("Aspect Focus", ["All"] + sorted(list(unique_aspects)))

    # Apply Filters
    filtered_df = final_df[final_df["sentiment"].isin(selected_sent)]
    if selected_aspect != "All":
        filtered_df = filtered_df[filtered_df["aspects_str"].str.contains(selected_aspect, na=False)]

    # 3. KPI Metrics
    c1, c2, c3, c4 = st.columns(4)
    total_count = len(filtered_df)
    pos_count = len(filtered_df[filtered_df['sentiment'] == 'positive'])
    neg_count = len(filtered_df[filtered_df['sentiment'] == 'negative'])

    c1.metric("Total Comments", total_count)
    c2.metric("Positive Hype", f"{(pos_count/total_count)*100 if total_count else 0:.1f}%")
    c3.metric("Negative / Mid", f"{(neg_count/total_count)*100 if total_count else 0:.1f}%")
    c4.metric("Top Emotion", filtered_df["emotion"].mode()[0].title() if not filtered_df.empty else "N/A")

    # 4. Charts
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

    # 5. Data Explorer
    st.subheader("Deep Dive: The Comments")
    display_cols = ["text", "sentiment", "emotion", "aspects_str", "intent"]
    avail_cols = [c for c in display_cols if c in filtered_df.columns]
    
    if "likesCount" in filtered_df.columns:
        avail_cols.append("likesCount")
    elif "likes" in filtered_df.columns:
        avail_cols.append("likes")
        
    st.dataframe(filtered_df[avail_cols], use_container_width=True, height=400)
