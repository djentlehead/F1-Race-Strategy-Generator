# pylint: disable=import-error
from flask import Flask, render_template, request, jsonify
import plotly
import plotly.graph_objects as go
import json
import numpy as np

app = Flask(__name__)

class Tyre:
    def __init__(self, compound, age, base):
        self.compound = compound
        self.age = age
        self.base = base

    def lapTime(self):
        compound = self.compound.lower()
        if compound == "hard" or compound == "h":
            return (self.base + 2.5) * (1.001) ** self.age
        if compound == "medium" or compound == "m":
            return (self.base + 1.6) * (1.003) ** self.age
        if compound == "soft" or compound == "s":
            return self.base * (1.005) ** self.age
        return None

def strategy(numberOfLaps, c1, c2):
    time = 500 * numberOfLaps
    pitStop = 0
    for i in range(numberOfLaps):
        t = 0

        c1_tyre = Tyre(c1, 0, 90)
        t += c1_tyre.lapTime()
        for j in range(i):
            c1_tyre = Tyre(c1, c1_tyre.age + 1, c1_tyre.base)
            t += c1_tyre.lapTime()

        c2_tyre = Tyre(c2, 0, 90)
        t += c2_tyre.lapTime()
        for j in range(numberOfLaps - i - 1):  
            c2_tyre = Tyre(c2, c2_tyre.age + 1, c2_tyre.base)
            t += c2_tyre.lapTime()

        if time > t:
            time = t
            pitStop = i + 1  
        
    return pitStop, time
    pass

def create_plot(numberOfLaps, c1, c2):
    strat = strategy(numberOfLaps, c1, c2)
    y1 = []
    c1_tyre = Tyre(c1, 0, 90)
    y1.append(c1_tyre.lapTime())
    for j in range(strat[0] - 1):
        c1_tyre = Tyre(c1, c1_tyre.age + 1, 90)
        y1.append(c1_tyre.lapTime())

    while (len(y1) != numberOfLaps):
        y1.append(0)

    y2 = []
    for j in range(strat[0]):
        y2.append(0)

    c2_tyre = Tyre(c2, 0, 90)
    y2.append(c2_tyre.lapTime())
    for j in range(numberOfLaps - strat[0] - 1):
        c2_tyre = Tyre(c2, c2_tyre.age + 1, c2_tyre.base)
        y2.append(c2_tyre.lapTime())

    x = list(range(1, numberOfLaps + 1))

    # Create Plotly figure
    fig = go.Figure()

    colors = {
        'S': 'red',
        'M': 'yellow',
        'H': 'black'
    }

    fig.add_trace(go.Scatter(
        x=x,
        y=y1,
        name=f'{c1} compound',
        line=dict(color=colors.get(c1, 'green'))
    ))

    fig.add_trace(go.Scatter(
        x=x,
        y=y2,
        name=f'{c2} compound',
        line=dict(color=colors.get(c2, 'green'))
    ))

    fig.update_layout(
        title=f'Race Strategy: {c1} → {c2}',
        xaxis_title='Lap Number',
        yaxis_title='Lap Time (seconds)',
        template='plotly_white'
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def pickBest(numberOfLaps):
    strategies = [
        ("S", "M"),
        ("S", "H"),
        ("M", "H"),
        ("M", "S"),
        ("H", "S"),
        ("H", "M")
    ]
    
    best_time = float('inf')
    best_c1 = None
    best_c2 = None
    
    for c1, c2 in strategies:
        new_time = strategy(numberOfLaps, c1, c2)[1]
        if new_time < best_time:
            best_time = new_time
            best_c1 = c1
            best_c2 = c2

    return best_time // 60, best_time % 60, best_c1, best_c2

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    laps = int(data['laps'])
    minutes, seconds, compound1, compound2 = pickBest(laps)
    plot_json = create_plot(laps, compound1, compound2)
    
    return jsonify({
        'plot': plot_json,
        'strategy': f"Best strategy: Start on {compound1}, switch to {compound2}",
        'time': f"Total time: {int(minutes)}:{seconds:.2f}"
    })

if __name__ == '__main__':
    app.run(debug=True)