# NEXUS · GenAI Chatbot Platform

A full-stack AI chatbot platform with a FastAPI backend and a sleek vanilla JS frontend — featuring JWT auth, streaming responses, persistent chat history, and a customizable system prompt.

**Live Demo:** [chatbot-1-rkok.onrender.com](https://chatbot-1-rkok.onrender.com/)

---

## ✨ Features

- 🔐 **Authentication** — Sign up / login with JWT-based sessions
- 💬 **Streaming chat** — Real-time, token-by-token AI responses via Server-Sent Events (SSE)
- 🗂️ **Chat history** — Every conversation is saved and can be revisited, renamed, or deleted
- 📝 **Custom system prompt** — Tune the assistant's behavior per session
- 📱 **Responsive UI** — Fully mobile-friendly with a collapsible sidebar
- 🎨 **Modern design** — Glassmorphism UI with animated gradients, built with plain HTML/CSS/JS (no framework needed)

---

## 🧱 Tech Stack

| Layer      | Technology                                  |
|------------|----------------------------------------------|
| Backend    | FastAPI (Python), PostgreSQL                  |
| LLM        | Groq API (`llama-3.3-70b`)                    |
| Auth       | JWT tokens                                    |
| Streaming  | Server-Sent Events (SSE)                      |
| Frontend   | HTML, CSS, JavaScript (vanilla), [marked.js](https://github.com/markedjs/marked) for Markdown rendering |
| Deployment | Render                                        |

---

## 📁 Project Structure

```
chatbot/
├── backend/          # FastAPI application, auth, chat streaming, DB models
├── frontend/         # index.html + app.js — the chat UI
└── .gitignore
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL database
- A Groq API key ([console.groq.com](https://console.groq.com))

### 1. Clone the repo

```bash
git clone https://github.com/Adityabiradar795/chatbot.git
cd chatbot
```

### 2. Backend setup

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in `backend/` with:

```env
DATABASE_URL=postgresql://user:password@host:port/dbname
GROQ_API_KEY=your_groq_api_key
JWT_SECRET=your_jwt_secret
```

Run the server:

```bash
uvicorn main:app --reload
```

### 3. Frontend setup

The frontend is static — just open `frontend/index.html` in your browser, or serve it with any static file server:

```bash
cd frontend
python -m http.server 5500
```

> ⚠️ Update the `BACKEND_URL` constant at the top of `app.js` to point to your running backend (local or deployed).

---

## 🔌 API Endpoints

| Method | Endpoint                     | Description                          |
|--------|-------------------------------|---------------------------------------|
| POST   | `/register`                  | Create a new account                  |
| POST   | `/login`                     | Log in and receive a JWT              |
| POST   | `/chat/stream`                | Send a message, stream the AI reply   |
| GET    | `/sessions`                  | List a user's chat sessions           |
| GET    | `/sessions/{id}/messages`    | Get messages for a specific session   |
| DELETE | `/sessions/{id}`             | Delete a chat session                 |

---

## 🌐 Live Demo

- **Frontend:** [chatbot-1-rkok.onrender.com](https://chatbot-1-rkok.onrender.com/)
- **Backend:** [chatbot-n5v4.onrender.com](https://chatbot-n5v4.onrender.com)

> Note: both services are hosted on Render's free tier, so the first request after inactivity may take 30–60s to wake up.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

## 📄 License

This project is licensed under the MIT License.
