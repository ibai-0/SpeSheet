
# ALLSTAT: CO2 Emissions Dashboard

> **Advanced spatio-temporal data analysis for official statistics.** > Developed by: Ibai Mayoral, Hugo Recio, Iñaki Moreno, & Xabier Aranguena.

---

## Live Application
The application is deployed and ready for review at the following link:

**[https://spesheet.onrender.com](https://spesheet.onrender.com)**

> **⚠️ Note on Loading Time:** > The app is hosted on a free-tier server. If the page takes **30–45 seconds** to load initially, the server is "waking up" from hibernation. Please be patient and avoid refreshing the page during this process.

---

## Local Installation (Technical Review)

If you prefer to run the application locally for code inspection or performance testing, follow these steps:

### 1. Clone the Repository
Clone the project and move into the directory:
```bash
git clone https://github.com/ibai-0/SpeSheet.git
cd SpeSheet
```

### 2. Activate Virtual Environment
Activate the virtual environment (Windows):
```bash
python -m venv venv
.\venv\Scripts\activate
```

Activate the virtual environment (Linux/Mac):
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 4. Run the app
Launch the server:
```bash
python main.py
```

### 5. Open the app in your browser
Once the terminal shows the server is live, visit:
```bash
http://127.0.0.1:8050/
```

### 6. Technologies Used
- Python (Core Logic)
- Pandas (Data Manipulation)
- Dash/Plotly (Visualization)

