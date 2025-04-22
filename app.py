import streamlit as st
import os
import re
import time
from docx import Document
from PyPDF2 import PdfReader
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag

# Download NLTK data (only runs once)
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

# Set up the app
st.set_page_config(page_title="AI Resume Parser", page_icon="📄", layout="wide")

# App title and description
st.title("📄 AI Resume Ranking Assistant")
st.markdown("""
Upload job description and candidate resumes to automatically rank candidates based on their qualifications.
""")

# Create directories if they don't exist
os.makedirs("uploads/resumes", exist_ok=True)
os.makedirs("uploads/job_descriptions", exist_ok=True)

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Files")
    jd_file = st.file_uploader("Upload Job Description (TXT or DOCX)", type=["txt", "docx"])
    resume_files = st.file_uploader("Upload Resumes (PDF or DOCX)", type=["pdf", "docx"], accept_multiple_files=True)
    use_sample = st.checkbox("Use sample data for demo")
    
    if st.button("Process Files"):
        if (jd_file or use_sample) and (resume_files or use_sample):
            with st.spinner("Analyzing candidates..."):
                time.sleep(2)
                st.session_state.processed = True
        else:
            st.warning("Please upload both job description and resumes")

def parse_job_description(text):
    sentences = sent_tokenize(text)
    skills = []
    experience = 0
    
    # Extract skills
    skill_keywords = ["knowledge", "experience with", "skills in", "familiarity with"]
    for sent in sentences:
        for keyword in skill_keywords:
            if keyword in sent.lower():
                tokens = word_tokenize(sent)
                tagged = pos_tag(tokens)
                skills.extend([word.lower() for word, pos in tagged 
                             if pos in ['NN', 'NNS'] and len(word) > 2])
    
    # Extract experience
    for sent in sentences:
        if "experience" in sent.lower() and "year" in sent.lower():
            try:
                experience = float(''.join(c for c in sent if c.isdigit() or c == '.'))
            except:
                pass
    
    return {
        "required_skills": list(set(skills)),
        "experience_required": experience
    }

def parse_resume(file_path):
    try:
        if file_path.lower().endswith('.pdf'):
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                content = ""
                for page in reader.pages:
                    content += page.extract_text() or ""
        elif file_path.lower().endswith('.docx'):
            doc = Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs if para.text])
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

        resume_data = {
            "name": os.path.basename(file_path).split('.')[0].replace('_', ' '),
            "email": "",
            "skills": [],
            "experience": 0,
            "education": [],
            "file_name": os.path.basename(file_path)
        }

        # Name extraction
        name_match = re.search(r'#\s*(.+)$', content, re.MULTILINE) or \
                    re.search(r'^([A-Z][a-z]+ [A-Z][a-z]+)', content, re.MULTILINE)
        if name_match:
            resume_data["name"] = name_match.group(1).strip()

        # Email extraction
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', content)
        if email_match:
            resume_data["email"] = email_match.group(0).lower()

        # Skills extraction
        skills_match = re.search(r'Skills:\s*(.+?)(?:\n\n|$)', content, re.IGNORECASE | re.DOTALL)
        if skills_match:
            skills = [s.strip().lower() for s in re.split(r'[,;]', skills_match.group(1)) if s.strip()]
            resume_data["skills"] = skills

        # Experience extraction
        exp_match = re.search(r'Experience:\s*([\d\.]+)', content, re.IGNORECASE)
        if exp_match:
            try:
                resume_data["experience"] = float(exp_match.group(1))
            except ValueError:
                pass

        # Education extraction
        edu_match = re.search(r'Education:\s*(.+?)(?:\n\n|$)', content, re.IGNORECASE | re.DOTALL)
        if edu_match:
            resume_data["education"] = [edu_match.group(1).strip()]

        return resume_data

    except Exception as e:
        st.error(f"Error parsing {file_path}: {str(e)}")
        return None
