import streamlit as st
import pandas as pd

# Function to calculate scores
def calculate_scores(data):
    results = []

    for user_id, group in data.groupby("user_id"):
        # Scoring 1: Less interacted videos
        less_interacted_videos = group[(group["_pause"] + group["_seek"]) < 3]  # Corrected to refer to _pause and _seek columns
        interaction_percentage = len(less_interacted_videos) / len(group) * 100
        interaction_score = 10 if interaction_percentage >= 80 else 8 if interaction_percentage >= 50 else 5

        # Scoring 2: Videos watched offline
        offline_videos = group[group["_pb_type"] == 2]
        offline_percentage = len(offline_videos) / len(group) * 100
        offline_score = 10 if offline_percentage >= 90 else 9 if offline_percentage >= 50 else 5

        # Scoring 3: Total sessions per lesson_id
        session_score = 10
        for lesson_id, lesson_group in group.groupby("lesson_id"):
            lesson_group = lesson_group.sort_values("start_time")
            end_times = lesson_group["end_time"].shift(1)
            start_times = lesson_group["start_time"]
            session_gaps = start_times - end_times
            session_count = (session_gaps > 60 * 1000).sum() + 1  # Count sessions (threshold 1 minute in ms)
            if session_count > 5:
                session_score -= 1  # Reduce score for excessive sessions

        # Append results
        total_score = (interaction_score + offline_score + session_score) / 3
        results.append({
            "user_id": user_id,
            "interaction_score": interaction_score,
            "offline_score": offline_score,
            "session_score": session_score,
            "total_score": total_score
        })

    return pd.DataFrame(results)

# Streamlit App
st.title("User Video Scoring System")

uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

if uploaded_file:
    data = pd.read_csv(uploaded_file)
    st.write("Uploaded Data:")
    st.dataframe(data)
    
    # Debugging column names
    st.write("Dataset Columns:", data.columns.tolist())
    
    # Clean column names
    data.columns = data.columns.str.strip()
    
    # Ensure necessary columns are present
    required_columns = ["user_id", "_pause", "_seek", "_pb_type", "start_time", "end_time", "lesson_id"]
    if all(col in data.columns for col in required_columns):
        # Calculate Scores
        scores = calculate_scores(data)
        st.write("Calculated Scores:")
        st.dataframe(scores)

        # Download Button
        csv = scores.to_csv(index=False)
        st.download_button("Download Scored Data", csv, "scores.csv", "text/csv")
    else:
        st.error(f"Missing columns. Ensure the dataset includes: {', '.join(required_columns)}")
