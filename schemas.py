"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# Brand-specific schemas for the Provided luxury e-commerce experience

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product"
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    variants: List[dict] = Field(default_factory=list, description="Variant options like size/color")
    tags: List[str] = Field(default_factory=list)
    featured: bool = Field(False)

class Collection(BaseModel):
    """
    Collections schema
    Collection name: "collection"
    """
    name: str
    slug: str
    description: Optional[str] = None
    hero_image: Optional[str] = None
    product_ids: List[str] = Field(default_factory=list)
    featured: bool = Field(False)

class Cart(BaseModel):
    """
    Shopping cart schema (per session/user)
    Collection name: "cart"
    """
    session_id: str = Field(..., description="Client session identifier")
    currency: Literal["USD", "EUR", "GBP"] = "USD"
    items: List[dict] = Field(default_factory=list, description="Cart line items")

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: Optional[str] = Field(None, description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")
