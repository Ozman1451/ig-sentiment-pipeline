import streamlit as st
import pandas as pd
import plotly.express as px
import subprocess, pathlib, os, time, sys, signal, requests
from apify_client import ApifyClient
from openai import OpenAI

ROOT = pathlib.Path.cwd()
VENV_PYTHON = sys.executable
VENV_VLLM = str(ROOT / ".venv/bin/vllm")

try:
    APIFY_TOKEN = (pathlib.Path.home() / ".config/ig-apify/apify.token").read_text().strip()
except Exception:
    APIFY_TOKEN = "YOUR_APIFY_TOKEN_HERE"

apify = ApifyClient(APIFY_TOKEN)
llm_client = OpenAI(base_url="http://localhost:8000/v1", api_key="local")

st.set_page_config(page_title="Gen Z QSR Radar", layout="wide", page_icon="🍔")
st.title("🍔 IG Pipeline Control Center")

if "posts_df" not in st.session_state: st.session_state.posts_df = None
if "selected_posts" not in st.session_state: st.session_state.selected_posts = []
if "pipeline_run_complete" not in st.session_state: st.session_state.pipeline_run_complete = False
if "exec_summary" not in st.session_state: st.session_state.exec_summary = ""

def kill_vllm_tree(proc=None):
    """Forcefully nuke vLLM parent process and all orphaned CUDA workers."""
    if proc and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
    # Fallback cleanup for any lingering CUDA processes on GPU 0
    subprocess.run("kill -9 $(nvidia-smi --query-compute-apps=pid --format=csv,noheader) 2>/dev/null || true", shell=True)
    subprocess.run(["pkill", "-9", "-f", "vllm"], stderr=subprocess.DEVNULL)

# --- PHASE 1: DISCOVERY ---
st.sidebar.header("1. Target Discovery")
target_url = st.sidebar.text_input("Instagram Brand URL", "https://www.instagram.com/cheeziouspakistan/")
max_posts = st.sidebar.number_input("Recent Posts to Analyze", min_value=1, max_value=20, value=5)

