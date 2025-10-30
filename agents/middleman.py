import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from uagents import Agent, Context, Model
from utils import FEE_PERCENTAGE, load_balances, save_balances, load_offers, save_offers
import requests

vault = {}

def get_price_usd(token: str):
    token_map = {
        "SOL": "solana",
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "USDC": "usd-coin",
        "USDT": "tether"
    }
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_map[token]}&vs_currencies=usd"
        r = requests.get(url).json()
        return r[token_map[token]]["usd"]
    except:
        return 1.0

# Models
class Offer(Model):
    from_token: str
    to_token: str
    amount: float

class RequestOffers(Model):
    request: str = "get_offers"

class Quote(Model):
    from_token: str
    to_token: str
    amount: float  # amount seller gives
    price_to_token: float  # amount buyer must pay

class AcceptOffer(Model):
    offer_index: int

middleman = Agent(name="middleman", port=8000, endpoint=["http://localhost:8000/submit"])

# Seller posts an offer
@middleman.on_message(model=Offer)
async def on_offer(ctx: Context, sender: str, msg: Offer):
    balances = load_balances()
    seller_bal = balances["seller"].get(msg.from_token, 0)
    if seller_bal < msg.amount:
        ctx.logger.info(f"Seller has insufficient {msg.from_token}")
        return

    # Lock seller funds in vault
    vault[sender] = {msg.from_token: msg.amount}
    balances["seller"][msg.from_token] -= msg.amount
    save_balances(balances)

    offers = load_offers()
    offers.append({"from_token": msg.from_token, "to_token": msg.to_token, "amount": msg.amount, "seller": sender})
    save_offers(offers)
    ctx.logger.info(f"Stored offer: {msg.amount} {msg.from_token} → {msg.to_token}")

# Buyer requests offers
@middleman.on_message(model=RequestOffers)
async def on_request(ctx: Context, sender: str, msg: RequestOffers):
    offers = load_offers()
    for i, offer in enumerate(offers):
        # Compute correct amount of to_token
        price_from = get_price_usd(offer["from_token"])
        price_to   = get_price_usd(offer["to_token"])
        to_amount  = (offer["amount"] * price_from) / price_to
        to_amount_after_fee = to_amount * (1 - FEE_PERCENTAGE/100)

        quote = Quote(
            from_token=offer["from_token"],
            to_token=offer["to_token"],
            amount=offer["amount"],
            price_to_token=to_amount_after_fee
        )
        await ctx.send(sender, quote)

# Buyer accepts offer
@middleman.on_message(model=AcceptOffer)
async def on_accept(ctx: Context, sender: str, msg: AcceptOffer):
    offers = load_offers()
    idx = msg.offer_index
    if idx < 0 or idx >= len(offers):
        ctx.logger.info("Invalid offer index")
        return

    offer = offers.pop(idx)
    seller_addr = offer["seller"]
    locked_amount = vault[seller_addr][offer["from_token"]]

    balances = load_balances()

    # Compute actual to_token amount
    price_from = get_price_usd(offer["from_token"])
    price_to   = get_price_usd(offer["to_token"])
    to_amount  = (locked_amount * price_from) / price_to
    to_amount_after_fee = to_amount * (1 - FEE_PERCENTAGE/100)
    fee_amount = to_amount - to_amount_after_fee

    # Check buyer balance
    buyer_bal = balances["buyer"].get(offer["to_token"], 0)
    if buyer_bal < to_amount:
        ctx.logger.info("Buyer has insufficient funds")
        # Refund seller
        balances["seller"][offer["from_token"]] += locked_amount
        save_balances(balances)
        save_offers(offers)
        return

    # Execute swap
    balances["buyer"][offer["to_token"]] -= to_amount
    balances["buyer"][offer["from_token"]] = balances["buyer"].get(offer["from_token"], 0) + locked_amount

    balances["seller"][offer["to_token"]] = balances["seller"].get(offer["to_token"], 0) + to_amount_after_fee

    balances["middleman"][offer["to_token"]] = balances["middleman"].get(offer["to_token"], 0) + fee_amount

    save_balances(balances)
    vault.pop(seller_addr)
    save_offers(offers)
    ctx.logger.info(f"Swap executed: {locked_amount} {offer['from_token']} → {offer['to_token']} (buyer pays {to_amount:.4f}), fee {fee_amount:.4f}")

if __name__ == "__main__":
    print(f"[middleman] address: {middleman.address}")
    middleman.run()
