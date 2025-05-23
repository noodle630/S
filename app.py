import os
import csv
import io
import pandas as pd
from flask import Flask, request, jsonify, make_response
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Initialize Flask app
app = Flask(__name__)

@app.route('/clean', methods=['POST'])
def clean_csv():
    """
    API endpoint to clean CSV data using OpenAI.
    
    This endpoint receives a CSV file upload, sends the content to OpenAI for cleaning,
    and returns the cleaned CSV data as a response.
    """
    try:
        # Check if a file was uploaded
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        
        # Check if file is empty
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Check if the file is a CSV
        if file.filename is None or not file.filename.endswith('.csv'):
            return jsonify({"error": "File must be a CSV"}), 400
        
        # Read the CSV file
        csv_content = file.read().decode('utf-8')
        
        # Parse the CSV to determine structure and issues
        try:
            df = pd.read_csv(io.StringIO(csv_content))
            row_count = len(df)
            column_count = len(df.columns)
            columns = list(df.columns)
            
            # Limit the data sample to prevent exceeding token limits
            sample_rows = min(5, row_count)
            data_sample = df.head(sample_rows).to_csv(index=False)
            
            # Prepare a message about the data structure
            data_info = f"""
            CSV file has {row_count} rows and {column_count} columns.
            Columns: {', '.join(columns)}
            """
            
        except Exception as e:
            return jsonify({"error": f"Error parsing CSV: {str(e)}"}), 400
        
        # Send to OpenAI for cleaning
        prompt = f"""
        As an AI data cleaning expert, clean the following CSV data to make it marketplace-ready.
        
        Data information:
        {data_info}
        
        Sample data (first {sample_rows} rows):
        {data_sample}
        
        Please perform the following cleaning tasks on the entire CSV:
        1. Fix inconsistent formatting (capitalization, spacing, punctuation)
        2. Standardize values in each column
        3. Handle missing values appropriately
        4. Remove any invalid or corrupted data
        5. Ensure proper formatting for marketplace listings (e.g., proper product titles, descriptions)
        6. Return the ENTIRE cleaned dataset in valid CSV format
        
        IMPORTANT: Your response should ONLY contain the cleaned CSV data in a valid, properly formatted CSV. 
        Do not include any explanations or markdown formatting. Just return the raw CSV content.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[
                {"role": "system", "content": "You are a data cleaning expert that helps prepare CSV files for marketplace listings."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent outputs
        )
        
        # Extract the cleaned CSV from the response
        message_content = response.choices[0].message.content
        if message_content is None:
            return jsonify({"error": "Received empty response from OpenAI API"}), 500
            
        # Remove markdown code block indicators if present
        cleaned_content = message_content.strip()
        if cleaned_content.startswith("```csv"):
            cleaned_content = cleaned_content[6:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
            
        cleaned_csv = cleaned_content.strip()
        
        # Create a text/csv response
        response = make_response(cleaned_csv)
        response.headers["Content-Disposition"] = f"attachment; filename=cleaned_{file.filename}"
        response.headers["Content-Type"] = "text/csv"
        
        return response
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add a route for the index page that displays a form for uploading CSV files
@app.route('/', methods=['GET'])
def index():
    """Simple HTML form for testing the CSV cleaner"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CSV Cleaner</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #333;
            }
            form {
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
            .form-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            input[type="file"] {
                width: 100%;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            button:hover {
                background-color: #45a049;
            }
            .info {
                background-color: #e7f3fe;
                border-left: 6px solid #2196F3;
                padding: 10px;
                margin: 15px 0;
            }
        </style>
    </head>
    <body>
        <h1>CSV Cleaner Tool</h1>
        <div class="info">
            <p>This tool uses OpenAI GPT-4o to clean and optimize CSV data for marketplace listings.</p>
            <p>Upload a CSV file and receive a cleaned version with standardized formatting.</p>
        </div>
        
        <form action="/clean" method="post" enctype="multipart/form-data">
            <div class="form-group">
                <label for="file">Select CSV File:</label>
                <input type="file" id="file" name="file" accept=".csv" required>
            </div>
            <button type="submit">Clean CSV</button>
        </form>
    </body>
    </html>
    """
    return html

# Custom error handler for 404 errors
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Route not found"}), 404

# Custom error handler for 500 errors 
@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Server error"}), 500

if __name__ == '__main__':
    # Run the app on 0.0.0.0 to make it accessible externally
    # Use port 5001 to avoid conflict with the Node.js server
    app.run(host='0.0.0.0', port=5001, debug=True)