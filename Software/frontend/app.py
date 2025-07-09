from flask import Flask, render_template
app = Flask(__name__, template_folder='html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/route/optimal')
def optimal():
    return render_template('optimal.html')

@app.route('/route/alternative')
def alternative():
    return render_template('alternative.html')


@app.route('/graphs/optimal')
def graphs_optimal():
    return render_template('graphs.html')

if __name__ == "__main__":
    app.run(debug=True, port=3000)