def calculate_score(resume_data, jd_requirements):
    score = 0
    resume_skills = set(resume_data["skills"])
    required_skills = set(jd_requirements["required_skills"])
    matched_skills = resume_skills.intersection(required_skills)
    
    # Skill matching (50 points)
    skill_score = 50 * (len(matched_skills) / len(required_skills)) if required_skills else 0
    score += skill_score
    
    # Experience matching (30 points)
    if jd_requirements["experience_required"] > 0:
        exp_ratio = resume_data["experience"] / jd_requirements["experience_required"]
        score += 30 * min(exp_ratio, 1.0)
    else:
        score += 15
    
    # Education (20 points)
    if any(edu.lower() in ['bachelor', 'master', 'phd'] for edu in resume_data["education"]):
        score += 20
    
    return min(100, round(score, 1)), matched_skills

if "processed" in st.session_state:
    st.header("Results")
    
    if use_sample:
        jd_text = """Looking for a Python developer with:
        - 3+ years experience with Django/Flask
        - Knowledge of machine learning
        - Bachelor's degree in Computer Science
        - AWS experience preferred"""
        
        sample_resumes = [
            {"name": "John Smith", "skills": ["python", "django", "aws"], 
             "experience": 4, "education": ["Bachelor in Computer Science"], "email": "john@example.com"},
            {"name": "Jane Doe", "skills": ["python", "machine learning"], 
             "experience": 2, "education": ["Master in Data Science"], "email": "jane@example.com"},
            {"name": "Alex Johnson", "skills": ["java", "spring"], 
             "experience": 5, "education": ["Bachelor in Software Engineering"], "email": "alex@example.com"}
        ]
    else:
        if jd_file:
            jd_path = os.path.join("uploads/job_descriptions", jd_file.name)
            with open(jd_path, "wb") as f:
                f.write(jd_file.getbuffer())
            
            if jd_file.type == "text/plain":
                with open(jd_path, "r") as f:
                    jd_text = f.read()
            else:
                doc = Document(jd_path)
                jd_text = "\n".join([para.text for para in doc.paragraphs])
        
        sample_resumes = []
        for resume_file in resume_files:
            resume_path = os.path.join("uploads/resumes", resume_file.name)
            with open(resume_path, "wb") as f:
                f.write(resume_file.getbuffer())
            parsed = parse_resume(resume_path)
            if parsed:
                sample_resumes.append(parsed)
    
    jd_requirements = parse_job_description(jd_text)
    
    with st.expander("Job Requirements"):
        st.write(jd_text)
        st.subheader("Extracted Requirements")
        st.write(f"**Required Skills:** {', '.join(jd_requirements['required_skills'])}")
        st.write(f"**Years of Experience Required:** {jd_requirements['experience_required']}")
    
    ranked_candidates = []
    for resume in sample_resumes:
        score, matched_skills = calculate_score(resume, jd_requirements)
        ranked_candidates.append({
            **resume,
            "score": score,
            "matched_skills": matched_skills
        })
    
    ranked_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    st.subheader("Ranked Candidates")
    for i, candidate in enumerate(ranked_candidates, 1):
        with st.container():
            cols = st.columns([1, 4, 2])
            cols[0].metric(f"Rank #{i}", f"{candidate['score']}/100")
            with cols[1]:
                st.subheader(candidate["name"])
                st.write(f"**Experience:** {candidate['experience']} years")
                st.write(f"**Education:** {', '.join(candidate['education'])}")
                st.write(f"**Matched Skills:** {', '.join(candidate['matched_skills'])}")
            with cols[2]:
                st.progress(candidate["score"] / 100)
                st.caption("Overall match score")
        st.divider()
    
    if ranked_candidates:
        csv_header = "Name,Email,Score,Matched Skills,Experience,Education\n"
        csv_rows = []
        for candidate in ranked_candidates:
            row = [
                candidate['name'],
                candidate['email'],
                str(candidate['score']),
                ';'.join(candidate['matched_skills']),
                str(candidate['experience']),
                ';'.join(candidate['education'])
            ]
            csv_rows.append(','.join(row))
        
        st.download_button(
            label="Download Results as CSV",
            data=csv_header + '\n'.join(csv_rows),
            file_name="candidate_rankings.csv",
            mime="text/csv"
        )
    else:
        st.warning("No candidate data available to download")
else:
    st.info("Please upload files and click 'Process Files' in the sidebar")