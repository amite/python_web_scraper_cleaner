#!/usr/bin/env python3
"""
Simple web interface for news Q&A.
Run with: uv run web_ui.py
Then open: http://localhost:8000
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from news_server import _ask_news_logic, _ask_news_logic_stream
import uvicorn
from pathlib import Path

app = FastAPI(title="News Q&A")

# Create templates directory if it doesn't exist
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)

# Create the HTML template
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>News Q&A</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
        }
        .question-form {
            margin-bottom: 30px;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        button {
            background: #007bff;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .answer {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #007bff;
            white-space: pre-wrap;
            line-height: 1.6;
            min-height: 50px;
        }
        .question-text {
            color: #666;
            margin-bottom: 10px;
            font-style: italic;
        }
        .examples {
            margin-top: 20px;
            padding: 15px;
            background: #e7f3ff;
            border-radius: 5px;
        }
        .examples h3 {
            margin-top: 0;
            color: #0056b3;
        }
        .example-link {
            color: #007bff;
            cursor: pointer;
            text-decoration: underline;
            margin-right: 15px;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #007bff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📰 News Q&A</h1>
        
        <form class="question-form" id="questionForm">
            <input type="text" id="questionInput" name="question" placeholder="Ask a question about the news..." 
                   autofocus required>
            <button type="submit" id="submitBtn">Ask</button>
        </form>

        <div id="responseArea" class="hidden">
            <div class="question-text" id="questionDisplay"></div>
            <div class="answer" id="answerDisplay"></div>
        </div>

        <div class="examples">
            <h3>Example Questions:</h3>
            <span class="example-link" onclick="askQuestion('What are danish officials saying?')">
                What are danish officials saying?
            </span>
            <span class="example-link" onclick="askQuestion('What is happening in Iran?')">
                What is happening in Iran?
            </span>
            <span class="example-link" onclick="askQuestion('Is there news from South Korea?')">
                Is there news from South Korea?
            </span>
        </div>
    </div>

    <script>
        const form = document.getElementById('questionForm');
        const questionInput = document.getElementById('questionInput');
        const submitBtn = document.getElementById('submitBtn');
        const responseArea = document.getElementById('responseArea');
        const questionDisplay = document.getElementById('questionDisplay');
        const answerDisplay = document.getElementById('answerDisplay');

        function askQuestion(q) {
            questionInput.value = q;
            form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const question = questionInput.value.trim();
            if (!question) return;

            // Show response area and reset
            responseArea.classList.remove('hidden');
            questionDisplay.textContent = 'Q: ' + question;
            answerDisplay.innerHTML = '<div class="loading"></div>';
            
            // Disable form
            submitBtn.disabled = true;
            questionInput.disabled = true;

            try {
                // Create form data
                const formData = new FormData();
                formData.append('question', question);

                // Fetch with streaming
                const response = await fetch('/ask-stream', {
                    method: 'POST',
                    body: formData
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let answer = '';
                answerDisplay.textContent = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data === '[DONE]') {
                                break;
                            }
                            answer += data;
                            answerDisplay.textContent = answer;
                        }
                    }
                }
            } catch (error) {
                answerDisplay.textContent = 'Error: ' + error.message;
            } finally {
                // Re-enable form
                submitBtn.disabled = false;
                questionInput.disabled = false;
                questionInput.focus();
            }
        });
    </script>
</body>
</html>
"""

# Write the template
(templates_dir / "index.html").write_text(html_template)
templates = Jinja2Templates(directory=str(templates_dir))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def ask(request: Request, question: str = Form(...)):
    answer = _ask_news_logic(question)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "question": question,
        "answer": answer
    })

@app.post("/ask-stream")
async def ask_stream(question: str = Form(...)):
    """Stream the answer using Server-Sent Events."""
    def event_generator():
        for token in _ask_news_logic_stream(question):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    print("🚀 Starting News Q&A Web Interface...")
    print("📍 Open http://localhost:8001 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8001)
