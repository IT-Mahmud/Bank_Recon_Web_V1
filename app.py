# app.py

from flask import Flask
from routes.main_routes import main_bp
from routes.upload_routes import upload_bp
from routes.bank_fin_reconcile_routes import bank_fin_reconcile_bp
from routes.bank_fin_tally_reconcile_routes import bank_fin_tally_reconcile_bp
from routes.bank_tally_reconcile_routes import bank_tally_bp

app = Flask(__name__)
app.secret_key = 'a_random_secret'

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(bank_fin_reconcile_bp)
app.register_blueprint(bank_fin_tally_reconcile_bp)
app.register_blueprint(bank_tally_bp)

if __name__ == '__main__':
    app.run(debug=True)
