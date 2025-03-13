# api/views.py
import os
import fitz  # PyMuPDF for PDFs
from docx import Document
import requests  # Import the requests library
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class UploadResumeView(APIView):
    def post(self, request, format=None):
        # Get the file and job description from the request
        resume_file = request.FILES.get('resume_file')
        job_description = request.data.get('job_description', '')

        # Validate presence of both file and job description
        if not resume_file:
            return Response({"error": "No resume file provided."}, status=status.HTTP_400_BAD_REQUEST)
        if not job_description:
            return Response({"error": "No job description provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Determine file extension and process accordingly
        file_extension = os.path.splitext(resume_file.name)[1].lower()

        try:
            if file_extension == '.pdf':
                # Extract text from PDF using PyMuPDF
                doc = fitz.open(stream=resume_file.read(), filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
            elif file_extension in ['.doc', '.docx']:
                # Extract text from Word document using python-docx
                from tempfile import NamedTemporaryFile
                with NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
                    tmp.write(resume_file.read())
                    tmp_path = tmp.name
                doc = Document(tmp_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                os.unlink(tmp_path)  # Clean up the temporary file
            elif file_extension == '.txt':
                # Read plain text file
                text = resume_file.read().decode('utf-8')
            else:
                return Response({"error": "Unsupported file type."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error extracting text: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Prepare payload for n8n webhook
        n8n_url = "https://n8n-resume-matcher.onrender.com/webhook/analyzer"
        payload = {
            "resume": text,
            "job-description": job_description
        }

        # Send data to n8n webhook and process the response
        try:
            n8n_response = requests.post(n8n_url, json=payload, timeout=50)
            n8n_response.raise_for_status()  # Raise an error for bad status codes
            # Debug logging: print response status and text
            print("n8n response status:", n8n_response.status_code)
            print("n8n response text:", n8n_response.text)
            n8n_data = n8n_response.json()  # Expecting a flat JSON object now
        except Exception as e:
            return Response({"error": f"n8n webhook error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Extract output from n8n response; handle both list and dict cases
        output = {}
        if isinstance(n8n_data, list) and len(n8n_data) > 0:
            output = n8n_data[0]
        elif isinstance(n8n_data, dict):
            output = n8n_data

        # ... after obtaining and processing n8n_data
        print("AI Analysis Output:", output)


        # Return the extracted text, job description, and AI analysis output
        final_response = {
            "extracted_text": text,
            "job_description": job_description,
            "ai_analysis": output
        }
        return Response(final_response, status=status.HTTP_200_OK)
