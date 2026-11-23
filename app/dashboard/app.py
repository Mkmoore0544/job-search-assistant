import os
from datetime import datetime

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AI Job Search Assistant", page_icon="💼", layout="wide")
st.title("AI Job Search Assistant")

pages = [
    "Dashboard", "Job Explorer", "Saved Jobs", "Application Tracker",
    "Resume and Profile", "Search Preferences", "AI Assistant",
    "Search History", "Company Watchlist", "Website Search", "Settings",
]
page = st.sidebar.radio("Navigation", pages)


def get(path: str, **kwargs: object) -> httpx.Response:
    return httpx.get(f"{API_URL}{path}", timeout=15, **kwargs)


def put(path: str, json: dict[str, object]) -> httpx.Response:
    return httpx.put(f"{API_URL}{path}", json=json, timeout=15)


if page == "Dashboard":
    try:
        metrics = get("/api/dashboard").json()
        columns = st.columns(5)
        labels = [
            ("Total jobs", metrics["total_jobs"]),
            ("New today", metrics["new_today"]),
            ("High matches", metrics["high_matches"]),
            ("Saved jobs", metrics["saved_jobs"]),
            ("Applications", metrics["applications"]),
        ]
        for column, (label, value) in zip(columns, labels):
            column.metric(label, value)
        st.subheader("Latest opportunities")
        st.dataframe(get("/api/jobs?limit=20").json(), use_container_width=True)
    except httpx.HTTPError:
        st.error("API is unavailable. Start the FastAPI service first.")

elif page == "Job Explorer":
    try:
        jobs = get("/api/jobs?limit=200").json()
        title = st.text_input("Job title")
        minimum = st.slider("Minimum match score", 0, 100, 0)
        haystack_fields = ("title", "employer", "location", "description")
        filtered = [
            job for job in jobs
            if (not title or any(title.lower() in str(job.get(field, "")).lower() for field in haystack_fields))
            and (job["score"] or 0) >= minimum
        ]
        st.dataframe(filtered, use_container_width=True)
        selected = st.selectbox("View details", [""] + [f"{job['title']} — {job['employer']}" for job in filtered])
        if selected:
            job = filtered[[f"{item['title']} — {item['employer']}" for item in filtered].index(selected)]
            st.markdown(f"### {job['title']} at {job['employer']}")
            st.write(job["location"])
            st.write(job["description"])
            st.link_button("Open original listing", job["url"])
            if st.button("Save job"):
                get_result = httpx.post(f"{API_URL}/api/jobs/{job['id']}/save", timeout=15)
                st.success("Saved") if get_result.status_code == 200 else st.error("Could not save")
            if st.button("Dismiss job"):
                httpx.post(f"{API_URL}/api/jobs/{job['id']}/dismiss", timeout=15)
                st.success("Dismissed")
    except httpx.HTTPError:
        st.error("API is unavailable.")

elif page == "Saved Jobs":
    st.info("Saved jobs are included in the Job Explorer. Use the save action to bookmark listings.")

elif page == "Application Tracker":
    st.subheader("Applications")
    st.info("Application records are available through the API. Mark saved jobs applied from the Job Explorer.")

elif page == "Resume and Profile":
    st.subheader("Resume upload")
    uploaded = st.file_uploader("Upload PDF or DOCX resume", type=["pdf", "docx"])
    if uploaded:
        if st.button("Upload resume"):
            response = httpx.post(
                f"{API_URL}/api/resume",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                timeout=30,
            )
            st.success("Resume uploaded") if response.status_code == 200 else st.error(response.text)
    st.subheader("Profile")
    try:
        profile = get("/api/profile").json()
    except httpx.HTTPError:
        profile = {}
    name = st.text_input("Name", profile.get("name", ""))
    education = st.text_area("Education", profile.get("education", "Bachelor of Science in Software Engineering"))
    skills = st.text_area("Skills", profile.get("skills", "Python, JavaScript, React, Node.js, Express, SQL, MySQL, REST APIs, Git, AWS, Docker"))
    experience = st.text_area("Professional experience", profile.get("experience", ""))
    projects = st.text_area("Projects", profile.get("projects", ""))
    if st.button("Save profile"):
        result = put("/api/profile", {"name": name, "education": education, "skills": skills, "experience": experience, "projects": projects})
        st.success("Profile saved") if result.status_code == 200 else st.error("Could not save profile")