if st.sidebar.button("Fetch Post Metrics"):
    with st.spinner("Scraping profile metadata via Apify..."):
        run_input = {"directUrls": [target_url.strip()], "resultsLimit": max_posts}
        run = apify.actor("apify/instagram-scraper").call(run_input=run_input)
        
        posts_data = []
        for item in apify.dataset(run.default_dataset_id).iterate_items():
            if "url" in item:
                posts_data.append({
                    "Post URL": item.get("url"), "Type": item.get("type", "Image"),
                    "Likes": item.get("likesCount", 0), "Comments": item.get("commentsCount", 0)
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
    
    if st.sidebar.button("🚀 Run Full AI Pipeline (Auto-VRAM)"):
        with st.status("Executing Pipeline...", expanded=True) as status:
            with open(ROOT / "data/raw/selected_posts.txt", "w") as f:
                for url in st.session_state.selected_posts: f.write(f"{url}\n")
            
            st.write(f"Scraping deep comments (limit: {max_comments})...")
            env = os.environ.copy()
            env["MAX_COMMENTS"] = str(max_comments)
            subprocess.run([VENV_PYTHON, "src/collect_comments.py"], env=env, check=True)
            subprocess.run([VENV_PYTHON, "src/clean.py"], check=True)
            subprocess.run([VENV_PYTHON, "src/strict_clean.py"], check=True)
            
            st.write("⚡ Booting vLLM Engine (Allocating GPU 0 VRAM...)")
            vllm_env = os.environ.copy()
            vllm_env["CUDA_VISIBLE_DEVICES"] = "0"
            vllm_cmd = [VENV_VLLM, "serve", "Qwen/Qwen2.5-7B-Instruct", "--port", "8000", "--served-model-name", "m", "--max-model-len", "4096", "--gpu-memory-utilization", "0.85", "--quantization", "fp8", "--enforce-eager"]
            
            # preexec_fn=os.setsid creates a dedicated process group for vLLM and its workers
            vllm_proc = subprocess.Popen(vllm_cmd, env=vllm_env, preexec_fn=os.setsid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            st.write("Waiting for model to load (~30 seconds)...")
            vllm_ready = False
            for _ in range(60):
                try:
                    if requests.get("http://localhost:8000/v1/models").status_code == 200:
                        vllm_ready = True
                        break
                except Exception: time.sleep(2)
            
            if vllm_ready:
                st.write("🧠 Running local AI tagging inference...")
                subprocess.run([VENV_PYTHON, "src/tag.py"], check=True)
                subprocess.run([VENV_PYTHON, "src/aggregate.py"], check=True)
                
                st.write("Generating Executive Summary...")
                summary_text = (ROOT / "reports/qsr_summary.md").read_text()
                prompt = f"You are a Gen Z brand strategist. Analyze this Instagram sentiment report for {target_url}:\n{summary_text}\n\nProvide exactly 3 bullet points analyzing their social presence, highlighting the biggest risk, the biggest strength, and a highly actionable operational recommendation. Be concise."
                try:
                    response = llm_client.chat.completions.create(model="m", messages=[{"role": "user", "content": prompt}], max_tokens=250, temperature=0.3)
                    st.session_state.exec_summary = response.choices[0].message.content
                except Exception as e: st.session_state.exec_summary = f"Summary failed: {e}"
                
                st.write("🛑 Shutting down vLLM Process Tree & Freeing VRAM...")
                kill_vllm_tree(vllm_proc)
            else:
                st.error("vLLM Engine failed to boot!")
                kill_vllm_tree(vllm_proc)
            
            status.update(label="Pipeline Complete! VRAM Freed.", state="complete", expanded=False)
        st.session_state.pipeline_run_complete = True

# --- PHASE 3: DASHBOARD ---
if getattr(st.session_state, "pipeline_run_complete", False):
    st.divider()
    st.header("📊 Final Dashboard & AI Insights")
    st.subheader("🤖 Qwen 2.5 Executive Summary")
    st.info(st.session_state.exec_summary)
    
    final_df = pd.read_csv(ROOT / "reports/final_qsr_data.csv")
    final_df["aspects_str"] = final_df["aspects_str"].fillna("none")
    
    st.sidebar.header("3. Data Filters")
    all_sentiments = final_df["sentiment"].unique().tolist()
    selected_sent = st.sidebar.multiselect("Sentiment", all_sentiments, default=all_sentiments)
    unique_aspects = set([asp.strip() for sublist in final_df['aspects_str'].str.split(',') for asp in sublist])
    selected_aspect = st.sidebar.selectbox("Aspect Focus", ["All"] + sorted(list(unique_aspects)))

    filtered_df = final_df[final_df["sentiment"].isin(selected_sent)]
    if selected_aspect != "All": filtered_df = filtered_df[filtered_df["aspects_str"].str.contains(selected_aspect, na=False)]

    c1, c2, c3, c4 = st.columns(4)
    total = len(filtered_df)
    c1.metric("Total Comments", total)
    c2.metric("Positive Hype", f"{(len(filtered_df[filtered_df['sentiment'] == 'positive'])/total)*100 if total else 0:.1f}%")
    c3.metric("Negative / Mid", f"{(len(filtered_df[filtered_df['sentiment'] == 'negative'])/total)*100 if total else 0:.1f}%")
    c4.metric("Top Emotion", filtered_df["emotion"].mode()[0].title() if not filtered_df.empty else "N/A")

    col1, col2 = st.columns(2)
    with col1: st.plotly_chart(px.pie(filtered_df, names="sentiment", hole=0.4, color="sentiment", color_discrete_map={"positive":"#2ecc71", "negative":"#e74c3c", "neutral":"#95a5a6", "mixed":"#f39c12"}), use_container_width=True)
    with col2: 
        emo_counts = filtered_df["emotion"].value_counts().reset_index(); emo_counts.columns = ["emotion", "count"]
        st.plotly_chart(px.bar(emo_counts, x="emotion", y="count", color="emotion", template="plotly_white"), use_container_width=True)

    st.subheader("Deep Dive: The Comments")
    avail_cols = [c for c in ["text", "sentiment", "emotion", "aspects_str", "intent", "likesCount", "likes"] if c in filtered_df.columns]
    st.dataframe(filtered_df[avail_cols], use_container_width=True, height=400)
