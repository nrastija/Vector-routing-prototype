from flask import Flask, render_template
app = Flask(__name__, template_folder='html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/route/optimal')
def optimal():
    return render_template('optimal.html')

if __name__ == "__main__":
    app.run(debug=True, port=3000)
