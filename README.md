# F1 Tyre Strategy Generator

## Overview
The **F1 Tyre Strategy Generator** is a tool designed to calculate the best tyre strategy for Formula 1 races based on input parameters such as the number of laps and tyre compounds. It uses Python for the backend logic and a simple web interface to display the results.

## Project Structure
- **main.py**: Contains the core logic for calculating the tyre strategy. It simulates lap times based on different tyre compounds and their age.
- **index.html**: Serves as the frontend interface for the web application. It interacts with the backend to display the calculated strategies.

## Features
- Calculates optimal pit stop strategies based on tyre wear and lap times.
- Supports different tyre compounds: Soft, Medium, and Hard.
- Web-based interface for easy interaction.

## How to Run

### Clone the Repository
```bash
git clone https://github.com/your-username/f1-tyre-strategy.git
```

### Navigate to the Project Directory
```bash
cd f1-tyre-strategy
```

### Set up a Virtual Environment
```bash
python -m venv .venv
```

### Install the dependencies
```bash
pip install flask plotly
```

### Run the Web Application
Open your web broswer and go to http://localhost:5000 to use the application

