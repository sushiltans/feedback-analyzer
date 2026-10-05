# AI Feedback Analyzer

A complete Flask web application for collecting, analyzing, filtering, visualizing, and exporting feedback using TextBlob sentiment analysis.

## Features

- Secure user registration and login with password hashing
- Individual feedback analysis
- Positive / Neutral / Negative sentiment classification
- Polarity and subjectivity scores
- Bulk CSV upload (`feedback` or `text` column)
- Analytics dashboard with sentiment distribution chart
- Search feedback by keyword
- Filter by sentiment
- Sort newest/oldest
- Delete individual feedback entries
- Export all analyzed feedback to CSV
- SQLite database with automatic initialization
- Responsive UI for desktop and mobile
- GitHub-ready project structure

## Tech Stack

- Python 3.10+
- Flask
- SQLite
- TextBlob
- HTML5 / CSS3 / JavaScript
- Chart.js

## Project Structure

```text
AI-Feedback-Analyzer/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── instance/
│   └── .gitkeep
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── feedback.html
│   └── dashboard.html
├── static/
│   ├── css/style.css
│   └── js/
│       ├── app.js
│       └── dashboard.js
└── tests/
    └── test_app.py
```

## Run Locally

### 1. Clone

```bash
git clone https://github.com/YOUR-USERNAME/AI-Feedback-Analyzer.git
cd AI-Feedback-Analyzer
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the secret key

Copy `.env.example` to `.env` and set a strong `SECRET_KEY`. For local use, the built-in fallback also allows the application to start, but use a real secret before deployment.

### 5. Start the application

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

## CSV Format

Recommended:

```csv
feedback
"The product is excellent and easy to use."
"Support was slow to respond."
"The application is okay."
```

A `text` column is also supported. If no header is present, the first column is analyzed.

## Security Notes

- Passwords are hashed with Werkzeug.
- User feedback is isolated by authenticated user ID.
- SQL queries use parameters rather than string interpolation for user values.
- Do not commit `.env` or the generated SQLite database.
- Set a strong random `SECRET_KEY` in production.
- For public deployment, run with a production WSGI server rather than Flask's development server.

## Testing

```bash
pip install pytest
pytest -q
```

## Deployment

The application can be deployed to any Python-friendly hosting provider that supports Flask. Set the `SECRET_KEY` environment variable and use a persistent database/storage strategy if the host has an ephemeral filesystem.

## License

Add the license you want to use before publishing (MIT is a common choice for open-source projects).
