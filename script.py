import streamlit as st
import pandas as pd

# Function to calculate scores
def calculate_scores(data):
    results = []

    for user_id, group in data.groupby("user_id"):
        # Scoring 1: Less interacted videos - Only for videos watched more than 90%
        # Prevent division by zero if duration is zero
        group["completion_percentage"] = group.apply(
            lambda row: (row["actual_hours"] * row["speed"]) / row["duration"] * 100 if row["duration"] != 0 else 0,
            axis=1
        )
        filtered_group = group[group["completion_percentage"] >= 90]

        less_interacted_videos = filtered_group[(filtered_group["_pause"] + filtered_group["_seek"]) < 3]  # Corrected to refer to _pause and _seek columns
        interaction_percentage = len(less_interacted_videos) / len(filtered_group) * 100 if len(filtered_group) > 0 else 0
        interaction_score = 10 if interaction_percentage >= 80 else 8 if interaction_percentage >= 50 else 5

        # Scoring 2: Videos watched offline
        offline_videos = group[group["_pb_type"] == 2]
        offline_percentage = len(offline_videos) / len(group) * 100 if len(group) > 0 else 0
        offline_score = 10 if offline_percentage >= 90 else 9 if offline_percentage >= 50 else 5

        # Scoring 3: Total sessions per lesson_id
        session_score = 10
        group["start_time"] = pd.to_datetime(group["start_time"], errors='coerce')  # Convert start_time to datetime
        group["end_time"] = pd.to_datetime(group["end_time"], errors='coerce')      # Convert end_time to datetime

        for lesson_id, lesson_group in group.groupby("lesson_id"):
            lesson_group = lesson_group.sort_values("start_time")
            end_times = lesson_group["end_time"].shift(1)
            start_times = lesson_group["start_time"]
            session_gaps = start_times - end_times

            # Filter out non-valid session gaps (NaT)
            session_gaps = session_gaps.dropna()

            session_count = (session_gaps > pd.Timedelta(minutes=1)).sum() + 1  # Count sessions (threshold 1 minute)
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
    # Load the dataset
    data = pd.read_csv(uploaded_file)

    # Clean column names to strip any extra spaces
    data.columns = data.columns.str.strip()

    # Print column names to debug
    st.write("Dataset Columns:", data.columns.tolist())
    
    # Show the first few rows of the data for further debugging
    st.write("Preview of the Data (First 5 Rows):")
    st.write(data.head())
    
    # Ensure necessary columns are present
    required_columns = ["user_id", "_pause", "_seek", "_pb_type", "actual_hours", "speed", "duration", "start_time", "end_time", "lesson_id"]
    if all(col in data.columns for col in required_columns):
        # Calculate Scores
        scores = calculate_scores(data)
        st.write("Calculated Scores:")
        st.dataframe(scores)

        # Download Button
        csv = scores.to_csv(index=False)
        st.download_button("Download Scored Data", csv, "scores.csv", "text/csv")
    else:
        missing_cols = [col for col in required_columns if col not in data.columns]
        st.error(f"Missing columns. Ensure the dataset includes: {', '.join(missing_cols)}")
