from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        salary = float(request.form.get('salary', 0))

        # Simple tax logic (example)
        if salary <= 700000:
            tax = 0
        else:
            tax = (salary - 700000) * 0.1

        return render_template('index.html', result=f"Your Tax = ₹{tax:.2f}")

    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
