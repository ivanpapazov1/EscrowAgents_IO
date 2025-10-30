import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from uagents import Agent, Context, Model
from utils import load_balances
import asyncio

MIDDLEMAN_ADDRESS = "miiddleman_address" #paste

class RequestOffers(Model):
    request: str = "get_offers"

class Quote(Model):
    from_token: str
    to_token: str
    amount: float  # seller gives
    price_to_token: float  # buyer must pay

class AcceptOffer(Model):
    offer_index: int

buyer = Agent(name="buyer", port=8002, endpoint=["http://localhost:8002/submit"])
received_offers = []

@buyer.on_message(model=Quote)
async def on_offer(ctx: Context, sender: str, msg: Quote):
    exists = any(
        o.from_token == msg.from_token and
        o.to_token == msg.to_token and
        o.amount == msg.amount
        for o in received_offers
    )
    if not exists:
        received_offers.append(msg)
        print(f"\n📩 New offer: {msg.amount} {msg.from_token} → {msg.to_token}, buyer pays {msg.price_to_token:.4f} {msg.to_token}")

@buyer.on_event("startup")
async def request_offers(ctx: Context):
    async def loop_request():
        while True:
            try:
                await ctx.send(MIDDLEMAN_ADDRESS, RequestOffers())
            except Exception as e:
                print(f"❌ Failed to request offers: {e}")
            await asyncio.sleep(3)
    asyncio.create_task(loop_request())

@buyer.on_event("startup")
async def manual_mode(ctx: Context):
    while True:
        if not received_offers:
            print("No offers yet. Waiting...")
            await asyncio.sleep(2)
            continue

        balances = load_balances()
        print("\n=== AVAILABLE OFFERS ===")
        for i, o in enumerate(received_offers):
            print(f"{i}. {o.amount} {o.from_token} → {o.to_token}, buyer pays {o.price_to_token:.4f}")

        choice = input("Select offer number to accept (ENTER to skip): ")
        if not choice:
            await asyncio.sleep(1)
            continue

        try:
            idx = int(choice)
            if idx < 0 or idx >= len(received_offers):
                print("❌ Invalid choice")
                continue
        except:
            print("❌ Invalid input")
            continue

        offer = received_offers[idx]
        buyer_bal = balances["buyer"].get(offer.to_token, 0)
        if buyer_bal < offer.price_to_token:
            print(f"❌ Not enough {offer.to_token}. You have {buyer_bal}, need {offer.price_to_token:.4f}")
            continue

        # Send AcceptOffer message to Middleman
        await ctx.send(MIDDLEMAN_ADDRESS, AcceptOffer(offer_index=idx))
        received_offers.pop(idx)
        print(f"✅ Offer {idx} accepted")

if __name__ == "__main__":
    buyer.run()
