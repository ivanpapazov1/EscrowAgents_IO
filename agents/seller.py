import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from uagents import Agent, Context, Model
from utils import load_balances
import asyncio

MIDDLEMAN_ADDRESS = "middleman_address" #paste

class Offer(Model):
    from_token: str
    to_token: str
    amount: float

seller = Agent(name="seller", port=8001, endpoint=["http://localhost:8001/submit"])

@seller.on_event("startup")
async def startup(ctx: Context):
    balances = load_balances()
    print("=== SELLER CONTROL PANEL ===")
    print("Available tokens:", ", ".join(balances["seller"].keys()))
    from_token = input("Token to sell: ").strip()
    to_token = input("Token to receive: ").strip()
    amount = float(input("Amount: "))

    if balances["seller"].get(from_token, 0) < amount:
        print("❌ Not enough balance")
        return

    offer = Offer(from_token=from_token, to_token=to_token, amount=amount)
    await ctx.send(MIDDLEMAN_ADDRESS, offer)
    print(f"✅ Offer sent: {amount} {from_token} → {to_token}")

if __name__ == "__main__":
    seller.run()
