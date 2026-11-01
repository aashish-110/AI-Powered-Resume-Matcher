import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel
import json
from flask import Flask,render_template,request,redirect,url_for,flash
from werkzeug.utils import secure_filename
from io import BytesIO

load_dotenv(Path(__file__).with_name(".env"))
my_api_key = os.getenv("GROQ_API_KEY")

if not my_api_key:
    raise ValueError("GROQ_API_KEY is not set")

client=Groq(api_key=my_api_key)
app=Flask(__name__)
app.secret_key=os.getenv("FLASK_SECRET_KEY","resume-matcher-key")
app.config["MAX_CONTENT_LENGTH"]=10*1024*1024

model = "openai/gpt-oss-20b"
role = "user"

job_description = """Job Description: Associate AI Engineer
Company: Tech Solutions Nepal
Department: AI & Engineering
Employment Type: Full-Time (Entry-Level)

About the Role:
We are seeking an Associate AI Engineer to design and integrate LLM-powered applications, build robust backend APIs, and work with vector databases for intelligent automation.

Responsibilities:
- Build and deploy AI/LLM features, RAG pipelines, and intelligent workflows.
- Develop clean, high-performance REST APIs using FastAPI or Flask.
- Connect backend services to vector databases (such as Qdrant or ChromaDB) and relational databases (PostgreSQL/SQL).
- Clean, preprocess, and validate data for model pipelines.
- Containerize applications using Docker and collaborate via Git.

Required Qualifications:
- Bachelor's degree in Computer Science, Artificial Intelligence, IT, or a related field.
- Strong proficiency in Python, OOP, and data structures.
- Hands-on experience developing REST APIs in Python (FastAPI or Flask).
- Practical understanding of LLMs, prompt engineering, embeddings, and RAG concepts.
- Familiarity with SQL and relational databases.
- Experience with Git version control.

Preferred Qualifications:
- Experience with LLM orchestration (LangChain, LlamaIndex, or Groq/OpenAI APIs) and Pydantic validation.
- Experience with Docker and containerization.
- Familiarity with vector search and vector stores (Qdrant, Pinecone, or ChromaDB).
- Exposure to cloud basics (AWS/GCP) and CI/CD pipelines.

Experience:
- 0 to 1 year of practical experience (hands-on academic projects, internships, or open-source AI builds accepted).
"""

class jobD(BaseModel):
    role:str
    required_skills:list[str]
    preferred_skills:list[str]
    minimum_experience:float | None
    education_requirement:list[str]
    responsibilities:list[str]

job_schema=jobD.model_json_schema()

system_prompt=f""" You are an Expert HR Assistant. Your Job is to analyze the job description and extract structured information from them.
Return only Valid Json Matching this Schema 
{job_schema}
Important: Not to return the Schena itself
Also don't return the unnecessary fields 
Fill the schema with the actual information extracted from the job description.

If the experince is not mentioned return null.
If information for list is missing return empty list.
Do not Invent Information """

user_prompt=f""" Analyze the following job description:
{job_description}
"""
message_system={
    'role':'system',
    'content':system_prompt
}
message_user={
    'role':'user',
    'content':user_prompt
}
response_format={
    'type':'json_object'
}

messages=[message_system,message_user]
job=None

def get_job():
    global job
    if job is None:
        response=client.chat.completions.create(model=model,messages=messages,response_format=response_format)
        answer=response.choices[0].message.content
        job_data=json.loads(answer)
        job=jobD(**job_data)
    return job

#resume
class match_result(BaseModel):
    candidate_name:str | None
    matching_skills:list[str]
    missing_important_skills:list[str]
    experience_requirement_met:bool | None
    education_requirement_met:bool | None
    score:float
    score_reasons:list[str]
    verdict:str

class experience(BaseModel):
    company:str | None
    role:str | None
    duration:float | None
    description:str | None
    skills_used:list[str]=[]


class Resume(BaseModel):
    name:str | None
    email: str | None
    phone: str | None
    total_exp:float | None
    skills: list[str]=[]
    experience:list[str]=[]
    education:list[str]=[]
    projects: list[str]=[]
    certifications: list[str]=[]

resume_schema=Resume.model_json_schema()

