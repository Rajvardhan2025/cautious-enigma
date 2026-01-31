from datetime import datetime
import logging
from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from api.schemas import AppointmentCreate, AppointmentUpdate
from core.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["appointments"])
db = DatabaseManager()

@router.post("/appointments")
async def create_appointment(appointment: AppointmentCreate):
    """Create a new appointment"""
    try:
        # Get user by phone
        user = await db.get_user_by_phone(appointment.user_phone)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if slot is available
        datetime_str = f"{appointment.date} {appointment.time}"
        booked_slots = await db.get_booked_slots(appointment.date)
        
        if datetime_str in booked_slots:
            raise HTTPException(status_code=400, detail="Time slot already booked")
        
        # Create appointment
        appointment_data = {
            "user_id": str(user["_id"]),
            "date": appointment.date,
            "time": appointment.time,
            "datetime": datetime.strptime(f"{appointment.date} {appointment.time}", "%Y-%m-%d %H:%M"),
            "purpose": appointment.purpose,
            "status": "confirmed",
            "created_at": datetime.utcnow()
        }
        
        appointment_id = await db.create_appointment(appointment_data)
        return {"appointment_id": str(appointment_id), "message": "Appointment created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/appointments/{user_phone}")
async def get_user_appointments(user_phone: str):
    """Get all appointments for a user"""
    try:
        # Get user by phone
        user = await db.get_user_by_phone(user_phone)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        appointments = await db.get_user_appointments(str(user["_id"]))
        
        # Convert ObjectIds to strings and format dates
        for apt in appointments:
            apt["_id"] = str(apt["_id"])
            if isinstance(apt["datetime"], datetime):
                apt["datetime"] = apt["datetime"].isoformat()
        
        return {"appointments": appointments}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/appointments/{appointment_id}")
async def update_appointment(appointment_id: str, update: AppointmentUpdate):
    """Update an appointment"""
    try:
        # Get current appointment
        appointment = await db.get_appointment_by_id(appointment_id, None) 
        # Note: the db method was defined to take user_id, but the original api.py passed None? 
        # Actually in original api.py line 248: appointment = await db.get_appointment_by_id(appointment_id, None)
        # Let's check database.py get_appointment_by_id implementation.
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        # Prepare updates
        updates = {}
        if update.date and update.time:
            # Check if new slot is available
            datetime_str = f"{update.date} {update.time}"
            booked_slots = await db.get_booked_slots(update.date)
            
            if datetime_str in booked_slots:
                raise HTTPException(status_code=400, detail="New time slot already booked")
            
            updates["date"] = update.date
            updates["time"] = update.time
            updates["datetime"] = datetime.strptime(f"{update.date} {update.time}", "%Y-%m-%d %H:%M")
        
        if update.purpose:
            updates["purpose"] = update.purpose
        
        if update.status:
            updates["status"] = update.status
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        # Update appointment
        success = await db.update_appointment(ObjectId(appointment_id), updates)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update appointment")
        
        return {"message": "Appointment updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/appointments/{appointment_id}")
async def cancel_appointment(appointment_id: str):
    """Cancel an appointment"""
    try:
        success = await db.update_appointment_status(ObjectId(appointment_id), "cancelled")
        if not success:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        return {"message": "Appointment cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/slots/{date}")
async def get_available_slots(date: str):
    """Get available appointment slots for a date"""
    try:
        # Hard-coded business hours (9 AM to 5 PM)
        base_slots = [f"{hour:02d}:00" for hour in range(9, 17)]
        
        # Get booked slots
        booked_slots = await db.get_booked_slots(date)
        booked_times = [slot.split(' ')[1] for slot in booked_slots if slot.startswith(date)]
        
        # Filter available slots
        available_slots = [slot for slot in base_slots if slot not in booked_times]
        
        return {"date": date, "available_slots": available_slots}
        
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summaries/{user_phone}")
async def get_conversation_summaries(user_phone: str):
    """Get conversation summaries for a user"""
    try:
        # Get user by phone
        user = await db.get_user_by_phone(user_phone)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        summaries = await db.get_user_conversation_summaries(str(user["_id"]))
        
        # Convert ObjectIds to strings and format dates
        for summary in summaries:
            summary["_id"] = str(summary["_id"])
            if isinstance(summary["conversation_date"], datetime):
                summary["conversation_date"] = summary["conversation_date"].isoformat()
        
        return {"summaries": summaries}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