elif page == "Search Preferences":
    try:
        preference = get("/api/preferences").json()
    except httpx.HTTPError:
        preference = {}
    keywords = st.text_area("Job title keywords", preference.get("keywords", "Junior Software Developer, Software Engineer I, Backend Developer, Junior Python Developer"))
    locations = st.text_area("Locations", preference.get("locations", "Remote in United States, Texarkana TX"))
    minimum_salary = st.number_input("Minimum annual salary", 0, 500000, int(preference.get("min_salary", 60000)))
    interval = st.number_input("Search interval (hours)", 0.25, 168.0, float(preference.get("interval_hours", 4)))
    sources = st.multiselect(
        "Job sources",
        ["adzuna", "usajobs", "greenhouse", "lever", "ashby", "remotive"],
        preference.get("enabled_sources", "adzuna,remotive,greenhouse,lever,ashby").split(","),
    )
    if st.button("Save preferences"):
        result = put("/api/preferences", {
            "keywords": keywords,
            "locations": locations,
            "min_salary": minimum_salary,
            "interval_hours": interval,
            "enabled_sources": ",".join(sources),
        })
        st.success("Preferences saved") if result.status_code == 200 else st.error("Could not save preferences")
    st.subheader("Search arbitrary keywords")
    live_keyword = st.text_input("Search keywords", "software")
    live_location = st.text_input("Search location", "United States")
    if st.button("Search now for keywords"):
        response = httpx.post(
            f"{API_URL}/api/search/keywords",
            params={"keywords": live_keyword, "location": live_location},
            timeout=180,
        )
        if response.status_code == 200:
            st.success(response.json())
        else:
            st.error(response.text)
    if st.button("Run search now"):
        response = httpx.post(f"{API_URL}/api/search", timeout=120)
        if response.status_code == 200:
            st.success(response.json())
        else:
            st.error("Search failed")

elif page == "AI Assistant":
    st.subheader("Job Search AI Assistant")
    question = st.text_input("Ask about jobs or preferences")
    if st.button("Ask") and question:
        jobs = get("/api/jobs?limit=30").json()
        lower = question.lower()
        if "match" in lower or "best" in lower:
            ranked = sorted(jobs, key=lambda item: item["score"] or 0, reverse=True)
            st.write("Highest-matching listings:")
            st.dataframe(ranked[:10], use_container_width=True)
        elif "search" in lower:
            response = httpx.post(f"{API_URL}/api/search", timeout=120)
            st.write(response.json())
        else:
            st.write("I can search, rank matching jobs, and explain the returned listings. Use the Search Preferences page for preference changes.")

elif page == "Search History":
    st.subheader("Scheduled search history")
    try:
        history = get("/api/search-history?limit=50").json()
        st.dataframe(history, use_container_width=True)
    except httpx.HTTPError:
        st.error("API is unavailable.")

elif page == "Company Watchlist":
    st.subheader("Company watchlist")
    try:
        watchlist = get("/api/watchlist").json()
        st.dataframe(watchlist, use_container_width=True)
    except httpx.HTTPError:
        st.error("API is unavailable.")
    st.subheader("Add a company")
    company = st.text_input("Company name")
    career_url = st.text_input("Authorized career-page or ATS board URL")
    if st.button("Add company"):
        if not company.strip():
            st.error("Company name is required.")
        else:
            response = httpx.post(
                f"{API_URL}/api/watchlist",
                json={"company": company, "career_url": career_url},
                timeout=15,
            )
            st.success("Company added") if response.status_code == 200 else st.error(response.text)

elif page == "Website Search":
    st.subheader("One-click website search")
    st.caption("Opens the selected website's normal public job-search page in a new tab.")
    website_keywords = st.text_input("Job keywords", "software")
    website_location = st.text_input("Location", "United States")
    website = st.selectbox(
        "Job website",
        ["Indeed", "LinkedIn", "Glassdoor", "ZipRecruiter", "Dice"],
    )
    if st.button("Open job search"):
        if not website_keywords.strip():
            st.error("Enter keywords.")
        else:
            try:
                result = get(
                    "/api/website-search",
                    params={
                        "site": website,
                        "keywords": website_keywords,
                        "location": website_location,
                    },
                ).json()
                st.link_button(
                    f"Search {website}",
                    result["url"],
                    use_container_width=True,
                )
            except httpx.HTTPError:
                st.error("Could not create the search link.")

elif page == "Settings":
    st.subheader("Search Indeed and LinkedIn")
    manual_keywords = st.text_input("Website search keywords", "Junior Software Developer")
    manual_location = st.text_input("Website search location", "Texarkana, Texas")
    try:
        links = get(
            "/api/manual-search-links",
            params={"keywords": manual_keywords, "location": manual_location},
        ).json()
        st.link_button("Search on Indeed", links["indeed"])
        st.link_button("Search on LinkedIn", links["linkedin"])
        st.caption("These links open your normal browser searches. This app does not scrape or bypass either website.")
    except httpx.HTTPError:
        st.error("Could not create website search links.")

    st.subheader("Email notifications")
    recipient = st.text_input("Notification recipient")
    if st.button("Send test email"):
        response = httpx.post(f"{API_URL}/api/email/test", params={"recipient": recipient}, timeout=30)
        st.success("Test email sent") if response.status_code == 200 else st.error(response.text)