def final_score(job,resume):
    match_schema = match_result.model_json_schema()
    prompt = f"""
    You are an HR recruiter.

    Compare the candidate's resume with the job description.

    JOB DESCRIPTION:
    {job.model_dump_json(indent=2)}

    CANDIDATE RESUME:
    {resume.model_dump_json(indent=2)}
    Return JSON matching this schema:

    {match_schema}

    Give me:

    1. Candidate name
    2. Matching skills
    3. Missing required skills only
    4. Whether experience and education requirements are met
    5. Overall match percentage from 0 to 100
    6. Short reasons explaining why the score is not 100
    7. A short final verdict

    Important:
    - Focus only on the main requirements written by the company, not preferred skills.
    - score_reasons must contain 1 to 4 short and specific points when score is below 100.
    - Mention exact evidence when possible. Example: "6 months experience shown; the role asks for 1 year."
    - Explain missing education, experience depth or required responsibility evidence.
    - Do not repeat long descriptions and do not invent information.
    - If score is 100, score_reasons must be an empty list.

    Keep the response concise and easy to read.
    """
    message={
        "role": "user",
        "content" : prompt
    }
    messages=[message]
    response_format={
        "type": "json_object"
    }
    response = client.chat.completions.create(model=model, messages=messages, response_format=response_format)
    data = json.loads(response.choices[0].message.content)
    result=match_result(**data)
    result.score=max(0,min(100,result.score))
    return result


def parse_resume(resume_text):
    system_prompt = f"""
    You are an expert resume parser.
    Extract information from the resume based on its meaning,
    not only based on exact section headings.
    Different resumes may use different headings.
    For example:
    - Experience
    - Professional Experience
    - Work History
    - Employment
    - Internships
    These may all contain relevant experience.
    Skills may also appear in the skills section, work experience,
    internships or projects.
    Return ONLY valid JSON matching this schema:
    {resume_schema}

    Important rules:
    1. Do not invent information.
    2. If a value is not available, return null.
    3. If a list has no information, return an empty list.
    4. Include internships inside experiences.
    5. Extract skills mentioned across the entire resume.
    """

    user_prompt = f"""
    Parse the following resume:

    {resume_text}
    """
    message_system={
        "role" : "system",
        "content" : system_prompt
    }
    message_user={
        "role" : "user",
        "content" : user_prompt
    }
    messages=[message_system, message_user]
    response_format={
        "type": "json_object"
    }
    response=client.chat.completions.create(model=model, messages=messages, response_format=response_format)
    raw_output = response.choices[0].message.content
    data = json.loads(raw_output)
    resume = Resume(**data)
    return resume


from pypdf import PdfReader
from docx import Document

def read_pdf(file_path):
    reader=PdfReader(file_path)
    text=""
    for page in reader.pages:
        page_text=page.extract_text()
        if page_text:
            text+=page_text+"\n"
    return text

def read_docx(file_path):
    document=Document(file_path)
    text=""
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text+=paragraph.text+"\n"

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells: #column is said to be cell in python
                if cell.text.strip():
                    text+=cell.text+"\n"
    return text

def read_resume(file_path,file_name):
    suffix=Path(file_name).suffix.lower()
    if suffix==".pdf":
        return read_pdf(file_path)
    elif suffix=='.docx':
        return read_docx(file_path)
    else:
        return None


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze',methods=['POST'])
def analyze():
    files=request.files.getlist('resumes')
    files=[file for file in files if file.filename]
    if not files:
        flash('Choose at least one PDF or DOCX resume.','error')
        return redirect(url_for('index'))

    final_result=[]
    for file in files:
        file_name=secure_filename(file.filename)
        if Path(file_name).suffix.lower() not in ('.pdf','.docx'):
            final_result.append({'filename':file_name,'error':'Only PDF and DOCX files are supported.'})
            continue
        try:
            resume_text=read_resume(BytesIO(file.read()),file_name)
            if not resume_text.strip():
                raise ValueError('No readable text was found in this file.')
            parsed_resume=parse_resume(resume_text)
            result=final_score(get_job(),parsed_resume)
            final_result.append({'filename':file_name,'resume':parsed_resume,'match':result})
        except Exception as error:
            final_result.append({'filename':file_name,'error':str(error)})

    return render_template('results.html',results=final_result)

@app.errorhandler(413)
def file_too_large(error):
    flash('The upload is too large. The total upload limit is 10 MB.','error')
    return redirect(url_for('index'))

if __name__=='__main__':
    app.run(debug=True)
