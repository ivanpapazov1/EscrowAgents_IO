import json

FEE_PERCENTAGE = 1.0  # Middleman fee %

BALANCES_FILE = "balances.json"

def load_balances():
    try:
        with open(BALANCES_FILE, "r") as f:
            return json.load(f)
    except:
        return {"seller": {}, "buyer": {}, "middleman": {}}

def save_balances(data):
    with open(BALANCES_FILE, "w") as f:
        json.dump(data, f, indent=4)

OFFERS_FILE = "offers.json"

def load_offers():
    try:
        with open(OFFERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_offers(data):
    with open(OFFERS_FILE, "w") as f:
        json.dump(data, f, indent=4)
