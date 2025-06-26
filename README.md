# HappyFox Backend Rule Processing Assignment

This repository is a complete backend solution for the **HappyFox Backend Rule Processing Assignment**, simulating the logic of Gmail-style rule-based email processing. It includes parsing and evaluating complex rule sets, performing actions on matched emails using the Gmail API, and storing/inspecting results in a local SQLite database. Unit and integration tests are provided to verify correctness.

---

## 🌐 Project Overview

**Goal**: Build a backend service that processes Gmail messages stored in a local database (`emails.db`) based on rules defined in a JSON file (`rules.json`) and applies corresponding actions via the Gmail API.

### Features

* Support for matching fields: `From`, `To`, `Subject`, `Message (Snippet)`, `Received Date`
* Supported predicates:

  * For string fields: `contains`, `does not contain`, `equals`, `does not equal`
  * For date fields: `less than`, `greater than` (with days/months)
* Support for rule sets with **ALL**/**ANY** matching semantics
* Actions supported:

  * `mark_as_read`
  * `mark_as_unread`
  * `move_to:<label>`
* Local database storage with a `processed_at` timestamp
* Full Gmail API integration for labeling/marking emails

---

## 📂 Project Structure

```
HappyFox_Backend_task/
├── src/
│   ├── process_rules.py       # Main rule evaluation + Gmail actions
│   ├── fetch_and_store.py     # Fetches emails from Gmail & stores in SQLite
│   └── inspect_db_mail.py     # Utility to inspect local DB after processing
│
├── tests/
│   ├── test_predicates.py         # Unit tests for rule predicate logic
│   ├── test_evaluate_rule.py      # Unit tests for rule evaluation
│   └── test_integration.py        # In-memory DB integration test
│
├── config/
│   └── credentials.json       # Gmail API credentials (OAuth2)
├── rules.json                 # Define rule sets and actions
├── emails.db                  # SQLite DB storing fetched Gmail messages
├── pytest.ini                 # Pytest config
├── README.md                  # This file
└── .venv/                     # Python virtual environment
```

---

## 🔧 Installation & Setup

```bash
# Clone the repo
$ git clone https://github.com/yourusername/HappyFox_Backend_task.git
$ cd HappyFox_Backend_task

# Create virtual environment
$ python -m venv .venv
$ source .venv/bin/activate     # On Windows: .venv\Scripts\activate

# Install dependencies
$ pip install -r requirements.txt
```

---

## 📊 How to Run the Project

### Step 1: Fetch Emails from Gmail

```bash
python src/fetch_and_store.py
```

This fetches Gmail messages and stores them in `emails.db`. Make sure `credentials.json` exists under `config/` and OAuth scopes are enabled.

### Step 2: Define Your Rules

Edit the `rules.json` file to create your own rule sets. Example:

```json
{
  "predicate": "any",
  "rules": [
    { "field": "From", "predicate": "contains", "value": "happyfox.com" },
    { "field": "Subject", "predicate": "contains", "value": "Assignment" }
  ],
  "actions": {
    "mark_as_read": true,
    "move_to": "Important"
  }
}
```

### Step 3: Run the Rule Processor

```bash
python src/process_rules.py --rules rules.json
```

This evaluates the rules against all unprocessed emails and applies the defined actions using the Gmail API. It marks `processed_at` for matched emails.

### Step 4: Inspect Processed Mails

```bash
python src/inspect_db_mail.py
```

This shows which emails were processed, their labels, and timestamps.

---

## ✅ Running the Tests

### Unit Tests

To run predicate logic and rule evaluation tests:

```bash
pytest tests/test_predicates.py
pytest tests/test_evaluate_rule.py
```

### Integration Test

To simulate end-to-end logic in-memory (without touching `emails.db` or Gmail API):

```bash
pytest tests/test_integration.py
```

---

## ⚡ Challenges Faced

### 1. **Date-based Logic and Natural Language Ambiguity**

Initially, rules like *"less than 2 days"* were interpreted as *older than 2 days*, which led to logical confusion. It was clarified as:

* **"less than N days old"** = received **within the last N days** (i.e., `received_at > now - N days`)

### 2. **Flaky Time-Dependent Tests**

Tests using `datetime.now()` directly were unreliable. Fix:

* Refactored functions to accept optional `now` parameter
* Used fixed `datetime` in tests for determinism

### 3. **Email Action Isolation**

To avoid interacting with real Gmail accounts in tests:

* All integration tests are isolated using in-memory DB
* Gmail API not triggered during tests

---

## 📅 Submission Checklist

*

---

## 🎥 Demo Video & GitHub

* GitHub Repository: [https://github.com/yourusername/HappyFox\_Backend\_task](https://github.com/yourusername/HappyFox_Backend_task)
* Demo Video: \[Link to YouTube or Drive Video Presentation & Walkthrough]

---

## 🙏 Credits

Created by Tejaswini R M as part of the HappyFox Pre-Placement Assignment.

---

## 🎓 License

This project is released for educational/demo purposes under the MIT License.
Feel free to fork and adapt for personal use.

---

If you face any issues setting it up or want to understand the logic further, feel free to raise an issue on the GitHub repo!
