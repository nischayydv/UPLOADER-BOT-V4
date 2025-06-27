import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

if __name__ == '__main__':
    # Use dynamic port from Render
    port = int(os.environ.get('PORT', 8080))  # fallback to 8080
    app.run(host='0.0.0.0', port=port)
