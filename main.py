import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Provided API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------
# Utility
# ---------------------------
class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            ObjectId(str(v))
            return str(v)
        except Exception:
            raise ValueError("Invalid ObjectId")


def to_public_doc(doc: dict):
    if not doc:
        return doc
    d = {**doc}
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


# ---------------------------
# Request/Response Models
# ---------------------------
class CartItem(BaseModel):
    product_id: ObjectIdStr
    title: str
    price: float
    image: Optional[str] = None
    quantity: int = Field(1, ge=1, le=10)
    variant: Optional[str] = None


class CartUpsert(BaseModel):
    session_id: str
    item: CartItem


class CartRemove(BaseModel):
    session_id: str
    product_id: ObjectIdStr
    variant: Optional[str] = None


# ---------------------------
# Routes
# ---------------------------
@app.get("/")
def read_root():
    return {"brand": "Provided", "message": "Luxury in quiet confidence."}


@app.get("/api/collections/featured")
def featured_collections():
    if db is None:
        return {"collections": []}
    cols = list(db.collection.find({"featured": True})) if hasattr(db, "collection") else []
    # Fallback to generic name if no 'collection' collection, try 'collections'
    if not cols and hasattr(db, "collections"):
        cols = list(db.collections.find({"featured": True}))
    return {"collections": [to_public_doc(c) for c in cols]}


@app.get("/api/products")
def list_products(featured: Optional[bool] = Query(default=None)):
    if db is None:
        return {"products": []}
    query = {}
    if featured is not None:
        query["featured"] = featured
    products = db.product.find(query).limit(50)
    return {"products": [to_public_doc(p) for p in products]}


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    if db is None:
        raise HTTPException(404, "Not found")
    try:
        prod = db.product.find_one({"_id": ObjectId(product_id)})
        if not prod:
            raise HTTPException(404, "Not found")
        return to_public_doc(prod)
    except Exception:
        raise HTTPException(400, "Invalid id")


@app.get("/api/cart")
def get_cart(session_id: str = Query(...)):
    if db is None:
        return {"items": [], "subtotal": 0.0}
    cart = db.cart.find_one({"session_id": session_id})
    if not cart:
        return {"items": [], "subtotal": 0.0}
    items = cart.get("items", [])
    subtotal = sum((i.get("price", 0) * i.get("quantity", 1)) for i in items)
    return {"id": str(cart.get("_id")), "items": items, "subtotal": round(subtotal, 2)}


@app.post("/api/cart/add")
def add_to_cart(payload: CartUpsert):
    if db is None:
        raise HTTPException(500, "Database unavailable")
    cart = db.cart.find_one({"session_id": payload.session_id})
    item = payload.item.model_dump()
    if cart is None:
        create_document("cart", {"session_id": payload.session_id, "items": [item]})
    else:
        items = cart.get("items", [])
        # Merge if same product and variant
        merged = False
        for i in items:
            if i.get("product_id") == item["product_id"] and i.get("variant") == item.get("variant"):
                i["quantity"] = min(10, i.get("quantity", 1) + item.get("quantity", 1))
                merged = True
                break
        if not merged:
            items.append(item)
        db.cart.update_one({"_id": cart["_id"]}, {"$set": {"items": items}})
    return {"status": "ok"}


@app.post("/api/cart/remove")
def remove_from_cart(payload: CartRemove):
    if db is None:
        raise HTTPException(500, "Database unavailable")
    cart = db.cart.find_one({"session_id": payload.session_id})
    if not cart:
        return {"status": "ok"}
    items = [i for i in cart.get("items", []) if not (
        i.get("product_id") == payload.product_id and i.get("variant") == payload.variant
    )]
    db.cart.update_one({"_id": cart["_id"]}, {"$set": {"items": items}})
    return {"status": "ok"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ---------------------------
# Seed minimal demo data for prototype
# ---------------------------
@app.on_event("startup")
def seed_demo():
    if db is None:
        return
    try:
        if db.product.count_documents({}) == 0:
            demo = [
                {
                    "title": "Provided Cashmere Overcoat",
                    "description": "Double-faced Italian cashmere with hand-finished edges.",
                    "price": 1680.0,
                    "category": "Outerwear",
                    "in_stock": True,
                    "featured": True,
                    "images": [
                        "https://images.unsplash.com/photo-1548883354-cab52747f867?w=1200&auto=format&fit=crop&q=80",
                        "https://images.unsplash.com/photo-1548883354-3e64f90cbb7a?w=1200&auto=format&fit=crop&q=80"
                    ],
                    "variants": [
                        {"size": "S"}, {"size": "M"}, {"size": "L"}
                    ],
                    "tags": ["cashmere", "editorial"]
                },
                {
                    "title": "Provided Silk Blend Shirt",
                    "description": "Matte silk blend with mother-of-pearl buttons.",
                    "price": 420.0,
                    "category": "Shirts",
                    "in_stock": True,
                    "featured": True,
                    "images": [
                        "https://images.unsplash.com/photo-1516826957135-700dedea698c?w=1200&auto=format&fit=crop&q=80"
                    ],
                    "variants": [
                        {"size": "XS"}, {"size": "S"}, {"size": "M"}, {"size": "L"}
                    ],
                    "tags": ["silk"]
                },
                {
                    "title": "Provided Japanese Denim",
                    "description": "Selvedge denim, rinse washed for a deep navy tone.",
                    "price": 360.0,
                    "category": "Denim",
                    "in_stock": True,
                    "featured": False,
                    "images": [
                        "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=1200&auto=format&fit=crop&q=80"
                    ],
                    "variants": [
                        {"size": "28"}, {"size": "30"}, {"size": "32"}, {"size": "34"}
                    ],
                    "tags": ["denim"]
                }
            ]
            db.product.insert_many(demo)
        # Seed featured collection doc
        if db.collections.count_documents({"slug": "aw-collection"}) == 0:
            prod_ids = [str(p["_id"]) for p in db.product.find({"featured": True})]
            db.collections.insert_one({
                "name": "Autumn/Winter",
                "slug": "aw-collection",
                "description": "Quiet layers. Cinematic textures.",
                "hero_image": "https://images.unsplash.com/photo-1503342217505-b0a15cf70489?w=1600&auto=format&fit=crop&q=80",
                "product_ids": prod_ids,
                "featured": True
            })
    except Exception:
        # Best-effort seed; ignore errors in ephemeral env
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
