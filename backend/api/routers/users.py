from datetime import datetime
import logging
from fastapi import APIRouter, HTTPException
from api.schemas import UserCreate
from core.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])
db = DatabaseManager()

@router.post("")
async def create_user(user: UserCreate):
    """Create a new user"""
    try:
        # Check if user already exists
        existing_user = await db.get_user_by_phone(user.phone)
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        
        user_data = {
            "phone": user.phone,
            "name": user.name,
            "email": user.email,
            "created_at": datetime.utcnow()
        }
        
        user_id = await db.create_user(user_data)
        return {"user_id": str(user_id), "message": "User created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{phone}")
async def get_user(phone: str):
    """Get user by phone number"""
    try:
        user = await db.get_user_by_phone(phone)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Convert ObjectId to string
        user["_id"] = str(user["_id"])
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))
