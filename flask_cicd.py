from flask import Flask
app = Flask(__name__)

@app.route("/info")
def ks():
    return "HELLO STRANGER"

@app.route("/number")
def ks1():
    return "+9122222"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

