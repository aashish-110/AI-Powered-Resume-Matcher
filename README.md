# Resume Match

A small Flask web app that accepts PDF or DOCX resumes, extracts candidate information with Groq, and displays a readable match report for the configured job description.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file and add your Groq API key:

   ```text
   GROQ_API_KEY=your_groq_api_key_here
   FLASK_SECRET_KEY=replace-with-a-random-value
   ```
4. Start the app:

   ```bash
   python parser.py
   ```

5. Open `http://127.0.0.1:5000`.

The upload limit is 10 MB total per request. Supported formats are PDF and DOCX.
